# -*- coding: utf-8 -*-
"""岗位图谱路由：/api/graph/*"""
import logging

from fastapi import APIRouter, HTTPException, Query

from app.graph.job_graph_repo import job_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("")
async def get_career_graph(job: str = Query(..., description="岗位名称")):
    return job_graph.get_all_paths(job)


@router.get("/main-transfers/{job_name}")
async def get_main_transfers(job_name: str):
    result = job_graph.get_main_with_transfers(job_name)
    if not result["main"]:
        raise HTTPException(status_code=404, detail=f"岗位 '{job_name}' 不存在图谱中")
    return result
