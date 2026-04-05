# -*- coding: utf-8 -*-
"""
报告CRUD操作
遵循v5规范：C4约束 - 所有数据库操作封装在crud层
"""

from typing import Optional, List
from datetime import datetime
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReportModel


class ReportCRUD:
    """报告数据访问层"""
    
    def _generate_report_id(self) -> str:
        """生成报告ID"""
        return f"report_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    
    async def create(
        self, 
        session: AsyncSession, 
        student_id: str,
        job_name: str
    ) -> ReportModel:
        """创建报告记录"""
        report = ReportModel(
            report_id=self._generate_report_id(),
            student_id=student_id,
            job_name=job_name,
            status="pending"
        )
        session.add(report)
        await session.flush()
        return report
    
    async def get_by_report_id(
        self, 
        session: AsyncSession, 
        report_id: str
    ) -> Optional[ReportModel]:
        """根据report_id获取报告"""
        stmt = select(ReportModel).where(ReportModel.report_id == report_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_content(
        self, 
        session: AsyncSession, 
        report_id: str,
        content: dict,
        status: str = "completed"
    ) -> Optional[ReportModel]:
        """更新报告内容"""
        report = await self.get_by_report_id(session, report_id)
        if not report:
            return None
        
        for key, value in content.items():
            if hasattr(report, key):
                setattr(report, key, value)
        
        report.status = status
        await session.flush()
        return report
    
    async def update_status(
        self,
        session: AsyncSession,
        report_id: str,
        status: str,
        error_message: str = None
    ) -> Optional[ReportModel]:
        """更新报告状态"""
        report = await self.get_by_report_id(session, report_id)
        if not report:
            return None

        report.status = status
        if error_message:
            report.error_message = error_message

        await session.flush()
        return report

    async def update_progress(
        self,
        session: AsyncSession,
        report_id: str,
        progress: int,
        message: str,
    ) -> None:
        """更新报告生成进度（存入 extra_data，不触发状态变更）"""
        report = await self.get_by_report_id(session, report_id)
        if not report:
            return
        extra = dict(report.extra_data or {})
        extra["_progress"] = progress
        extra["_progress_msg"] = message
        report.extra_data = extra
        await session.flush()
    
    async def get_by_student_and_job(
        self,
        session: AsyncSession,
        student_id: str,
        job_name: str,
    ) -> Optional[ReportModel]:
        """获取同一学生+岗位的最新报告（用于幂等生成检查）"""
        stmt = (
            select(ReportModel)
            .where(ReportModel.student_id == student_id)
            .where(ReportModel.job_name == job_name)
            .order_by(ReportModel.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_student(
        self,
        session: AsyncSession,
        student_id: str,
        limit: int = 10
    ) -> List[ReportModel]:
        """获取学生的所有报告"""
        stmt = (
            select(ReportModel)
            .where(ReportModel.student_id == student_id)
            .order_by(ReportModel.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def delete(
        self, 
        session: AsyncSession, 
        report_id: str
    ) -> bool:
        """删除报告"""
        report = await self.get_by_report_id(session, report_id)
        if not report:
            return False
        
        await session.delete(report)
        return True


report_crud = ReportCRUD()
