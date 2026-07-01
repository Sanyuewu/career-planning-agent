# -*- coding: utf-8 -*-
"""
YOUTU-GraphRAG 独立检索微服务。

复用进程内的 youtu_retriever_service（图谱常驻内存 + FAISS + KTRetriever），
对外暴露 HTTP 检索契约，供主后端通过 retrieval_client 调用，实现独立扩容。

契约：
  POST /retrieve  {query, top_k}     → 完整检索结果（answer/context/triples/...）
  GET  /health                       → {"ready": bool, ...stats}

启动（在项目根目录）：
  uvicorn retrieval_service.server:app --port 8090
注意：本服务进程的 RETRIEVAL_SERVICE_URL 必须为空，使 query() 在本地执行，
不会自我转发造成回环。
"""

import os
import sys
import time
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.observability import setup_logging
from app.services.youtu_retriever_service import youtu_retriever_service


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # 单例在 import 时已加载图谱与 FAISS；这里仅确认就绪
    app.state.ready = youtu_retriever_service.graph_data is not None
    yield


app = FastAPI(title="YOUTU-GraphRAG Retrieval Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    stats = youtu_retriever_service.get_stats()
    ready = stats.get("graph_loaded", False)
    return {"ready": ready, **stats}


@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    t0 = time.perf_counter()
    result = await youtu_retriever_service.query(req.query, top_k=req.top_k)
    result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return result
