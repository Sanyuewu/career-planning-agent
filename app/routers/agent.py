"""
Agent API路由
提供Agent任务的HTTP端点
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

from app.agents.crew_manager import CrewManager, AgentRole
from app.agents.task_manager import task_manager, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["Agent"])


class AnalyzeRequest(BaseModel):
    resume_content: str
    parsed_data: Dict[str, Any] = {}
    target_jobs: List[Dict[str, Any]] = []
    use_llm: bool = True


class WorkflowRequest(BaseModel):
    resume_content: str
    parsed_data: Dict[str, Any]
    target_jobs: List[Dict[str, Any]]
    use_llm: bool = True


class SingleAgentRequest(BaseModel):
    role: str
    context: Dict[str, Any]
    use_llm: bool = True


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    suggestions: Optional[List[str]] = None


@router.post("/analyze", response_model=TaskResponse)
async def start_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """启动简历分析任务（重定向至 CrewAI LLM 驱动流程）"""
    task_id = await task_manager.create_task(metadata={"type": "crewai_analysis"})

    background_tasks.add_task(
        run_crew_workflow_task,
        task_id,
        request.resume_content,
        request.parsed_data,
        [],   # target_jobs
        None, # student_id
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Analysis task started (CrewAI)"
    )


@router.post("/workflow", response_model=TaskResponse)
async def run_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """运行完整工作流（重定向至 CrewAI 4-Agent LLM 驱动流程）"""
    task_id = await task_manager.create_task(metadata={"type": "crewai_workflow"})

    background_tasks.add_task(
        run_crew_workflow_task,
        task_id,
        request.resume_content,
        request.parsed_data,
        [j.get("job_name", "") for j in request.target_jobs if isinstance(j, dict)],
        None, # student_id
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Workflow task started (CrewAI 4-Agent)"
    )


@router.post("/single", response_model=TaskResponse)
async def run_single_agent(request: SingleAgentRequest, background_tasks: BackgroundTasks):
    """运行单个Agent"""
    try:
        role = AgentRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent role: {request.role}")
    
    task_id = await task_manager.create_task(metadata={
        "type": "single_agent",
        "role": request.role,
        "use_llm": request.use_llm
    })
    
    background_tasks.add_task(
        run_single_agent_task,
        task_id,
        role,
        request.context,
        request.use_llm
    )
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message=f"Single agent task started for {request.role}"
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status.value,
        progress=task.progress,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        error=task.error
    )


@router.get("/result/{task_id}", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """获取任务结果"""
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status == TaskStatus.PENDING:
        return TaskResultResponse(
            task_id=task.id,
            status="pending",
            result=None
        )
    
    if task.status == TaskStatus.RUNNING:
        return TaskResultResponse(
            task_id=task.id,
            status="running",
            result=None
        )
    
    if task.status == TaskStatus.FAILED:
        return TaskResultResponse(
            task_id=task.id,
            status="failed",
            result={"error": task.error}
        )
    
    result = task_manager.get_result(task_id)
    
    return TaskResultResponse(
        task_id=task.id,
        status="completed",
        result=result,
        confidence=result.get("confidence", {}).get("overall") if result else None,
        suggestions=result.get("suggestions") if result else None
    )


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 20):
    """列出任务"""
    task_status = TaskStatus(status) if status else None
    tasks = task_manager.list_tasks(status=task_status, limit=limit)
    
    return [
        {
            "task_id": t.id,
            "status": t.status.value,
            "created_at": t.created_at.isoformat(),
            "progress": t.progress
        }
        for t in tasks
    ]


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Task already finished")
    
    await task_manager.cancel_task(task_id)
    
    return {"task_id": task_id, "status": "cancelled"}


async def run_analysis_task(
    task_id: str,
    resume_content: str,
    parsed_data: Dict,
    target_jobs: List,
    use_llm: bool
):
    """后台任务：运行简历分析"""
    try:
        await task_manager.start_task(task_id)
        
        manager = CrewManager(use_llm=use_llm)
        
        await task_manager.update_progress(task_id, 0.2)
        
        result = await manager.run_single_agent(
            AgentRole.RESUME_ANALYZER,
            {"resume_content": resume_content, "parsed_data": parsed_data}
        )
        
        await task_manager.update_progress(task_id, 1.0)
        await task_manager.complete_task(task_id, result.data)
        
    except Exception as e:
        logger.error(f"Analysis task failed: {e}")
        await task_manager.fail_task(task_id, str(e))


async def run_workflow_task(
    task_id: str,
    resume_content: str,
    parsed_data: Dict,
    target_jobs: List,
    use_llm: bool
):
    """后台任务：运行完整工作流"""
    try:
        await task_manager.start_task(task_id)
        
        manager = CrewManager(use_llm=use_llm)
        
        await task_manager.update_progress(task_id, 0.1)
        
        result = await manager.run_workflow(resume_content, parsed_data, target_jobs)
        
        await task_manager.update_progress(task_id, 1.0)
        await task_manager.complete_task(task_id, result)
        
    except Exception as e:
        logger.error(f"Workflow task failed: {e}")
        await task_manager.fail_task(task_id, str(e))


async def run_single_agent_task(
    task_id: str,
    role: AgentRole,
    context: Dict,
    use_llm: bool
):
    """后台任务：运行单个Agent"""
    try:
        await task_manager.start_task(task_id)
        
        manager = CrewManager(use_llm=use_llm)
        
        result = await manager.run_single_agent(role, context)
        
        await task_manager.update_progress(task_id, 1.0)
        await task_manager.complete_task(task_id, result.data)
        
    except Exception as e:
        logger.error(f"Single agent task failed: {e}")
        await task_manager.fail_task(task_id, str(e))


# ============== CrewAI Routes ==============

class CrewAIWorkflowRequest(BaseModel):
    """CrewAI 工作流请求"""
    resume_content: str
    parsed_data: Dict[str, Any] = {}
    target_jobs: List[str] = []
    student_id: Optional[str] = None


class CrewAIAnalysisRequest(BaseModel):
    """CrewAI 分析请求"""
    resume_content: str
    parsed_data: Dict[str, Any] = {}


class CrewAIMatchRequest(BaseModel):
    """CrewAI 匹配请求"""
    resume_analysis: Dict[str, Any]
    target_jobs: List[str]


class CrewAIResultResponse(BaseModel):
    """CrewAI 结果响应"""
    success: bool
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/crew/workflow", response_model=CrewAIResultResponse)
async def run_crew_workflow(request: CrewAIWorkflowRequest):
    """运行 CrewAI 完整工作流（同步执行）"""
    from app.agents.crews import career_planning_crew
    
    result = await career_planning_crew.run_workflow(
        resume_content=request.resume_content,
        parsed_data=request.parsed_data,
        target_jobs=request.target_jobs,
        student_id=request.student_id,
    )
    
    return CrewAIResultResponse(
        success=result.success,
        status=result.status,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        duration_seconds=result.duration_seconds,
        results=result.results,
        error=result.error,
    )


@router.post("/crew/workflow/async", response_model=TaskResponse)
async def run_crew_workflow_async(
    request: CrewAIWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """运行 CrewAI 完整工作流（异步执行）"""
    task_id = await task_manager.create_task(metadata={
        "type": "crewai_workflow",
        "student_id": request.student_id,
    })
    
    background_tasks.add_task(
        run_crew_workflow_task,
        task_id,
        request.resume_content,
        request.parsed_data,
        request.target_jobs,
        request.student_id,
    )
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="CrewAI workflow task started"
    )


@router.post("/crew/analysis", response_model=CrewAIResultResponse)
async def run_crew_analysis(request: CrewAIAnalysisRequest):
    """运行 CrewAI 简历分析（同步执行）"""
    from app.agents.crews import career_planning_crew
    
    result = await career_planning_crew.run_analysis_only(
        resume_content=request.resume_content,
        parsed_data=request.parsed_data,
    )
    
    return CrewAIResultResponse(
        success=result.success,
        status=result.status,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        duration_seconds=result.duration_seconds,
        results=result.results,
        error=result.error,
    )


@router.post("/crew/match", response_model=CrewAIResultResponse)
async def run_crew_match(request: CrewAIMatchRequest):
    """运行 CrewAI 岗位匹配（同步执行）"""
    from app.agents.crews import career_planning_crew
    
    result = await career_planning_crew.run_matching(
        resume_analysis=request.resume_analysis,
        target_jobs=request.target_jobs,
    )
    
    return CrewAIResultResponse(
        success=result.success,
        status=result.status,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        duration_seconds=result.duration_seconds,
        results=result.results,
        error=result.error,
    )


@router.get("/crew/status")
async def get_crew_status():
    """获取 CrewAI 状态"""
    try:
        from crewai import __version__ as crewai_version
        crewai_installed = True
        version = crewai_version
    except ImportError:
        crewai_installed = False
        version = None
    
    from app.agents.crewai_config import get_llm_config
    llm_config = get_llm_config()
    
    return {
        "crewai_installed": crewai_installed,
        "crewai_version": version,
        "llm_provider": llm_config.provider,
        "llm_model": llm_config.model,
        "llm_configured": bool(llm_config.api_key),
    }


async def run_crew_workflow_task(
    task_id: str,
    resume_content: str,
    parsed_data: Dict,
    target_jobs: List,
    student_id: Optional[str],
):
    """后台任务：运行 CrewAI 工作流"""
    try:
        await task_manager.start_task(task_id)
        
        from app.agents.crews import career_planning_crew
        
        await task_manager.update_progress(task_id, 0.1)
        
        result = await career_planning_crew.run_workflow(
            resume_content=resume_content,
            parsed_data=parsed_data,
            target_jobs=target_jobs,
            student_id=student_id,
        )
        
        await task_manager.update_progress(task_id, 1.0)
        
        if result.success:
            await task_manager.complete_task(task_id, result.results)
        else:
            await task_manager.fail_task(task_id, result.error or "Unknown error")
        
    except Exception as e:
        logger.error(f"CrewAI workflow task failed: {e}")
        await task_manager.fail_task(task_id, str(e))
