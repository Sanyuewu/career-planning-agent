# -*- coding: utf-8 -*-
"""
学生CRUD操作
遵循v5规范：C4约束 - 所有数据库操作封装在crud层
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StudentModel


class StudentCRUD:
    """学生数据访问层"""
    
    async def create(
        self, 
        session: AsyncSession, 
        student_data: dict
    ) -> StudentModel:
        """创建学生记录"""
        student = StudentModel(**student_data)
        session.add(student)
        await session.flush()
        return student
    
    async def get_by_student_id(
        self, 
        session: AsyncSession, 
        student_id: str
    ) -> Optional[StudentModel]:
        """根据student_id获取学生"""
        stmt = select(StudentModel).where(StudentModel.student_id == student_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(
        self, 
        session: AsyncSession, 
        id: int
    ) -> Optional[StudentModel]:
        """根据id获取学生"""
        return await session.get(StudentModel, id)
    
    async def update(
        self, 
        session: AsyncSession, 
        student_id: str, 
        update_data: dict
    ) -> Optional[StudentModel]:
        """更新学生信息"""
        student = await self.get_by_student_id(session, student_id)
        if not student:
            return None
        
        for key, value in update_data.items():
            if hasattr(student, key):
                setattr(student, key, value)
        
        await session.flush()
        return student
    
    async def delete(
        self, 
        session: AsyncSession, 
        student_id: str
    ) -> bool:
        """删除学生"""
        student = await self.get_by_student_id(session, student_id)
        if not student:
            return False
        
        await session.delete(student)
        return True
    
    async def list_all(
        self, 
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[StudentModel]:
        """获取学生列表"""
        stmt = select(StudentModel).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_by_name(
        self, 
        session: AsyncSession, 
        name: str
    ) -> List[StudentModel]:
        """根据姓名搜索"""
        stmt = select(StudentModel).where(StudentModel.name.ilike(f"%{name}%"))
        result = await session.execute(stmt)
        return list(result.scalars().all())


student_crud = StudentCRUD()
