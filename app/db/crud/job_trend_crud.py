# -*- coding: utf-8 -*-
"""
岗位趋势CRUD操作 - I6趋势分析
遵循v5.1规范
"""

from typing import Optional, List
from datetime import date, datetime
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobTrendSnapshotModel


class JobTrendCRUD:
    """岗位趋势数据访问层"""
    
    async def create_snapshot(
        self,
        session: AsyncSession,
        job_code: str,
        snapshot_date: date,
        jd_count: int,
        avg_salary: int,
        demand_index: float,
        top_skills: List[str]
    ) -> JobTrendSnapshotModel:
        """创建趋势快照"""
        snapshot = JobTrendSnapshotModel(
            job_code=job_code,
            snapshot_date=snapshot_date,
            jd_count=jd_count,
            avg_salary=avg_salary,
            demand_index=demand_index,
            top_skills=top_skills,
        )
        session.add(snapshot)
        await session.flush()
        return snapshot
    
    async def get_by_job_code(
        self,
        session: AsyncSession,
        job_code: str,
        limit: int = 4
    ) -> List[JobTrendSnapshotModel]:
        """获取岗位的趋势数据"""
        stmt = (
            select(JobTrendSnapshotModel)
            .where(JobTrendSnapshotModel.job_code == job_code)
            .order_by(JobTrendSnapshotModel.snapshot_date.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_snapshots(
        self,
        session: AsyncSession,
        job_code: str,
        limit: int = 4
    ) -> List[JobTrendSnapshotModel]:
        """获取岗位最近N条趋势快照"""
        stmt = (
            select(JobTrendSnapshotModel)
            .where(JobTrendSnapshotModel.job_code == job_code)
            .order_by(JobTrendSnapshotModel.snapshot_date.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_trend_for_job(
        self,
        session: AsyncSession,
        job_code: str,
        days: int = 30
    ) -> List[JobTrendSnapshotModel]:
        """获取岗位趋势数据（用于TrendChart组件)"""
        stmt = (
            select(JobTrendSnapshotModel)
            .where(JobTrendSnapshotModel.job_code == job_code)
            .order_by(JobTrendSnapshotModel.snapshot_date.desc())
            .limit(days)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_by_job_code(
        self,
        session: AsyncSession,
        job_code: str
    ) -> bool:
        """删除岗位所有趋势快照"""
        stmt = delete(JobTrendSnapshotModel).where(
            JobTrendSnapshotModel.job_code == job_code
        )
        await session.execute(stmt)
        await session.flush()
        return True


job_trend_crud = JobTrendCRUD()
