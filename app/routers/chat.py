# -*- coding: utf-8 -*-
"""对话智能体路由：/api/chat/*"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select as sa_select

from app.db import get_db_session, match_result_crud, chat_session_crud
from app.db.models import ChatSessionModel
from app.deps import get_current_user
from app.schemas.api import ChatMessageRequest, ChatMessageResponse
from app.services.chat_agent_service import chat_agent_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/session")
async def create_chat_session(student_id: Optional[str] = None, match_job_name: Optional[str] = None):
    async with get_db_session() as session:
        db_session = await chat_session_crud.create(session, student_id)

        chat_session = chat_agent_service.create_session(db_session.session_id)
        if student_id:
            chat_session.student_id = student_id
            await chat_agent_service.load_user_memory(chat_session)

        if student_id and match_job_name:
            try:
                match_rows = await match_result_crud.get_by_student(session, student_id, limit=50)
                target = next((r for r in match_rows if r.job_name == match_job_name), None)
                if not target and match_rows:
                    target = match_rows[0]
                if target:
                    chat_session.student_portrait["current_match"] = {
                        "job_name": target.job_name,
                        "overall_score": target.overall_score,
                        "weight_used": target.weight_used or {},
                        "summary": target.summary or "",
                    }
            except Exception as _e:
                logger.warning("注入匹配上下文失败: %s", _e)

        return {
            "session_id": db_session.session_id,
            "state": db_session.state,
            "messages": [],
            "emotion_score": db_session.emotion_score,
            "turn_count": db_session.turn_count,
        }


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(request: ChatMessageRequest):
    session = chat_agent_service.get_session(request.session_id)
    if not session:
        async with get_db_session() as db:
            db_sess = await chat_session_crud.get_by_session_id(db, request.session_id)
        if not db_sess:
            raise HTTPException(status_code=404, detail="会话不存在")
        session = chat_agent_service.restore_session(
            request.session_id, db_sess.state or "GREETING",
            db_sess.messages or [], db_sess.turn_count or 0,
        )
        logger.info(f"从DB恢复会话 {request.session_id}，状态={session.state}")

    async with get_db_session() as db_session:
        await chat_session_crud.add_message(
            db_session, request.session_id,
            {"role": "user", "content": request.message, "timestamp": datetime.utcnow().isoformat()}
        )

    response = await chat_agent_service.generate_response(session, request.message)

    async with get_db_session() as db_session:
        await chat_session_crud.add_message(
            db_session, request.session_id,
            {"role": "assistant", "content": response, "timestamp": datetime.utcnow().isoformat()}
        )
        await chat_session_crud.update(db_session, request.session_id, {"state": session.state.value})

    return ChatMessageResponse(
        id=f"msg_{uuid.uuid4().hex[:8]}",
        role="assistant",
        content=response,
        state=session.state.value,
        emotion=session.current_emotion.value if session.current_emotion else None,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.post("/stream")
async def stream_chat_message(request: ChatMessageRequest):
    session = chat_agent_service.get_session(request.session_id)
    if not session:
        async with get_db_session() as db:
            db_sess = await chat_session_crud.get_by_session_id(db, request.session_id)
        if not db_sess:
            raise HTTPException(status_code=404, detail="会话不存在")
        session = chat_agent_service.restore_session(
            request.session_id, db_sess.state or "GREETING",
            db_sess.messages or [], db_sess.turn_count or 0,
        )

    async def event_generator():
        try:
            async with get_db_session() as db_sess:
                await chat_session_crud.add_message(
                    db_sess, request.session_id,
                    {"role": "user", "content": request.message, "timestamp": datetime.utcnow().isoformat()}
                )

            full_parts: list[str] = []
            async for chunk in chat_agent_service.generate_response_stream(session, request.message):
                full_parts.append(chunk)
                yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"

            response = "".join(full_parts)

            async with get_db_session() as db_sess:
                await chat_session_crud.add_message(
                    db_sess, request.session_id,
                    {"role": "assistant", "content": response, "timestamp": datetime.utcnow().isoformat()}
                )
                await chat_session_crud.update(
                    db_sess, request.session_id,
                    {"state": session.state.value, "turn_count": session.turn_count}
                )

            yield f"data: {json.dumps({'full_response': response, 'state': session.state.value}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"chat/stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    session = chat_agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return [
        {
            "id": f"msg_{i}",
            "role": msg.role,
            "content": msg.content,
            "state": msg.state.value if msg.state else None,
            "emotion": msg.emotion.value if msg.emotion else None,
            "timestamp": msg.timestamp or datetime.utcnow().isoformat(),
        }
        for i, msg in enumerate(session.messages)
    ]


@router.get("/sessions")
async def list_chat_sessions(
    student_id: Optional[str] = None,
    limit: int = 10,
    current_user: Optional[dict] = Depends(get_current_user),
):
    async with get_db_session() as session:
        query = sa_select(ChatSessionModel)
        if student_id:
            query = query.where(ChatSessionModel.student_id == student_id)
        query = query.order_by(ChatSessionModel.updated_at.desc()).limit(limit)
        result = await session.execute(query)
        sessions = result.scalars().all()
    return [
        {
            "id": str(s.session_id),
            "title": f"对话 {s.created_at.strftime('%Y-%m-%d') if s.created_at else ''}",
            "updatedAt": s.updated_at.isoformat() if s.updated_at else "",
            "messageCount": len(s.messages) if s.messages else 0,
        }
        for s in sessions
    ]


@router.get("/session/{session_id}")
async def get_chat_session(session_id: str):
    session = chat_agent_service.get_session(session_id)
    if not session:
        async with get_db_session() as db:
            db_sess = await chat_session_crud.get_by_session_id(db, session_id)
        if not db_sess:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {
            "session_id": db_sess.session_id,
            "state": db_sess.state or "GREETING",
            "messages": db_sess.messages or [],
            "emotion_score": db_sess.emotion_score or 0,
            "turn_count": db_sess.turn_count or 0,
            "title": f"对话 {db_sess.created_at.strftime('%Y-%m-%d') if db_sess.created_at else ''}",
            "created_at": db_sess.created_at.isoformat() if db_sess.created_at else None,
            "updated_at": db_sess.updated_at.isoformat() if db_sess.updated_at else None,
        }
    return {
        "session_id": session_id,
        "state": session.state.value,
        "messages": [
            {
                "id": f"msg_{i}",
                "role": msg.role,
                "content": msg.content,
                "state": msg.state.value if msg.state else None,
                "emotion": msg.emotion.value if msg.emotion else None,
                "timestamp": msg.timestamp or datetime.utcnow().isoformat(),
            }
            for i, msg in enumerate(session.messages)
        ],
        "emotion_score": session.emotion_score,
        "turn_count": session.turn_count,
    }


@router.delete("/session/{session_id}")
async def delete_chat_session(session_id: str):
    chat_agent_service.delete_session(session_id)
    async with get_db_session() as session:
        await chat_session_crud.delete(session, session_id)
    return {"ok": True}


@router.patch("/session/{session_id}")
async def update_chat_session(session_id: str, data: dict):
    title = data.get("title", "")
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    async with get_db_session() as session:
        await chat_session_crud.update(session, session_id, {"title": title})
    return {"ok": True}
