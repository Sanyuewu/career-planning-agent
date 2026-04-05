# -*- coding: utf-8 -*-
"""
画像历史CRUD操作
遵循v5.1规范
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.models import PortraitHistoryModel, StudentModel


class PortraitHistoryCRUD:
    """画像历史数据访问层"""
    
    def _generate_snapshot_id(self) -> str:
        return f"snapshot_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    
    async def create_snapshot(
        self,
        session: AsyncSession,
        student_id: str,
        portrait: dict,
        completeness: float,
        competitiveness: float,
        snapshot_reason: str = None,
        diff_summary: dict = None
    ) -> PortraitHistoryModel:
        max_version = await self.get_max_version(session, student_id)
        version = (max_version or 0) + 1
        
        snapshot = PortraitHistoryModel(
            snapshot_id=self._generate_snapshot_id(),
            student_id=student_id,
            version=version,
            portrait=portrait,
            completeness=completeness,
            competitiveness=competitiveness,
            snapshot_reason=snapshot_reason,
            diff_summary=diff_summary or {},
            created_at=datetime.utcnow(),
        )
        
        session.add(snapshot)
        await session.flush()
        await session.refresh(snapshot)
        return snapshot
    
    async def get_max_version(
        self,
        session: AsyncSession,
        student_id: str
    ) -> Optional[int]:
        stmt = select(func.max(PortraitHistoryModel.version)).where(
            PortraitHistoryModel.student_id == student_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_history(
        self,
        session: AsyncSession,
        student_id: str,
        limit: int = 10
    ) -> List[PortraitHistoryModel]:
        stmt = (
            select(PortraitHistoryModel)
            .where(PortraitHistoryModel.student_id == student_id)
            .order_by(PortraitHistoryModel.version.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest(
        self,
        session: AsyncSession,
        student_id: str
    ) -> Optional[PortraitHistoryModel]:
        stmt = (
            select(PortraitHistoryModel)
            .where(PortraitHistoryModel.student_id == student_id)
            .order_by(PortraitHistoryModel.version.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_version(
        self,
        session: AsyncSession,
        student_id: str,
        version: int
    ) -> Optional[PortraitHistoryModel]:
        stmt = select(PortraitHistoryModel).where(
            PortraitHistoryModel.student_id == student_id,
            PortraitHistoryModel.version == version,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def delete_old_snapshots(
        self,
        session: AsyncSession,
        student_id: str,
        keep_count: int = 10
    ) -> int:
        history = await self.get_history(session, student_id, limit=1000)
        if len(history) <= keep_count:
            return 0
        
        to_delete = history[keep_count:]
        for snapshot in to_delete:
            await session.delete(snapshot)
        
        await session.flush()
        return len(to_delete)


portrait_history_crud = PortraitHistoryCRUD()
