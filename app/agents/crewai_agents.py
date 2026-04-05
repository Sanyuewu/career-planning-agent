# -*- coding: utf-8 -*-
"""
CrewAI Agent 定义
使用官方 CrewAI 框架定义 Agent
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.agents.crewai_config import (
    get_crewai_llm,
    AGENT_CONFIGS,
    TASK_CONFIGS,
)
from app.agents.tools import get_tools_by_agent

logger = logging.getLogger(__name__)


def create_resume_analyzer_agent() -> "Agent":
    """
    创建简历分析 Agent
    
    Returns:
        CrewAI Agent 实例
    """
    try:
        from crewai import Agent
        
        config = AGENT_CONFIGS["resume_analyzer"]
        llm = get_crewai_llm()
        
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=llm,
            tools=get_tools_by_agent("resume_analyzer"),
            memory=True,
            verbose=True,
            max_iter=5,
            max_rpm=10,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


def create_job_matcher_agent() -> "Agent":
    """
    创建岗位匹配 Agent
    
    Returns:
        CrewAI Agent 实例
    """
    try:
        from crewai import Agent
        
        config = AGENT_CONFIGS["job_matcher"]
        llm = get_crewai_llm()
        
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=llm,
            tools=get_tools_by_agent("job_matcher"),
            memory=True,
            verbose=True,
            max_iter=5,
            max_rpm=10,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


def create_career_advisor_agent() -> "Agent":
    """
    创建职业发展顾问 Agent
    
    Returns:
        CrewAI Agent 实例
    """
    try:
        from crewai import Agent
        
        config = AGENT_CONFIGS["career_advisor"]
        llm = get_crewai_llm()
        
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=llm,
            tools=get_tools_by_agent("career_advisor"),
            memory=True,
            verbose=True,
            max_iter=5,
            max_rpm=10,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


def create_report_generator_agent() -> "Agent":
    """
    创建报告生成 Agent
    
    Returns:
        CrewAI Agent 实例
    """
    try:
        from crewai import Agent
        
        config = AGENT_CONFIGS["report_generator"]
        llm = get_crewai_llm()
        
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=llm,
            tools=get_tools_by_agent("report_generator"),
            memory=True,
            verbose=True,
            max_iter=5,
            max_rpm=10,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


def create_analyze_resume_task(agent: "Agent", resume_content: str, parsed_data: Dict = None) -> "Task":
    """
    创建简历分析任务
    
    Args:
        agent: 执行任务的 Agent
        resume_content: 简历文本内容
        parsed_data: 已解析的数据（可选）
        
    Returns:
        CrewAI Task 实例
    """
    try:
        from crewai import Task
        
        config = TASK_CONFIGS["analyze_resume"]
        
        description = config["description"].format(
            resume_content=resume_content
        )
        
        return Task(
            description=description,
            expected_output=config["expected_output"],
            agent=agent,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


def create_match_jobs_task(
    agent: "Agent",
    resume_analysis: Dict,
    target_jobs: List[str]
) -> "Task":
    """
    创建岗位匹配任务
    
    Args:
        agent: 执行任务的 Agent
        resume_analysis: 简历分析结果
        target_jobs: 目标岗位列表
        
    Returns:
        CrewAI Task 实例
    """
    try:
        from crewai import Task
        
        config = TASK_CONFIGS["match_jobs"]
        
        description = config["description"].format(
            resume_analysis=str(resume_analysis),
            target_jobs=str(target_jobs)
        )
        
        return Task(
            description=description,
            expected_output=config["expected_output"],
            agent=agent,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


def create_generate_advice_task(
    agent: "Agent",
    resume_analysis: Dict,
    match_results: Dict
) -> "Task":
    """
    创建职业建议生成任务
    
    Args:
        agent: 执行任务的 Agent
        resume_analysis: 简历分析结果
        match_results: 岗位匹配结果
        
    Returns:
        CrewAI Task 实例
    """
    try:
        from crewai import Task
        
        config = TASK_CONFIGS["generate_advice"]
        
        description = config["description"].format(
            resume_analysis=str(resume_analysis),
            match_results=str(match_results)
        )
        
        return Task(
            description=description,
            expected_output=config["expected_output"],
            agent=agent,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


def create_generate_report_task(
    agent: "Agent",
    resume_analysis: Dict,
    match_results: Dict,
    career_advice: Dict
) -> "Task":
    """
    创建报告生成任务
    
    Args:
        agent: 执行任务的 Agent
        resume_analysis: 简历分析结果
        match_results: 岗位匹配结果
        career_advice: 职业建议
        
    Returns:
        CrewAI Task 实例
    """
    try:
        from crewai import Task
        
        config = TASK_CONFIGS["generate_report"]
        
        description = config["description"].format(
            resume_analysis=str(resume_analysis),
            match_results=str(match_results),
            career_advice=str(career_advice)
        )
        
        return Task(
            description=description,
            expected_output=config["expected_output"],
            agent=agent,
        )
    except ImportError:
        logger.warning("CrewAI not installed, returning None")
        return None


class CrewAIAgentManager:
    """CrewAI Agent 管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self):
        """初始化所有 Agent"""
        if self._initialized:
            return
        
        self._agents = {
            "resume_analyzer": create_resume_analyzer_agent(),
            "job_matcher": create_job_matcher_agent(),
            "career_advisor": create_career_advisor_agent(),
            "report_generator": create_report_generator_agent(),
        }
        self._initialized = True
        logger.info("CrewAI Agents initialized")
    
    def get_agent(self, agent_type: str) -> Optional["Agent"]:
        """获取指定类型的 Agent"""
        if not self._initialized:
            self.initialize()
        return self._agents.get(agent_type)
    
    def get_all_agents(self) -> Dict[str, "Agent"]:
        """获取所有 Agent"""
        if not self._initialized:
            self.initialize()
        return self._agents.copy()


crewai_agent_manager = CrewAIAgentManager()
