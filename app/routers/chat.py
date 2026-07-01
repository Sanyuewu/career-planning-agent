# -*- coding: utf-8 -*-
"""对话顾问路由：session CRUD / message(JSON) / stream(SSE 真流式)。"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse

from app.services.youtu_retriever_service import youtu_retriever_service
from app.services import progress_service
from app.core.llm_service import llm_service
from app.routers._common import _chat_store, ChatMessageRequest
from app.routers.auth import get_current_user, assert_student_access

router = APIRouter(tags=["对话顾问"])


async def _growth_context(student_id: Optional[str]) -> str:
    """该学生历史成长上下文（成长闭环）：让 Chat 也"记得"上次分/涨因/行动进度，
    不再是只看图谱的健忘问答机器人。best-effort，无数据/异常返回 ""。"""
    if not student_id:
        return ""
    try:
        summary = await asyncio.to_thread(progress_service.agent_context_summary, student_id)
        text = progress_service.format_summary_text(summary)
        return f"\n\n【该学生历史成长】（真实快照，可引用具体数字）{text}" if text else ""
    except Exception:
        return ""


async def _load_owned_session(session_id: str, user: dict) -> dict:
    """加载会话并校验归属（跨租户已被存储层拦为 404）。"""
    session = await _chat_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    sid = session.get("student_id")
    if sid:
        assert_student_access(user, sid)
    return session


@router.post("/api/chat/session")
async def create_session(
    student_id: Optional[str] = Query(None),
    match_job_name: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """创建对话会话（学生账号绑定到本人）"""
    if user.get("role") == "student" and user.get("student_id"):
        student_id = user["student_id"]
    elif student_id:
        assert_student_access(user, student_id)
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "student_id": student_id,
        "job_name": match_job_name,
        "state": "active",
        "messages": [],
        "emotion_score": 0.7,
        "turn_count": 0,
        "title": f"职业咨询 {datetime.now().strftime('%m-%d %H:%M')}",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    await _chat_store.save(session_id, session)
    return session


@router.get("/api/chat/session/{session_id}")
async def get_session(session_id: str, user: dict = Depends(get_current_user)):
    """获取会话"""
    return await _load_owned_session(session_id, user)


@router.get("/api/chat/sessions")
async def list_sessions(student_id: Optional[str] = Query(None),
                        user: dict = Depends(get_current_user)):
    """会话列表（学生账号仅返回本人；teacher/admin 受租户与数据范围约束）"""
    if user.get("role") == "student":
        student_id = user.get("student_id")
    sessions = list(await _chat_store.values())   # 已按租户过滤
    if student_id:
        sessions = [s for s in sessions if s.get("student_id") == student_id]
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return [
        {
            "id": s["session_id"],
            "title": s.get("title", ""),
            "updatedAt": s.get("updated_at", ""),
            "messageCount": len(s.get("messages", [])),
        }
        for s in sessions
    ]


@router.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    """删除会话"""
    await _load_owned_session(session_id, user)   # 归属校验（不存在→404，越权→403）
    await _chat_store.delete(session_id)
    return {"success": True}


@router.post("/api/chat/message")
async def send_message(req: ChatMessageRequest, user: dict = Depends(get_current_user)):
    """
    发送消息
    1. YOUTU-GraphRAG 检索相关图谱上下文
    2. LLM 生成回复
    3. 追加到会话历史
    """
    session = await _load_owned_session(req.session_id, user)

    text = req.text
    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": text,
        "timestamp": datetime.now().isoformat(),
    }
    session["messages"].append(user_msg)

    # YOUTU 检索图谱上下文
    job_ctx = session.get("job_name") or ""
    try:
        youtu_result = await youtu_retriever_service.query(
            f"{text}{'（岗位：' + job_ctx + '）' if job_ctx else ''}",
            top_k=8,
        )
        graph_answer = youtu_result.get("answer", "")
    except Exception:
        graph_answer = ""

    # 成长闭环：注入该学生历史成长上下文
    growth_ctx = await _growth_context(session.get("student_id"))

    # 构建对话历史（最近5轮）
    history = session["messages"][-10:]
    messages = [
        {"role": "system", "content": (
            "你是一位专业的大学生职业规划顾问，基于知识图谱数据为学生提供个性化职业建议。"
            f"{'图谱参考：' + graph_answer[:600] if graph_answer else ''}"
            f"{growth_ctx}"
        )}
    ]
    for m in history[:-1]:  # 排除刚加入的用户消息
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": text})

    try:
        reply_content = await llm_service.chat(messages, temperature=0.6)
    except Exception as e:
        reply_content = f"抱歉，暂时无法回答您的问题。({e})"

    assistant_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": reply_content,
        "state": "active",
        "emotion": "neutral",
        "timestamp": datetime.now().isoformat(),
    }
    session["messages"].append(assistant_msg)
    session["turn_count"] += 1
    session["updated_at"] = datetime.now().isoformat()
    await _chat_store.save(req.session_id, session)

    return assistant_msg


@router.post("/api/chat/stream")
async def chat_stream(req: ChatMessageRequest, user: dict = Depends(get_current_user)):
    """
    聊天 SSE 流接口
    1. YOUTU-GraphRAG 检索获取图谱上下文
    2. LLM 真流式 token 级生成
    3. 以 SSE 格式逐 token 推送，最后发送 full_response 事件
    """
    session = await _load_owned_session(req.session_id, user)

    text = req.text
    job_ctx = session.get("job_name") or ""

    # 保存用户消息
    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": text,
        "timestamp": datetime.now().isoformat(),
    }
    session["messages"].append(user_msg)

    async def _event_generator():
        try:
            # YOUTU 图谱检索（L2 实体层 + L1 属性层）
            graph_context = ""
            try:
                youtu_result = await youtu_retriever_service.query(
                    f"{text}{'（岗位：' + job_ctx + '）' if job_ctx else ''}",
                    top_k=8,
                )
                graph_context = youtu_result.get("answer", "") or youtu_result.get("context", "")
            except Exception:
                pass

            # 成长闭环：注入该学生历史成长上下文
            growth_ctx = await _growth_context(session.get("student_id"))

            # 构建消息历史（最近8条）
            history = session["messages"][-8:]
            messages = [
                {"role": "system", "content": (
                    "你是一位专业的大学生职业规划顾问，基于知识图谱数据为学生提供个性化职业建议。"
                    "回答要具体、有针对性，结合实际就业市场。"
                    + (f"\n\n【图谱参考信息】\n{graph_context[:800]}" if graph_context else "")
                    + growth_ctx
                )}
            ]
            for m in history[:-1]:
                messages.append({"role": m["role"], "content": m["content"]})
            messages.append({"role": "user", "content": text})

            # 真流式：LLM token 级增量直接推送，首字延迟≈首个 chunk 到达时间
            reply_parts = []
            async for delta in llm_service.chat_stream(messages, temperature=0.6):
                reply_parts.append(delta)
                payload = json.dumps({"token": delta}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            reply = "".join(reply_parts)

            # 流式结束后保存 assistant 消息
            assistant_msg = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": reply,
                "state": "active",
                "emotion": "neutral",
                "timestamp": datetime.now().isoformat(),
            }
            session["messages"].append(assistant_msg)
            session["turn_count"] = session.get("turn_count", 0) + 1
            session["updated_at"] = datetime.now().isoformat()
            await _chat_store.save(req.session_id, session)

            # 发送终止事件
            final = json.dumps({
                "full_response": reply,
                "state": "active",
                "emotion": "neutral",
            }, ensure_ascii=False)
            yield f"data: {final}\n\n"

        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
