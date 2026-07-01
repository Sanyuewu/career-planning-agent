# -*- coding: utf-8 -*-
"""
学生图谱存储服务
将学生数据存储到知识图谱中，支持基于图谱的智能匹配
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from app.config import BASE_DIR
from app.services.state_store import PersistentStore
from app.services import snapshot_store


class StudentGraphService:
    """学生图谱存储服务（学生/匹配落 DB：KVStore 写穿，重启不丢、多实例安全）"""

    def __init__(self):
        self.graph_path = BASE_DIR / "data" / "student_graph.json"
        # 复用 PersistentStore（与 chat/report 同一套写穿持久化），替代全量重写 JSON 文件。
        self.students = PersistentStore("student")        # student_id → 学生节点 dict
        self.matches_store = PersistentStore("match")     # match_id   → 匹配记录 dict
        self._migrate_json_if_needed()

    def _migrate_json_if_needed(self):
        """首次运行：DB 学生为空且旧 JSON 存在时，无损迁入 store（之后自动跳过）。
        student_graph.json 保留作冷备，不删除。"""
        if len(self.students) > 0 or not self.graph_path.exists():
            return
        try:
            with open(self.graph_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for sid, node in (data.get("students", {}) or {}).items():
                self.students[sid] = node
            for m in (data.get("matches", []) or []):
                mid = m.get("id") or str(uuid.uuid4())
                self.matches_store[mid] = m
            print(f"[student_graph] 已从 JSON 迁移 {len(self.students)} 学生 / "
                  f"{len(self.matches_store)} 匹配记录到 DB")
        except Exception as e:
            print(f"迁移 student_graph.json 失败: {e}")

    def save_student(self, student_data: Dict) -> str:
        """
        保存学生数据到图谱

        Args:
            student_data: 学生画像数据

        Returns:
            学生ID
        """
        raw_id = student_data.get("student_id", "")
        try:
            uuid.UUID(str(raw_id))
            student_id = str(raw_id)
        except (ValueError, AttributeError):
            student_id = str(uuid.uuid4())

        student_node = {
            "id": student_id,
            "type": "Student",
            "attributes": {
                "name": student_data.get("name", ""),
                "student_id": student_id,
                "skills": self._normalize_skills(student_data.get("skills", [])),
                "certificates": student_data.get("certificates", []),
                "innovation": student_data.get("innovation", "一般"),
                "learning": student_data.get("learning", "一般"),
                "stress_resistance": student_data.get("stress_resistance", "一般"),
                "communication": student_data.get("communication", "一般"),
                "internship": student_data.get("internship", "一般"),
                "education": student_data.get("education", []),
                "projects": student_data.get("projects", []),
                "internships": student_data.get("internships", []),
                "career_intent": student_data.get("career_intent", ""),
                "interests": student_data.get("interests", []),
                "job_preferences": student_data.get("job_preferences", {}),
                "completeness_score": student_data.get("completeness_score", 0),
                "competitiveness_score": student_data.get("competitiveness_score", 0),
                "created_at": datetime.now().isoformat()
            },
            "skill_edges": self._build_skill_edges(student_data.get("skills", []))
        }

        self.students[student_id] = student_node   # 写穿自动落库

        # 成长闭环：画像更新 append 一条快照（best-effort，失败不影响主流程）
        snapshot_store.record_portrait_snapshot(
            student_id, student_node["attributes"], trigger="resume_update"
        )

        return student_id

    def save_match_result(self, student_id: str, job_name: str, match_result: Dict) -> str:
        """
        保存匹配结果到图谱

        Args:
            student_id: 学生ID
            job_name: 岗位名称
            match_result: 匹配结果（四维度）

        Returns:
            匹配记录ID
        """
        match_id = str(uuid.uuid4())

        match_record = {
            "id": match_id,
            "type": "MATCHES",
            "student_id": student_id,
            "job_name": job_name,
            "attributes": {
                "basic_match": match_result.get("basic_match", 0),
                "skill_match": match_result.get("skill_match", 0),
                "quality_match": match_result.get("quality_match", 0),
                "potential_match": match_result.get("potential_match", 0),
                "total_match": match_result.get("total_match", 0),
                "matched_skills": match_result.get("matched_skills", []),
                "missing_skills": match_result.get("missing_skills", []),
                "skill_analysis": match_result.get("skill_analysis", ""),
                "created_at": datetime.now().isoformat()
            }
        }

        self.matches_store[match_id] = match_record   # 写穿自动落库

        return match_id

    def get_student_matches(self, student_id: str) -> List[Dict]:
        """获取学生的所有匹配记录"""
        return [
            match for match in self.matches_store.values()
            if match.get("student_id") == student_id
        ]

    def _normalize_skills(self, skills: List) -> List[str]:
        """规范化技能列表"""
        normalized = []
        for skill in skills:
            if isinstance(skill, dict):
                normalized.append(skill.get("name", ""))
            elif isinstance(skill, str):
                normalized.append(skill)
        return [s for s in normalized if s]

    def _build_skill_edges(self, skills: List) -> List[Dict]:
        """构建技能边"""
        edges = []
        for skill in skills:
            if isinstance(skill, dict):
                edges.append({
                    "target": skill.get("name", ""),
                    "type": "HAS_SKILL",
                    "level": skill.get("level", "熟练")
                })
            elif isinstance(skill, str):
                edges.append({
                    "target": skill,
                    "type": "HAS_SKILL",
                    "level": "熟练"
                })
        return edges

    def get_student(self, student_id: str) -> Optional[Dict]:
        """获取学生数据"""
        return self.students.get(student_id)

    def get_all_students(self) -> List[Dict]:
        """获取所有学生"""
        return list(self.students.values())

    def update_student(self, student_id: str, updates: Dict) -> bool:
        """更新学生数据"""
        if student_id not in self.students:
            return False

        student = self.students[student_id]
        student["attributes"].update(updates)
        student["attributes"]["updated_at"] = datetime.now().isoformat()
        self.students.save(student_id)   # 就地修改需显式落库

        # 成长闭环：手动编辑画像也 append 快照，区分 trigger 供归因
        snapshot_store.record_portrait_snapshot(
            student_id, student["attributes"], trigger="manual_edit"
        )
        return True

    def delete_student(self, student_id: str) -> bool:
        """删除学生（连带其匹配记录）"""
        if student_id not in self.students:
            return False

        del self.students[student_id]
        for mid in [k for k, m in self.matches_store.items() if m.get("student_id") == student_id]:
            del self.matches_store[mid]
        return True

    def get_student_match_data(self, student_id: str) -> Dict:
        """获取学生匹配数据（用于人岗匹配）"""
        student = self.get_student(student_id)
        if not student:
            return {}

        attrs = student.get("attributes", {})

        return {
            "student_id": attrs.get("student_id", ""),
            "name": attrs.get("name", ""),
            "skills": attrs.get("skills", []),
            "certificates": attrs.get("certificates", []),
            "innovation": attrs.get("innovation", "一般"),
            "learning": attrs.get("learning", "一般"),
            "stress_resistance": attrs.get("stress_resistance", "一般"),
            "communication": attrs.get("communication", "一般"),
            "internship": attrs.get("internship", "一般"),
            "education": attrs.get("education", []),
            "projects": attrs.get("projects", []),
            "internships": attrs.get("internships", []),
            "career_intent": attrs.get("career_intent", ""),
            "completeness_score": attrs.get("completeness_score", 0),
            "competitiveness_score": attrs.get("competitiveness_score", 0)
        }


student_graph_service = StudentGraphService()
