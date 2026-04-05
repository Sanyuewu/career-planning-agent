# -*- coding: utf-8 -*-
"""
测评结果 CRUD（D-4）
双写：students.ability_profile（兼容现有代码）+ assessment_results 表（支持统计分析）
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import AssessmentResultModel
import logging

logger = logging.getLogger(__name__)


class AssessmentResultCRUD:

    async def create(
        self,
        db: AsyncSession,
        student_id: str,
        assessment_type: str,
        job_hint: str,
        scores: Dict[str, Any],
        total_score: float,
        result_label: str = "",
    ) -> AssessmentResultModel:
        row = AssessmentResultModel(
            student_id=student_id,
            assessment_type=assessment_type,
            job_hint=job_hint,
            scores=scores,
            total_score=total_score,
            result_label=result_label,
            submitted_at=datetime.utcnow(),
        )
        db.add(row)
        await db.flush()
        return row

    async def get_by_student(
        self,
        db: AsyncSession,
        student_id: str,
        assessment_type: Optional[str] = None,
    ) -> List[AssessmentResultModel]:
        q = select(AssessmentResultModel).where(
            AssessmentResultModel.student_id == student_id
        )
        if assessment_type:
            q = q.where(AssessmentResultModel.assessment_type == assessment_type)
        q = q.order_by(AssessmentResultModel.submitted_at.desc())
        result = await db.execute(q)
        return list(result.scalars().all())

    async def get_stats(self, db: AsyncSession, assessment_type: str) -> Dict[str, Any]:
        """管理员统计：平均分/人数（D-4）"""
        q = select(
            func.count(AssessmentResultModel.id).label("count"),
            func.avg(AssessmentResultModel.total_score).label("avg_score"),
        ).where(AssessmentResultModel.assessment_type == assessment_type)
        result = await db.execute(q)
        row = result.one()
        return {
            "count": row.count or 0,
            "avg_score": round(row.avg_score or 0, 1),
            "assessment_type": assessment_type,
        }


assessment_result_crud = AssessmentResultCRUD()
