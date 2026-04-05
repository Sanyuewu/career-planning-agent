# -*- coding: utf-8 -*-
"""
CrewAI 配置模块
将现有 LLM 配置适配为 CrewAI 可用格式
"""

import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """LLM 配置模型"""
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 4000


def get_llm_config() -> LLMConfig:
    """获取 LLM 配置"""
    return LLMConfig(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0.2,
        max_tokens=4000,
    )


def get_crewai_llm():
    """获取 CrewAI 兼容的 LLM 实例"""
    try:
        from crewai import LLM
        config = get_llm_config()
        
        model_name = config.model
        if config.provider == "groq":
            model_name = f"groq/{config.model}"
        elif config.provider == "deepseek":
            model_name = f"deepseek/{config.model}"
        elif config.provider == "qwen":
            model_name = f"qwen/{config.model}"
        
        return LLM(
            model=model_name,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    except ImportError:
        logger.warning("CrewAI LLM not available, using fallback")
        return None
    except Exception as e:
        logger.error(f"Failed to create CrewAI LLM: {e}")
        return None


AGENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "resume_analyzer": {
        "role": "资深简历分析师",
        "goal": "深入分析简历内容，提取关键信息，评估技能水平和职业潜力",
        "backstory": """你是一位有15年经验的HR专家，擅长从简历中挖掘候选人的真实能力和潜力。
你能够识别简历中的亮点和不足，并给出专业的改进建议。
你的分析准确、客观，能够帮助候选人了解自己的优势和需要提升的方向。""",
        "temperature": 0.2,
        "max_tokens": 3000,
    },
    "job_matcher": {
        "role": "岗位匹配专家",
        "goal": "精准匹配候选人与岗位，分析技能差距，提供匹配建议",
        "backstory": """你是一位资深的招聘专家，熟悉各行业岗位需求。
你能够准确评估候选人与岗位的匹配度，并给出具体的提升建议。
你擅长从技能、经验、潜力等多个维度进行综合评估。""",
        "temperature": 0.3,
        "max_tokens": 3000,
    },
    "career_advisor": {
        "role": "职业发展顾问",
        "goal": "提供个性化的职业发展建议，规划职业路径，推荐学习资源",
        "backstory": """你是一位职业规划专家，帮助无数职场人找到适合自己的发展方向。
你善于分析个人优势，制定切实可行的职业发展计划。
你的建议既有战略高度，又有实操性，深受用户好评。""",
        "temperature": 0.5,
        "max_tokens": 4000,
    },
    "report_generator": {
        "role": "报告撰写专家",
        "goal": "生成结构清晰、内容丰富的职业规划报告",
        "backstory": """你是一位专业的报告撰写专家，擅长将复杂的分析结果转化为易于理解的报告内容。
你的报告结构清晰、建议具体，深受用户好评。
你善于用数据说话，同时保持文字的温度和感染力。""",
        "temperature": 0.3,
        "max_tokens": 5000,
    },
}


TASK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "analyze_resume": {
        "description": """分析以下简历内容，提取关键信息：

简历内容：
{resume_content}

请从以下维度进行分析：
1. 基本信息：姓名、学历、联系方式等
2. 教育背景：学校、专业、学历层次
3. 专业技能：技术技能和熟练程度
4. 实习经历：公司、职位、主要工作内容
5. 项目经验：项目名称、技术栈、个人贡献
6. 证书奖项：专业证书和获奖情况
7. 综合评估：简历完整度、竞争力评分、亮点和不足

请以JSON格式返回分析结果。""",
        "expected_output": """一个包含以下字段的结构化JSON对象：
- basic_info: 基本信息
- education: 教育背景列表
- skills: 技能列表（包含名称和熟练程度）
- internships: 实习经历列表
- projects: 项目经验列表
- certifications: 证书列表
- awards: 奖项列表
- completeness_score: 完整度评分(0-100)
- quality_score: 质量评分(0-100)
- highlights: 亮点列表
- weaknesses: 不足列表
- suggestions: 改进建议列表""",
    },
    "match_jobs": {
        "description": """根据简历分析结果，匹配以下目标岗位：

简历分析结果：
{resume_analysis}

目标岗位列表：
{target_jobs}

请对每个岗位进行匹配度分析，包括：
1. 综合匹配度评分
2. 各维度评分（基本要求、专业技能、职业素养、发展潜力、市场需求）
3. 匹配的技能列表
4. 技能差距列表
5. 匹配建议

请以JSON格式返回匹配结果。""",
        "expected_output": """一个包含匹配结果列表的JSON对象，每个匹配结果包含：
- job_title: 岗位名称
- match_score: 综合匹配度(0-100)
- dimensions: 各维度评分
- matched_skills: 匹配的技能列表
- gap_skills: 技能差距列表
- recommendation: 匹配建议""",
    },
    "generate_advice": {
        "description": """根据简历分析和岗位匹配结果，生成职业发展建议：

简历分析结果：
{resume_analysis}

岗位匹配结果：
{match_results}

请提供以下建议：
1. 职业方向建议：最适合的发展方向
2. 发展路径规划：短期、中期、长期目标
3. 技能提升优先级：最需要学习的技能
4. 行动计划：具体的行动步骤
5. 时间规划：建议的时间安排

请以JSON格式返回建议。""",
        "expected_output": """一个包含职业发展建议的JSON对象：
- career_direction: 职业方向建议
- development_path: 发展路径列表
- skill_priorities: 技能提升优先级列表
- action_items: 行动计划列表
- timeline: 时间规划""",
    },
    "generate_report": {
        "description": """根据以上分析结果，生成职业规划报告：

简历分析结果：
{resume_analysis}

岗位匹配结果：
{match_results}

职业建议：
{career_advice}

请生成一份结构清晰、内容丰富的职业规划报告，包括：
1. 个人画像摘要
2. 岗位匹配分析
3. 技能分析与提升建议
4. 职业发展路径
5. 行动计划
6. 时间规划

请以JSON格式返回报告内容。""",
        "expected_output": """一个包含职业规划报告的JSON对象：
- title: 报告标题
- sections: 报告章节列表，每个章节包含：
  - id: 章节ID
  - title: 章节标题
  - content: 章节内容""",
    },
}


CREW_CONFIGS: Dict[str, Dict[str, Any]] = {
    "career_planning": {
        "name": "职业规划Crew",
        "description": "负责完整的职业规划分析和报告生成",
        "process": "sequential",
        "memory": True,
        "verbose": True,
    },
    "quick_analysis": {
        "name": "快速分析Crew",
        "description": "负责快速的简历分析和岗位匹配",
        "process": "sequential",
        "memory": False,
        "verbose": False,
    },
}
