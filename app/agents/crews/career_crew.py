# -*- coding: utf-8 -*-
"""
CrewAI Crew 编排模块
定义完整的职业规划工作流
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from app.agents.crewai_config import CREW_CONFIGS
from app.agents.crewai_agents import (
    create_resume_analyzer_agent,
    create_job_matcher_agent,
    create_career_advisor_agent,
    create_report_generator_agent,
    create_analyze_resume_task,
    create_match_jobs_task,
    create_generate_advice_task,
    create_generate_report_task,
    crewai_agent_manager,
)

logger = logging.getLogger(__name__)


@dataclass
class CrewResult:
    """Crew 执行结果"""
    success: bool
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    raw_output: Optional[str] = None


class CareerPlanningCrew:
    """职业规划 Crew - 编排多个 Agent 协同工作"""
    
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self._agents = {}
        self._last_result: Optional[CrewResult] = None
    
    def _initialize_agents(self):
        """延迟初始化 Agent"""
        if not self._agents:
            self._agents = {
                "resume_analyzer": create_resume_analyzer_agent(),
                "job_matcher": create_job_matcher_agent(),
                "career_advisor": create_career_advisor_agent(),
                "report_generator": create_report_generator_agent(),
            }
        return self._agents
    
    async def run_workflow(
        self,
        resume_content: str,
        parsed_data: Optional[Dict] = None,
        target_jobs: Optional[List[str]] = None,
        student_id: Optional[str] = None,
    ) -> CrewResult:
        """
        运行完整的职业规划工作流（4-Agent 协作）

        执行链：简历分析 → 岗位匹配 → 职业建议 → 报告生成
        每个任务通过 context= 参数依赖前一个任务的输出，LLM 驱动推理。
        """
        started_at = datetime.now()

        try:
            agents = self._initialize_agents()

            if not all(agents.values()):
                return CrewResult(
                    success=False,
                    status="error",
                    started_at=started_at,
                    completed_at=datetime.now(),
                    error="部分 Agent 初始化失败，请检查 CrewAI 是否正确安装",
                )

            from crewai import Crew, Process

            # Task1：简历分析（resume_content 为空时从 parsed_data 重建描述）
            effective_resume = resume_content or ""
            if not effective_resume and parsed_data:
                skills = parsed_data.get("skills", [])
                basic = parsed_data.get("basic_info", {})
                effective_resume = (
                    f"学生信息：{basic}\n"
                    f"已有技能：{', '.join(skills[:15]) if skills else '未知'}\n"
                    f"差距技能：{', '.join(parsed_data.get('gap_skills', []))}\n"
                    f"student_id: {student_id or parsed_data.get('student_id', '')}"
                )

            task1 = create_analyze_resume_task(
                agents["resume_analyzer"],
                effective_resume,
                parsed_data,
            )

            tasks = []
            if task1:
                tasks.append(task1)

            # Task2：岗位匹配（依赖 task1）
            task2 = None
            if target_jobs and task1:
                task2 = create_match_jobs_task(
                    agents["job_matcher"],
                    {"parsed": parsed_data or {}, "target_jobs": target_jobs},
                    target_jobs,
                )
                if task2:
                    # context 让 job_matcher 可以读取 resume_analyzer 的输出
                    task2.context = [task1]
                    tasks.append(task2)

            # Task3：职业发展建议（依赖 task1 + task2）
            advice_context = [t for t in [task1, task2] if t]
            task3 = create_generate_advice_task(
                agents["career_advisor"],
                {"parsed": parsed_data or {}},
                {"target_jobs": target_jobs or []},
            )
            if task3:
                task3.context = advice_context
                tasks.append(task3)

            # Task4：报告生成（依赖所有前序任务）
            task4 = create_generate_report_task(
                agents["report_generator"],
                {"parsed": parsed_data or {}},
                {"target_jobs": target_jobs or []},
                {},
            )
            if task4:
                task4.context = [t for t in [task1, task2, task3] if t]
                tasks.append(task4)

            config = CREW_CONFIGS["career_planning"]

            crew = Crew(
                agents=list(agents.values()),
                tasks=tasks,
                process=Process.sequential,
                memory=config.get("memory", True),
                verbose=config.get("verbose", True),
            )

            logger.info("Starting CareerPlanningCrew workflow with %d tasks", len(tasks))

            inputs = {
                "resume_content": effective_resume,
                "parsed_data": json.dumps(parsed_data or {}, ensure_ascii=False),
                "target_jobs": ", ".join(target_jobs or []),
                "student_id": student_id or "",
            }

            result = await crew.kickoff_async(inputs=inputs)

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            parsed_result = self._parse_crew_output(result)

            self._last_result = CrewResult(
                success=True,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                results=parsed_result,
                raw_output=str(result.raw) if hasattr(result, 'raw') else str(result),
            )

            logger.info("CareerPlanningCrew completed in %.2fs", duration)
            return self._last_result

        except ImportError as e:
            logger.error("CrewAI import error: %s", e)
            return CrewResult(
                success=False,
                status="error",
                started_at=started_at,
                completed_at=datetime.now(),
                error=f"CrewAI 未正确安装: {str(e)}",
            )
        except Exception as e:
            logger.error("CareerPlanningCrew failed: %s", e, exc_info=True)
            return CrewResult(
                success=False,
                status="error",
                started_at=started_at,
                completed_at=datetime.now(),
                error=str(e),
            )
    
    async def run_analysis_only(
        self,
        resume_content: str,
        parsed_data: Optional[Dict] = None,
    ) -> CrewResult:
        """
        仅运行简历分析（快速模式）
        
        Args:
            resume_content: 简历文本内容
            parsed_data: 已解析的简历数据（可选）
            
        Returns:
            CrewResult 包含分析结果
        """
        started_at = datetime.now()
        
        try:
            agents = self._initialize_agents()
            
            if not agents.get("resume_analyzer"):
                return CrewResult(
                    success=False,
                    status="error",
                    started_at=started_at,
                    completed_at=datetime.now(),
                    error="简历分析 Agent 初始化失败",
                )
            
            from crewai import Crew, Process
            
            task = create_analyze_resume_task(
                agents["resume_analyzer"],
                resume_content,
                parsed_data
            )
            
            if not task:
                return CrewResult(
                    success=False,
                    status="error",
                    started_at=started_at,
                    completed_at=datetime.now(),
                    error="任务创建失败",
                )
            
            config = CREW_CONFIGS["quick_analysis"]
            
            crew = Crew(
                agents=[agents["resume_analyzer"]],
                tasks=[task],
                process=Process.sequential,
                memory=config.get("memory", False),
                verbose=config.get("verbose", False),
            )
            
            logger.info("Starting quick analysis workflow")
            
            result = await crew.kickoff_async(inputs={
                "resume_content": resume_content,
            })
            
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            
            parsed_result = self._parse_crew_output(result)
            
            return CrewResult(
                success=True,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                results=parsed_result,
                raw_output=str(result.raw) if hasattr(result, 'raw') else str(result),
            )
            
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}", exc_info=True)
            return CrewResult(
                success=False,
                status="error",
                started_at=started_at,
                completed_at=datetime.now(),
                error=str(e),
            )
    
    async def run_matching(
        self,
        resume_analysis: Dict,
        target_jobs: List[str],
    ) -> CrewResult:
        """
        运行岗位匹配
        
        Args:
            resume_analysis: 简历分析结果
            target_jobs: 目标岗位列表
            
        Returns:
            CrewResult 包含匹配结果
        """
        started_at = datetime.now()
        
        try:
            agents = self._initialize_agents()
            
            if not agents.get("job_matcher"):
                return CrewResult(
                    success=False,
                    status="error",
                    started_at=started_at,
                    completed_at=datetime.now(),
                    error="岗位匹配 Agent 初始化失败",
                )
            
            from crewai import Crew, Process
            
            task = create_match_jobs_task(
                agents["job_matcher"],
                resume_analysis,
                target_jobs
            )
            
            if not task:
                return CrewResult(
                    success=False,
                    status="error",
                    started_at=started_at,
                    completed_at=datetime.now(),
                    error="任务创建失败",
                )
            
            crew = Crew(
                agents=[agents["job_matcher"]],
                tasks=[task],
                process=Process.sequential,
                memory=False,
                verbose=True,
            )
            
            logger.info(f"Starting job matching for {len(target_jobs)} jobs")
            
            result = await crew.kickoff_async(inputs={
                "resume_analysis": resume_analysis,
                "target_jobs": target_jobs,
            })
            
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            
            parsed_result = self._parse_crew_output(result)
            
            return CrewResult(
                success=True,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                results=parsed_result,
                raw_output=str(result.raw) if hasattr(result, 'raw') else str(result),
            )
            
        except Exception as e:
            logger.error(f"Job matching failed: {e}", exc_info=True)
            return CrewResult(
                success=False,
                status="error",
                started_at=started_at,
                completed_at=datetime.now(),
                error=str(e),
            )
    
    def _parse_crew_output(self, result) -> Dict[str, Any]:
        """解析 Crew 输出结果"""
        try:
            if hasattr(result, 'raw'):
                raw_output = result.raw
                if isinstance(raw_output, str):
                    try:
                        return json.loads(raw_output)
                    except json.JSONDecodeError:
                        return {"raw": raw_output}
                elif isinstance(raw_output, dict):
                    return raw_output
            
            if hasattr(result, 'json_dict'):
                return result.json_dict
            
            if hasattr(result, 'tasks_output'):
                outputs = {}
                for i, task_output in enumerate(result.tasks_output):
                    if hasattr(task_output, 'raw'):
                        try:
                            outputs[f"task_{i}"] = json.loads(task_output.raw)
                        except:
                            outputs[f"task_{i}"] = task_output.raw
                return outputs
            
            return {"result": str(result)}
            
        except Exception as e:
            logger.warning(f"Failed to parse crew output: {e}")
            return {"raw": str(result)}
    
    @property
    def last_result(self) -> Optional[CrewResult]:
        """获取最后一次执行结果"""
        return self._last_result


career_planning_crew = CareerPlanningCrew()
