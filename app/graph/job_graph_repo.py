# -*- coding: utf-8 -*-
"""
岗位图谱模块 - NetworkX实现
遵循v4规范：优先方案Neo4j，备选方案NetworkX
支持：晋升路径、换岗路径、技能语义扩展(I1)
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import networkx as nx

from app.config import settings, DATA_DIR, PROFILE_JSON_PATH


class JobGraphRepo:
    """
    NetworkX内存图谱，接口与Neo4j版本一致
    切换方式：config.GRAPH_BACKEND = "networkx" | "neo4j"
    数据来源：pipeline生成的 data/job_graph.json 或 job_profiles.json
    """
    
    def __init__(self):
        self.G = nx.DiGraph()
        self._load_graph()
    
    def _load_graph(self):
        """加载图谱数据"""
        graph_path = DATA_DIR / "job_graph.json"
        
        if graph_path.exists():
            self._load_from_graph_json(graph_path)
        elif PROFILE_JSON_PATH.exists():
            self._build_from_profiles(PROFILE_JSON_PATH)
        else:
            raise FileNotFoundError("找不到岗位数据文件，请先运行pipeline脚本")
    
    def _load_from_graph_json(self, path: Path):
        """从job_graph.json加载预构建的图谱"""
        data = json.loads(path.read_text(encoding="utf-8"))
        
        for node in data.get("nodes", []):
            self.G.add_node(node["id"], **node.get("attrs", {}))
        
        for edge in data.get("edges", []):
            props = edge.get("props", {})
            edge_type = props.pop("edge_type", "UNKNOWN")
            self.G.add_edge(
                edge["from"], 
                edge["to"],
                type=edge_type,
                **props
            )
    
    def _build_from_profiles(self, path: Path):
        """从job_profiles.json构建图谱"""
        profiles = json.loads(path.read_text(encoding="utf-8"))
        
        for profile in profiles:
            job_name = profile.get("岗位名称", "")
            if not job_name:
                continue
            
            self.G.add_node(
                job_name,
                title=job_name,
                overview=profile.get("岗位概述", ""),
                industry=profile.get("所属行业", ""),
                industry_category=profile.get("行业分类", ""),
                salary=profile.get("薪资范围", ""),
                skills=profile.get("专业技能", []),
                required_skills=profile.get("必需技能", []),
                preferred_skills=profile.get("优先技能", []),
                bonus_skills=profile.get("加分技能", []),
                market_heat=profile.get("市场热度", 5),
                certs=profile.get("证书要求", []),
                tags=profile.get("岗位标签", []),
            )
            
            for vp in profile.get("垂直晋升路径", []):
                target = vp.get("岗位", "")
                if target and target != job_name:
                    self.G.add_edge(
                        job_name, target,
                        type="PROMOTES_TO",
                        years=vp.get("年限", ""),
                        description=vp.get("描述", ""),
                    )
            
            for hp in profile.get("横向换岗路径", []):
                target = hp.get("目标岗位", "")
                if target:
                    match_level = hp.get("匹配度", "中")
                    overlap = {"高": 0.8, "中": 0.5, "低": 0.3}.get(match_level, 0.5)
                    self.G.add_edge(
                        job_name, target,
                        type="CAN_TRANSFER_TO",
                        match_level=match_level,
                        overlap_pct=overlap,
                        advantage=hp.get("迁移优势", ""),
                        need_learn=hp.get("需补足", ""),
                    )
    
    def _normalize_job_id(self, job_name: str) -> str:
        """标准化岗位ID：先查图中是否直接存在，再尝试加前缀，避免 job_job_XXX 双前缀"""
        if job_name in self.G:
            return job_name
        prefixed = f"job_{job_name}"
        if prefixed in self.G:
            return prefixed
        return job_name  # 不存在时原样返回，由调用方处理 None
    
    def get_job_info(self, job_name: str) -> Optional[dict]:
        """获取岗位详细信息"""
        job_id = self._normalize_job_id(job_name)
        if job_id not in self.G:
            return None
        node_data = dict(self.G.nodes[job_id])
        return node_data
    
    def get_promotion_paths(self, job_name: str, max_depth: int = 5) -> List[Dict]:
        """
        获取晋升路径（DFS 沿 PROMOTES_TO 边，O(V+E) 替代原 O(V²) 实现）
        返回: [{"nodes": [...], "transitions": [...]}]
        """
        job_id = self._normalize_job_id(job_name)
        if job_id not in self.G:
            return []

        paths = []

        def _dfs(current: str, node_chain: list, edge_chain: list):
            if len(node_chain) > max_depth + 1:
                return
            # 记录每条长度 ≥ 2 的路径
            if len(edge_chain) >= 1:
                paths.append({
                    "nodes": [self.get_job_info(n) for n in node_chain],
                    "transitions": list(edge_chain),
                })
            for _, neighbor, data in self.G.out_edges(current, data=True):
                if data.get("type") == "PROMOTES_TO" and neighbor not in node_chain:
                    edge_chain.append({
                        "from": current.replace("job_", "") if current.startswith("job_") else current,
                        "to": neighbor.replace("job_", "") if neighbor.startswith("job_") else neighbor,
                        "years": data.get("years", ""),
                        "description": data.get("description", ""),
                    })
                    node_chain.append(neighbor)
                    _dfs(neighbor, node_chain, edge_chain)
                    node_chain.pop()
                    edge_chain.pop()

        _dfs(job_id, [job_id], [])
        return sorted(paths, key=lambda x: len(x["nodes"]))
    
    def get_transfer_paths(self, job_name: str) -> List[Dict]:
        """
        获取换岗路径
        返回: [{"target": str, "match_level": str, "advantage": str, "need_learn": str}]
        """
        job_id = self._normalize_job_id(job_name)
        if job_id not in self.G:
            return []
        
        paths = []
        for _, target, data in self.G.out_edges(job_id, data=True):
            if data.get("type") == "CAN_TRANSFER_TO":
                target_name = target.replace("job_", "") if target.startswith("job_") else target
                paths.append({
                    "target": target_name,
                    "match_level": data.get("match_level", "中"),
                    "overlap_pct": data.get("overlap_pct", 0.5),
                    "advantage": data.get("advantage", ""),
                    "need_learn": data.get("need_learn", ""),
                    "target_info": self.get_job_info(target),
                })
        
        return sorted(paths, key=lambda x: x["overlap_pct"], reverse=True)
    
    def expand_skills_semantic(
        self,
        skills: List[str],
        threshold: float = 0.6,
        verified_only: bool = False
    ) -> List[Dict]:
        """
        语义技能扩展 (I1核心功能)
        输入: 学生技能列表
        返回: [{"student_skill": str, "expanded_skills": [str], "similarity": float}]
        
        注意：此方法需要配合技能语义边(SIMILAR_TO)使用
        verified_only: 只使用已验证的语义边(verified=True)，避免误匹配
        """
        expanded = []
        for skill in skills:
            skill_node = f"skill_{skill}"
            if skill_node in self.G:
                similar_skills = []
                for _, neighbor, data in self.G.out_edges(skill_node, data=True):
                    if data.get("type") == "SIMILAR_TO":
                        if verified_only and not data.get("verified", False):
                            continue
                        sim = data.get("similarity", 0)
                        if sim >= threshold:
                            similar_skills.append({
                                "skill": neighbor.replace("skill_", ""),
                                "similarity": sim,
                            })
                expanded.append({
                    "student_skill": skill,
                    "expanded_skills": similar_skills,
                })
            else:
                expanded.append({
                    "student_skill": skill,
                    "expanded_skills": [],
                })
        
        return expanded
    
    def get_all_paths(self, job_name: str) -> dict:
        """
        获取岗位的所有路径信息（用于I5可视化）
        返回: {"nodes": [...], "edges": [...], "promotion_paths": [...], "transfer_paths": [...]}
        """
        job_id = self._normalize_job_id(job_name)
        if job_id not in self.G:
            return {"nodes": [], "edges": [], "promotion_paths": [], "transfer_paths": []}
        
        nodes = [{"id": job_id, **self.get_job_info(job_name)}]
        edges = []
        
        promotion_paths = self.get_promotion_paths(job_name)
        for path in promotion_paths:
            for node in path["nodes"]:
                if node and node.get("title") not in [n.get("title") for n in nodes]:
                    nodes.append({"id": node.get("title"), **node})
            for trans in path["transitions"]:
                edges.append({
                    "from": trans["from"],
                    "to": trans["to"],
                    "type": "PROMOTES_TO",
                    "label": trans.get("years", ""),
                })
        
        transfer_paths = self.get_transfer_paths(job_name)
        for tp in transfer_paths:
            target_info = tp.get("target_info")
            if target_info and target_info.get("title") not in [n.get("title") for n in nodes]:
                nodes.append({"id": target_info.get("title"), **target_info})
            edges.append({
                "from": job_id,
                "to": tp["target"],
                "type": "CAN_TRANSFER_TO",
                "label": tp.get("match_level", ""),
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "promotion_paths": promotion_paths,
            "transfer_paths": transfer_paths,
        }
    
    def build_career_timeline(self, job_name: str, years: int = 10) -> dict:
        """
        构建10年职业蓝图（用于I5时间轴）
        返回: {"salary_curve": [...], "milestones": [...]}
        """
        paths = self.get_promotion_paths(job_name)
        
        if not paths:
            return {
                "salary_curve": [0] * (years + 1),
                "milestones": [],
            }
        
        main_path = paths[0]
        salary_curve = []
        milestones = []
        
        job_info = self.get_job_info(job_name)
        current_salary = self._parse_salary(job_info.get("salary", "0") if job_info else "0")
        
        for year in range(years + 1):
            for i, trans in enumerate(main_path["transitions"]):
                years_required = self._parse_years(trans.get("years", "2-3年"))
                if year >= years_required:
                    target_info = self.get_job_info(trans["to"])
                    if target_info:
                        current_salary = self._parse_salary(target_info.get("salary", str(current_salary)))
                        if i < len(milestones) or not milestones:
                            milestones.append({
                                "year": year,
                                "job": trans["to"],
                                "description": trans.get("description", ""),
                            })
            
            salary_curve.append(current_salary)
        
        return {
            "salary_curve": salary_curve,
            "milestones": milestones,
        }
    
    def _parse_salary(self, salary_str: str) -> float:
        """解析薪资字符串，返回月薪(千元)
        支持格式：'1.5-3万14薪'、'8000-12000元'、'1-1.3万'、'面议' 等
        """
        if not salary_str or salary_str.strip() in ("面议", "待定", ""):
            return 0
        import re
        s = salary_str.strip()

        # 匹配 "X-Y万" 格式（如 "1.5-3万", "1-1.3万14薪"）
        m = re.search(r'([\d.]+)[^\d.]*([\d.]+)\s*万', s)
        if m:
            low, high = float(m.group(1)), float(m.group(2))
            return round((low + high) / 2 * 10, 1)

        # 匹配单个万值 "X万"
        m = re.search(r'([\d.]+)\s*万', s)
        if m:
            return round(float(m.group(1)) * 10, 1)

        # 匹配 "X-Y元" 格式（如 "8000-12000元"）
        m = re.search(r'(\d+)[^\d]+(\d+)\s*元', s)
        if m:
            low, high = int(m.group(1)), int(m.group(2))
            return round((low + high) / 2 / 1000, 1)

        # 匹配纯数字范围（如 "8000-12000"，"9-18k"）
        s_normalized = re.sub(r'[kK]', '000', s)
        m = re.search(r'(\d+)[^\d]+(\d+)', s_normalized)
        if m:
            low, high = int(m.group(1)), int(m.group(2))
            avg = (low + high) / 2
            return round(avg / 1000 if avg > 1000 else avg, 1)

        # 单个数字
        m = re.search(r'([\d.]+)', s)
        if m:
            v = float(m.group(1))
            return round(v / 1000 if v > 100 else v, 1)

        return 0
    
    def _parse_years(self, years_str: str) -> int:
        """解析年限字符串，返回年数"""
        if not years_str:
            return 3
        import re
        nums = re.findall(r'\d+', years_str)
        if nums:
            return int(nums[0])
        return 3
    
    def get_jobs_by_industry_category(self, category: str, limit: int = 20) -> List[Dict]:
        """按行业分类获取岗位列表"""
        results = []
        for node_id in self.G.nodes():
            node_data = self.G.nodes[node_id]
            if node_data.get("industry_category") == category:
                results.append({
                    "id": node_id,
                    "title": node_data.get("title", ""),
                    "industry": node_data.get("industry", ""),
                    "industry_category": node_data.get("industry_category", ""),
                    "salary": node_data.get("salary", ""),
                    "market_heat": node_data.get("market_heat", 5),
                })
            if len(results) >= limit:
                break
        return sorted(results, key=lambda x: x.get("market_heat", 0), reverse=True)
    
    def get_jobs_by_market_heat(self, min_heat: int = 1, max_heat: int = 10, limit: int = 20) -> List[Dict]:
        """按市场热度获取岗位列表"""
        results = []
        for node_id in self.G.nodes():
            node_data = self.G.nodes[node_id]
            heat = node_data.get("market_heat", 5)
            if min_heat <= heat <= max_heat:
                results.append({
                    "id": node_id,
                    "title": node_data.get("title", ""),
                    "industry": node_data.get("industry", ""),
                    "industry_category": node_data.get("industry_category", ""),
                    "salary": node_data.get("salary", ""),
                    "market_heat": heat,
                })
        results.sort(key=lambda x: x["market_heat"], reverse=True)
        return results[:limit]
    
    def get_skill_requirements(self, job_name: str) -> Dict:
        """获取岗位的技能需求层级"""
        job_id = self._normalize_job_id(job_name)
        if job_id not in self.G:
            return {"required_skills": [], "preferred_skills": [], "bonus_skills": []}
        
        node_data = self.G.nodes[job_id]
        return {
            "required_skills": node_data.get("required_skills", []),
            "preferred_skills": node_data.get("preferred_skills", []),
            "bonus_skills": node_data.get("bonus_skills", []),
        }
    
    def get_all_industry_categories(self) -> List[str]:
        """获取所有行业分类"""
        categories = set()
        for node_id in self.G.nodes():
            cat = self.G.nodes[node_id].get("industry_category", "")
            if cat:
                categories.add(cat)
        return sorted(list(categories))
    
    def get_hot_jobs(self, top_n: int = 10) -> List[Dict]:
        """获取热门岗位（按市场热度排序）"""
        return self.get_jobs_by_market_heat(min_heat=7, max_heat=10, limit=top_n)

    def get_valid_jobs(self) -> List[str]:
        """获取有效岗位列表（过滤掉无描述的空壳节点）"""
        valid_jobs = []
        for node_id in self.G.nodes():
            if not node_id.startswith("job_"):
                continue
            node_data = self.G.nodes[node_id]
            if node_data.get("overview") or node_data.get("skills"):
                title = node_data.get("title", node_id.replace("job_", ""))
                valid_jobs.append(title)
        return sorted(valid_jobs)

    def search_jobs(self, query: str, limit: int = 10) -> List[Dict]:
        """模糊搜索岗位（仅返回有效岗位）"""
        results = []
        query_lower = query.lower()
        
        for node_id in self.G.nodes():
            if not node_id.startswith("job_"):
                continue
            node_data = self.G.nodes[node_id]
            if not (node_data.get("overview") or node_data.get("skills")):
                continue
            
            title = node_data.get("title", "")
            if query_lower in title.lower():
                results.append({
                    "id": node_id,
                    "title": title,
                    "industry": node_data.get("industry", ""),
                    "industry_category": node_data.get("industry_category", ""),
                    "salary": node_data.get("salary", ""),
                    "market_heat": node_data.get("market_heat", 5),
                })
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_main_with_transfers(self, job_name: str) -> Dict:
        """
        任务专用：主节点 + 直接换岗派生节点（用于简历换岗展示）
        返回: {"main": JobInfo, "transfers": List[TransferPath], "graph": {"nodes": [...], "edges": [...]}}
        """
        job_id = self._normalize_job_id(job_name)
        if job_id not in self.G:
            return {"main": None, "transfers": [], "graph": {"nodes": [], "edges": []}}
        
        main_info = self.get_job_info(job_name)
        transfers = self.get_transfer_paths(job_name)
        
        # 构建最小图：主节点 + 直接换岗子节点
        nodes = [{"id": job_id, **(main_info or {})}]
        edges = []
        
        for i, tf in enumerate(transfers[:5]):  # 限制最多5个，避免图过密
            tf_id = self._normalize_job_id(tf["target"])
            tf_info = self.get_job_info(tf["target"])
            if tf_info:
                nodes.append({"id": tf_id, **tf_info})
                edges.append({
                    "from": job_id,
                    "to": tf_id,
                    "type": "CAN_TRANSFER_TO",
                    "label": tf["match_level"],
                    "data": tf  # 完整换岗信息 (advantage, need_learn 用于gap分析)
                })
        
        return {
            "main": main_info,
            "transfers": transfers[:5],  # 前5个匹配度最高的
            "graph": {"nodes": nodes, "edges": edges}
        }


    def get_career_paths(self, job_name: str) -> Dict[str, Any]:
        """获取岗位的职业路径（晋升+换岗）"""
        promotion_paths = self.get_promotion_paths(job_name)
        transfer_paths = self.get_transfer_paths(job_name)
        
        formatted_promotions = []
        for path in promotion_paths:
            nodes = []
            for node in path.get("nodes", []):
                if node:
                    nodes.append({
                        "title": node.get("title", ""),
                        "salary": node.get("salary", ""),
                    })
            if nodes:
                formatted_promotions.append({"nodes": nodes})
        
        formatted_transfers = []
        for tp in transfer_paths:
            formatted_transfers.append({
                "target": tp.get("target", ""),
                "match_level": tp.get("match_level", "中"),
                "overlap_pct": tp.get("overlap_pct", 0.5),
                "advantage": tp.get("advantage", ""),
                "need_learn": tp.get("need_learn", ""),
            })
        
        return {
            "promotion_paths": formatted_promotions,
            "transfer_paths": formatted_transfers,
        }


job_graph = JobGraphRepo()
