# -*- coding: utf-8 -*-
"""
准确率服务（���局单例）

职责：
1. 启动时从 data/eval/confidence_cal.json 加载置信度校准数据
2. 为匹配/���像 API 提供 accuracy_metadata（嵌入实����应）
3. 记录生产匹配事件到 data/eval/production_log.jsonl（��离线分析）
4. ��数据库 FeedbackModel + MatchResultModel 更新校准（结合真实用户反馈）
5. 计算简历字段置信度（供画像 API 使用）

调用方式：
    from app.services.accuracy_service import accuracy_service
    meta = accuracy_service.get_accuracy_metadata(confidence=0.82, industry="技术")
    accuracy_service.log_match_event(student_id, job_name, industry, confidence, ...)
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

_EVAL_DIR = Path(__file__).parent.parent.parent / "data" / "eval"
_CAL_FILE = _EVAL_DIR / "confidence_cal.json"
_PROD_LOG = _EVAL_DIR / "production_log.jsonl"

# 行业→置信度阈值（��于此值需提示复核）
_INDUSTRY_REVIEW_THRESHOLDS: Dict[str, float] = {
    "技术":   0.65,
    "运营":   0.55,
    "销售":   0.50,
    "产品":   0.55,
    "行政":   0.50,
    "人力资源": 0.50,
    "金融":   0.55,
    "其他":   0.50,
}

# 字段→基线置信度（没有 LLM 参与时的���则层置信度）
_FIELD_BASE_CONFIDENCE: Dict[str, float] = {
    "name":    0.95,   # 姓名：规则提��，准确率高
    "school":  0.92,   # 学校：关键词匹配
    "major":   0.88,   # 专业：关键词匹配
    "degree":  0.85,   # 学历：枚举匹配
    "skills":  0.80,   # 技能列表：规则+LLM，变化��
    "gpa":     0.82,   # 成绩：数���提取
    "internship_company": 0.78,   # 实习公司名
    "internship_duration": 0.72,  # 实习时长：有 null 风险
    "projects": 0.70,             # 项目描述：LLM推断
    "soft_skills": 0.65,          # 软技能：纯 LLM 推断
    "career_intent": 0.68,        # 求��意向：推断
}


class AccuracyService:
    """全局准确率服务（应用启动时实例化一次）"""

    def __init__(self):
        self._calibration: Dict[str, Dict] = {}
        self._industry_calibration: Dict[str, Dict] = {}
        self._reload_calibration()
        logger.info("[AccuracyService] 初始化完成，校准��: %s", list(self._calibration.keys()))

    # ── 校准数据加载 ──────────────────────────────────────────────────────────

    def _reload_calibration(self):
        """从文件加载置信度校准数据"""
        try:
            if _CAL_FILE.exists():
                with open(_CAL_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                self._calibration = data.get("buckets", {})
                self._industry_calibration = data.get("industry_buckets", {})
        except Exception as e:
            logger.warning("[AccuracyService] 加载校准文件失败: %s", e)

    # ── 核心 API：生成 accuracy_metadata ─────────────────────────────────────

    def get_accuracy_metadata(
        self,
        confidence: float,
        industry: str = "其他",
        field_type: str = "skill_match",
    ) -> Dict[str, Any]:
        """
        为 API 响应生成 accuracy_metadata ���典。
        调用方将其���接嵌入 MatchResult 或 StudentPortrait 的对应字段。

        Returns:
            {
                "confidence_bucket": "high" | "mid" | "low",
                "empirical_accuracy": float | None,  # None = 无��够样本
                "industry": str,
                "review_flag": bool,        # True = 建议人��复核
                "review_reason": str,       # 复核原因（若 review_flag=True）
                "sample_size": int,         # 经���值来自的样本数
            }
        """
        if confidence >= 0.8:
            bucket = "high"
        elif confidence >= 0.6:
            bucket = "mid"
        else:
            bucket = "low"

        # 优先使用行业细分校准，降��为全局校准
        ind_buckets = self._industry_calibration.get(industry, {})
        ind_info = ind_buckets.get(bucket, {})
        global_info = self._calibration.get(bucket, {})

        empirical = ind_info.get("empirical_accuracy") or global_info.get("empirical_accuracy")
        sample_size = ind_info.get("n", 0) + global_info.get("n", 0)

        # 低样本时������示经验准确率（���免误导）
        if sample_size < 5:
            empirical = None

        # 复核判断
        threshold = _INDUSTRY_REVIEW_THRESHOLDS.get(industry, 0.55)
        review_flag = confidence < threshold
        review_reason = ""
        if confidence < 0.4:
            review_reason = "置信度极低，简历信息可能不完整"
        elif confidence < threshold:
            review_reason = f"低于{industry}行业推荐置信度阈值（{threshold:.0%}），��议核对关键技能"

        return {
            "confidence_bucket": bucket,
            "empirical_accuracy": empirical,
            "industry": industry,
            "review_flag": review_flag,
            "review_reason": review_reason,
            "sample_size": sample_size,
        }

    def get_field_confidence(
        self,
        field_name: str,
        value: Any,
        extraction_method: str = "rule",
    ) -> float:
        """
        计算画像字段置信度。

        Args:
            field_name:  字段名（name / skills / internship_duration 等）
            value:       字段值（��于完���性判断）
            extraction_method: "rule" | "llm" | "user_input"

        Returns:
            0.0-1.0 的置信度
        """
        base = _FIELD_BASE_CONFIDENCE.get(field_name, 0.70)

        # 值为空 ��� 极低置信度
        if value is None or value == "" or value == [] or value == {}:
            return 0.10

        # 用户手动输入 → 最高置信度
        if extraction_method == "user_input":
            return min(base + 0.05, 1.0)

        # LLM 推断 → ���低��规则
        if extraction_method == "llm":
            return base * 0.92

        # 列表类型：长度影响置信度
        if isinstance(value, list):
            if len(value) == 0:
                return 0.10
            if len(value) >= 3:
                return min(base + 0.05, 1.0)

        return base

    def compute_portrait_field_confidence(self, portrait_data: dict) -> Dict[str, float]:
        """
        批量计算画像所有字段的置信度。
        portrait_data 为 StudentPortrait dict 或 StudentModel JSON fields。

        Returns: {field_name: confidence}
        """
        basic = portrait_data.get("basic_info") or {}
        result = {
            "name":    self.get_field_confidence("name", basic.get("name")),
            "school":  self.get_field_confidence("school", basic.get("school")),
            "major":   self.get_field_confidence("major", basic.get("major")),
            "degree":  self.get_field_confidence("degree", basic.get("degree") or portrait_data.get("education")),
            "skills":  self.get_field_confidence("skills", portrait_data.get("skills")),
            "internship_duration": self.get_field_confidence(
                "internship_duration",
                portrait_data.get("internships"),
                extraction_method="llm",
            ),
            "projects": self.get_field_confidence(
                "projects",
                portrait_data.get("projects"),
                extraction_method="llm",
            ),
            "soft_skills": self.get_field_confidence(
                "soft_skills",
                portrait_data.get("inferred_soft_skills"),
                extraction_method="llm",
            ),
            "career_intent": self.get_field_confidence(
                "career_intent",
                portrait_data.get("career_intent"),
                extraction_method="llm",
            ),
        }
        return result

    # ── 生产日志记录（���步安全，buffered write） ───────────────────────────────

    def log_match_event(
        self,
        student_id: str,
        job_name: str,
        industry: str,
        confidence: float,
        matched_count: int,
        gap_count: int,
        overall_score: float,
        result_id: Optional[str] = None,
    ) -> None:
        """
        记录一次生产匹配事件到 production_log.jsonl。
        非阻塞写入（忽略IO错误）。
        """
        try:
            _EVAL_DIR.mkdir(exist_ok=True)
            record = {
                "ts": datetime.utcnow().isoformat(),
                "student_id": student_id,
                "job_name": job_name,
                "industry": industry,
                "confidence": round(confidence, 3),
                "matched_count": matched_count,
                "gap_count": gap_count,
                "overall_score": round(overall_score, 1),
                "result_id": result_id,
            }
            with open(_PROD_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # 日志写入不影响主流程

    # ── 从数据库反馈更新校准（供定时任务调用） ───────────────────────────────

    async def update_calibration_from_db(self, db_session) -> Dict[str, Any]:
        """
        从 DB 的 FeedbackModel + MatchResultModel 计算真实用户满意度，
        更新 confidence_cal.json 中的校准数据。

        逻辑：
        - 对每条 feedback(rating=1/0)，关联对应的 match confidence
        - 按��信度桶统计「满意率」作为经验准确率
        - 同时按行业分组
        - 最小样本 ≥ 3 才写入（否则保留旧值）

        Returns: 更新后的校准统计摘要
        """
        from sqlalchemy import select
        from app.db.models import FeedbackModel, MatchResultModel

        try:
            # 获取所有 match 类型的反馈 + 对应 confidence
            stmt = (
                select(FeedbackModel.rating, MatchResultModel.confidence, MatchResultModel.job_name)
                .join(MatchResultModel, MatchResultModel.result_id == FeedbackModel.target_id)
                .where(FeedbackModel.target_type == "match")
            )
            rows = (await db_session.execute(stmt)).all()
        except Exception as e:
            logger.warning("[AccuracyService] DB查询失败: %s", e)
            return {}

        if not rows:
            return {"message": "暂无用户反馈数据"}

        # 按置信度桶统计
        bucket_data: Dict[str, List[int]] = {"high": [], "mid": [], "low": []}
        for rating, conf, job_name in rows:
            conf = conf or 0.0
            if conf >= 0.8:
                bucket_data["high"].append(rating)
            elif conf >= 0.6:
                bucket_data["mid"].append(rating)
            else:
                bucket_data["low"].append(rating)

        # 获取行业信息（job_name → industry 映射）
        industry_bucket_data: Dict[str, Dict[str, List[int]]] = {}
        try:
            job_industry_map = self._load_job_industry_map()
            for rating, conf, job_name in rows:
                industry = job_industry_map.get(job_name, "其他")
                conf = conf or 0.0
                bucket = "high" if conf >= 0.8 else ("mid" if conf >= 0.6 else "low")
                industry_bucket_data.setdefault(industry, {}).setdefault(bucket, []).append(rating)
        except Exception:
            pass

        # 计算满意率作为经验准确率
        new_buckets = {}
        for bucket, ratings in bucket_data.items():
            if len(ratings) >= 3:
                new_buckets[bucket] = {
                    "n": len(ratings),
                    "empirical_accuracy": round(sum(ratings) / len(ratings), 4),
                    "min_accuracy": None,  # 满意率不适用 min_accuracy
                    "source": "db_feedback",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            else:
                # 保留旧校准值
                new_buckets[bucket] = self._calibration.get(bucket, {})

        new_industry_buckets = {}
        for industry, buckets in industry_bucket_data.items():
            new_industry_buckets[industry] = {}
            for bucket, ratings in buckets.items():
                if len(ratings) >= 3:
                    new_industry_buckets[industry][bucket] = {
                        "n": len(ratings),
                        "empirical_accuracy": round(sum(ratings) / len(ratings), 4),
                        "source": "db_feedback",
                    }

        # 写入文件
        try:
            existing = {}
            if _CAL_FILE.exists():
                with open(_CAL_FILE, encoding="utf-8") as f:
                    existing = json.load(f)
            existing["buckets"] = new_buckets
            existing["industry_buckets"] = new_industry_buckets
            existing["_feedback_updated"] = datetime.utcnow().isoformat()
            existing["_feedback_count"] = len(rows)
            with open(_CAL_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            self._reload_calibration()
            logger.info("[AccuracyService] 从DB反馈更新校准完成，共%d条反馈", len(rows))
        except Exception as e:
            logger.error("[AccuracyService] 写入校准文件失败: %s", e)

        return {
            "feedback_count": len(rows),
            "buckets_updated": {k: v.get("n", 0) for k, v in new_buckets.items()},
        }

    @staticmethod
    def _load_job_industry_map() -> Dict[str, str]:
        """��� job_profiles.json 加载 job_name → industry 映射"""
        profiles_path = Path(__file__).parent.parent.parent / "data" / "job_profiles.json"
        result = {}
        try:
            with open(profiles_path, encoding="utf-8") as f:
                profiles = json.load(f)
            for p in profiles:
                name = p.get("岗位名称", "")
                industry = p.get("行业分类", p.get("所属行业", "其他"))
                if name:
                    result[name] = industry
        except Exception:
            pass
        return result

    # ── 统计摘要（供 /health 或 admin 端点调用） ─────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """返回当前校准数据摘要"""
        prod_log_lines = 0
        try:
            if _PROD_LOG.exists():
                prod_log_lines = sum(1 for _ in open(_PROD_LOG, encoding="utf-8"))
        except Exception:
            pass
        return {
            "calibration_buckets": list(self._calibration.keys()),
            "industry_calibrations": list(self._industry_calibration.keys()),
            "production_log_entries": prod_log_lines,
            "cal_file": str(_CAL_FILE),
        }


# ── 全局单例 ───────────────────────────────────────────────────────────────────

accuracy_service = AccuracyService()
