# -*- coding: utf-8 -*-
"""
Agent 运行记录器 —— 把一次 Agent run 的每一步落库（AgentRun / AgentStep）。

用于可观测与回放：trace_id 贯穿全程，步骤可在 agent_steps 表按序还原。
所有写入用 try/except 包裹，记录失败绝不影响 Agent 主流程。
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from app.core.database import SessionLocal
from app.models.db_models import AgentRun, AgentStep
from app.services.state_store import _ensure_tables

logger = logging.getLogger(__name__)


class RunRecorder:
    def __init__(self, run_id: str, student_id: str, goal: str,
                 trace_id: str, session_id: Optional[str] = None):
        self.run_id = run_id
        self.student_id = student_id
        self.goal = goal
        self.trace_id = trace_id
        self.session_id = session_id
        self._step_no = 0
        _ensure_tables()
        self._create()

    def _create(self) -> None:
        try:
            with SessionLocal() as db:
                db.add(AgentRun(
                    id=self.run_id, student_id=self.student_id,
                    session_id=self.session_id, goal=self.goal,
                    status="running", trace_id=self.trace_id,
                    created_at=datetime.utcnow(),
                ))
                db.commit()
        except Exception as e:
            logger.warning("[run %s] 创建记录失败: %s", self.run_id, e)

    def step(self, type_: str, state: Optional[str] = None,
             tool_name: Optional[str] = None, args: Any = None,
             result: Any = None, latency_ms: Optional[int] = None,
             token_usage: Optional[int] = None) -> None:
        self._step_no += 1
        try:
            with SessionLocal() as db:
                db.add(AgentStep(
                    run_id=self.run_id, step_no=self._step_no,
                    type=type_, state=state, tool_name=tool_name,
                    args_json=json.dumps(args, ensure_ascii=False, default=str) if args is not None else None,
                    result_json=json.dumps(result, ensure_ascii=False, default=str)[:8000] if result is not None else None,
                    latency_ms=latency_ms, token_usage=token_usage,
                    created_at=datetime.utcnow(),
                ))
                db.commit()
        except Exception as e:
            logger.warning("[run %s] 记录步骤失败: %s", self.run_id, e)

    def finish(self, status: str, final_state: Optional[str] = None,
               ttft_ms: Optional[int] = None, latency_ms: Optional[int] = None) -> None:
        try:
            with SessionLocal() as db:
                run = db.get(AgentRun, self.run_id)
                if run:
                    run.status = status
                    run.final_state = final_state
                    run.step_count = self._step_no
                    run.ttft_ms = ttft_ms
                    run.latency_ms = latency_ms
                    db.commit()
        except Exception as e:
            logger.warning("[run %s] 收尾失败: %s", self.run_id, e)
