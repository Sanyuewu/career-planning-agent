# -*- coding: utf-8 -*-
"""
对话会话CRUD操作
遵循v5规范：C4约束 - 所有数据库操作封装在crud层
"""

from typing import Optional, List
from datetime import datetime
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatSessionModel


class ChatSessionCRUD:
    """对话会话数据访问层"""
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"chat_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    async def create(
        self, 
        session: AsyncSession, 
        student_id: str = None
    ) -> ChatSessionModel:
        """创建对话会话"""
        chat_session = ChatSessionModel(
            session_id=self._generate_session_id(),
            student_id=student_id,
            state="GREETING",
            messages=[],
            emotion_history=[],
            emotion_score=1.0,
            turn_count=0
        )
        session.add(chat_session)
        await session.flush()
        return chat_session
    
    async def get_by_session_id(
        self, 
        session: AsyncSession, 
        session_id: str
    ) -> Optional[ChatSessionModel]:
        """根据session_id获取会话"""
        stmt = select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update(
        self, 
        session: AsyncSession, 
        session_id: str,
        update_data: dict
    ) -> Optional[ChatSessionModel]:
        """更新会话状态"""
        chat_session = await self.get_by_session_id(session, session_id)
        if not chat_session:
            return None
        
        for key, value in update_data.items():
            if hasattr(chat_session, key):
                setattr(chat_session, key, value)
        
        await session.flush()
        return chat_session
    
    async def add_message(
        self, 
        session: AsyncSession, 
        session_id: str,
        message: dict
    ) -> Optional[ChatSessionModel]:
        """添加消息"""
        chat_session = await self.get_by_session_id(session, session_id)
        if not chat_session:
            return None
        
        messages = chat_session.messages or []
        messages.append(message)
        chat_session.messages = messages
        chat_session.turn_count = len([m for m in messages if m.get("role") == "user"])
        
        await session.flush()
        return chat_session
    
    async def add_emotion_record(
        self, 
        session: AsyncSession, 
        session_id: str,
        emotion_record: dict
    ) -> Optional[ChatSessionModel]:
        """添加情绪记录"""
        chat_session = await self.get_by_session_id(session, session_id)
        if not chat_session:
            return None
        
        history = chat_session.emotion_history or []
        history.append(emotion_record)
        chat_session.emotion_history = history
        chat_session.current_emotion = emotion_record.get("emotion")
        chat_session.emotion_score = emotion_record.get("score", 1.0)
        
        await session.flush()
        return chat_session
    
    async def get_by_student(
        self, 
        session: AsyncSession, 
        student_id: str,
        limit: int = 10
    ) -> List[ChatSessionModel]:
        """获取学生的所有会话"""
        stmt = (
            select(ChatSessionModel)
            .where(ChatSessionModel.student_id == student_id)
            .order_by(ChatSessionModel.updated_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def delete(
        self, 
        session: AsyncSession, 
        session_id: str
    ) -> bool:
        """删除会话"""
        chat_session = await self.get_by_session_id(session, session_id)
        if not chat_session:
            return False
        
        await session.delete(chat_session)
        return True


chat_session_crud = ChatSessionCRUD()
