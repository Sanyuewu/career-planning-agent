# -*- coding: utf-8 -*-
"""
用户长期记忆 CRUD（A-4）
跨会话持久化：职业目标 / 担忧 / 优势 / 偏好
"""

from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserMemoryModel


class UserMemoryCRUD:

    @staticmethod
    async def upsert(
        session: AsyncSession,
        student_id: str,
        memory_key: str,
        memory_value: str,
        source_session: Optional[str] = None,
        confidence: float = 1.0,
    ) -> None:
        """插入或更新单条记忆"""
        existing = await session.scalar(
            select(UserMemoryModel).where(
                and_(
                    UserMemoryModel.student_id == student_id,
                    UserMemoryModel.memory_key == memory_key,
                )
            )
        )
        if existing:
            existing.memory_value = memory_value
            existing.source_session = source_session
            existing.confidence = confidence
            existing.updated_at = datetime.utcnow()
        else:
            session.add(UserMemoryModel(
                student_id=student_id,
                memory_key=memory_key,
                memory_value=memory_value,
                source_session=source_session,
                confidence=confidence,
            ))
        await session.commit()

    @staticmethod
    async def get_all(session: AsyncSession, student_id: str) -> Dict[str, str]:
        """获取某学生全部记忆，返回 {key: value}"""
        rows = (await session.execute(
            select(UserMemoryModel).where(UserMemoryModel.student_id == student_id)
        )).scalars().all()
        return {r.memory_key: r.memory_value for r in rows}

    @staticmethod
    async def delete_key(session: AsyncSession, student_id: str, memory_key: str) -> None:
        await session.execute(
            delete(UserMemoryModel).where(
                and_(
                    UserMemoryModel.student_id == student_id,
                    UserMemoryModel.memory_key == memory_key,
                )
            )
        )
        await session.commit()
