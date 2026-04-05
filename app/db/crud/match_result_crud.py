# -*- coding: utf-8 -*-
"""
匹配结果CRUD操作
遵循v5规范：C4约束 - 所有数据库操作封装在crud层
"""

from typing import Optional, List
from datetime import datetime
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MatchResultModel


class MatchResultCRUD:
    """匹配结果数据访问层"""
    
    def _generate_result_id(self) -> str:
        """生成结果ID"""
        return f"match_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    
    async def create(
        self, 
        session: AsyncSession, 
        student_id: str,
        job_name: str,
        result_data: dict
    ) -> MatchResultModel:
        """创建匹配结果"""
        result = MatchResultModel(
            result_id=self._generate_result_id(),
            student_id=student_id,
            job_name=job_name,
            **result_data
        )
        session.add(result)
        await session.flush()
        return result
    
    async def get_by_result_id(
        self, 
        session: AsyncSession, 
        result_id: str
    ) -> Optional[MatchResultModel]:
        """根据result_id获取结果"""
        stmt = select(MatchResultModel).where(MatchResultModel.result_id == result_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_student(
        self, 
        session: AsyncSession, 
        student_id: str,
        limit: int = 10
    ) -> List[MatchResultModel]:
        """获取学生的所有匹配结果"""
        stmt = (
            select(MatchResultModel)
            .where(MatchResultModel.student_id == student_id)
            .order_by(MatchResultModel.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_by_student_and_job(
        self, 
        session: AsyncSession, 
        student_id: str,
        job_name: str
    ) -> Optional[MatchResultModel]:
        """获取学生对某岗位的最新匹配结果"""
        stmt = (
            select(MatchResultModel)
            .where(
                MatchResultModel.student_id == student_id,
                MatchResultModel.job_name == job_name
            )
            .order_by(MatchResultModel.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def upsert(
        self,
        session: AsyncSession,
        student_id: str,
        job_name: str,
        result_data: dict,
    ) -> MatchResultModel:
        """同一学生+岗位已有记录则更新，否则新建（避免重复记录）"""
        existing = await self.get_latest_by_student_and_job(session, student_id, job_name)
        if existing:
            for key, value in result_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await session.flush()
            return existing
        return await self.create(session, student_id, job_name, result_data)

    async def delete_by_student(
        self, 
        session: AsyncSession, 
        student_id: str
    ) -> int:
        """删除学生的所有匹配结果"""
        results = await self.get_by_student(session, student_id, limit=1000)
        count = 0
        for result in results:
            await session.delete(result)
            count += 1
        return count


match_result_crud = MatchResultCRUD()
