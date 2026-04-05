# -*- coding: utf-8 -*-
"""
LLM输出校准模块
实现温度参数调整和幻觉检测功能

功能：
1. 动态温度参数调整（基于任务类型）
2. 幻觉检测（事实一致性验证）
3. 输出一致性校验
4. 置信度评分
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型枚举"""
    STRUCTURED_EXTRACTION = "structured_extraction"
    MATCHING_ANALYSIS = "matching_analysis"
    CHAT_CONVERSATION = "chat_conversation"
    REPORT_GENERATION = "report_generation"
    CREATIVE_WRITING = "creative_writing"


@dataclass
class TemperatureConfig:
    """温度参数配置"""
    task_type: TaskType
    temperature: float
    description: str
    consistency_threshold: float


TEMPERATURE_PRESETS: Dict[TaskType, TemperatureConfig] = {
    TaskType.STRUCTURED_EXTRACTION: TemperatureConfig(
        task_type=TaskType.STRUCTURED_EXTRACTION,
        temperature=0.1,
        description="结构化数据提取，需要高度确定性",
        consistency_threshold=0.95,
    ),
    TaskType.MATCHING_ANALYSIS: TemperatureConfig(
        task_type=TaskType.MATCHING_ANALYSIS,
        temperature=0.2,
        description="匹配分析，需要稳定输出",
        consistency_threshold=0.90,
    ),
    TaskType.CHAT_CONVERSATION: TemperatureConfig(
        task_type=TaskType.CHAT_CONVERSATION,
        temperature=0.7,
        description="对话交互，允许一定创造性",
        consistency_threshold=0.70,
    ),
    TaskType.REPORT_GENERATION: TemperatureConfig(
        task_type=TaskType.REPORT_GENERATION,
        temperature=0.3,
        description="报告生成，需要事实准确",
        consistency_threshold=0.85,
    ),
    TaskType.CREATIVE_WRITING: TemperatureConfig(
        task_type=TaskType.CREATIVE_WRITING,
        temperature=0.8,
        description="创意写作，鼓励多样性",
        consistency_threshold=0.60,
    ),
}


@dataclass
class HallucinationCheckResult:
    """幻觉检测结果"""
    is_hallucination: bool
    confidence: float
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class HallucinationDetector:
    """幻觉检测器"""
    
    HALLUCINATION_PATTERNS = [
        (r'\b(\d{4})年(\d{1,2})月(\d{1,2})日\b', '具体日期'),
        (r'\b\d{11,}\b', '电话号码'),
        (r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '邮箱地址'),
        (r'\b\d+\.\d+\.\d+\.\d+\b', 'IP地址'),
        (r'据(权威|最新|官方)(数据|研究|报告)', '权威引用'),
        (r'(研究表明|调查显示|统计表明)', '研究引用'),
        (r'具体薪资[是为][\d-]+', '具体薪资'),
        (r'公司.*?(市值|估值|营收).*?\d+', '公司财务数据'),
    ]
    
    FACTUAL_PATTERNS = [
        (r'Java.*?(面向对象|OOP)', True),
        (r'Python.*?(解释型|动态)', True),
        (r'MySQL.*?(关系型|数据库)', True),
        (r'Docker.*?(容器|虚拟化)', True),
    ]
    
    def __init__(self):
        self._known_facts: Dict[str, Any] = {}
    
    def check_response(
        self,
        response: str,
        context: Dict[str, Any] = None,
        task_type: TaskType = TaskType.CHAT_CONVERSATION,
    ) -> HallucinationCheckResult:
        """检查响应是否存在幻觉"""
        issues = []
        suggestions = []
        
        for pattern, desc in self.HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                issues.append(f"可能包含虚构的{desc}: {matches[:3]}")
                suggestions.append(f"建议验证{desc}的准确性或使用模糊表述")
        
        if context:
            context_skills = set(context.get('skills', []))
            response_lower = response.lower()
            
            for skill in context_skills:
                skill_clean = skill.split('（')[0].split('(')[0].strip().lower()
                if skill_clean and skill_clean not in response_lower:
                    pass
        
        vague_count = len(re.findall(r'(可能|大概|大约|左右|一般|通常)', response))
        if vague_count > 5:
            issues.append(f"过度使用模糊表述({vague_count}次)")
        
        confidence = self._calculate_confidence(issues, task_type)
        is_hallucination = confidence < TEMPERATURE_PRESETS[task_type].consistency_threshold
        
        return HallucinationCheckResult(
            is_hallucination=is_hallucination,
            confidence=confidence,
            issues=issues,
            suggestions=suggestions,
        )
    
    def _calculate_confidence(
        self,
        issues: List[str],
        task_type: TaskType,
    ) -> float:
        """计算置信度"""
        if not issues:
            return 1.0
        
        severity_weights = {
            '具体日期': 0.15,
            '电话号码': 0.20,
            '邮箱地址': 0.15,
            '权威引用': 0.25,
            '研究引用': 0.25,
            '具体薪资': 0.30,
            '公司财务数据': 0.30,
            '过度使用模糊表述': 0.10,
        }
        
        total_penalty = 0.0
        for issue in issues:
            for keyword, weight in severity_weights.items():
                if keyword in issue:
                    total_penalty += weight
                    break
        
        threshold = TEMPERATURE_PRESETS[task_type].consistency_threshold
        confidence = max(threshold - total_penalty * 0.5, 0.0)
        
        return min(confidence, 1.0)


class OutputCalibrator:
    """输出校准器"""
    
    def __init__(self):
        self.hallucination_detector = HallucinationDetector()
        self._calibration_history: List[Dict] = []
    
    def get_temperature(self, task_type: TaskType) -> float:
        """获取任务对应的温度参数"""
        return TEMPERATURE_PRESETS[task_type].temperature
    
    def calibrate_output(
        self,
        response: str,
        task_type: TaskType,
        context: Dict[str, Any] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """校准输出"""
        hallucination_result = self.hallucination_detector.check_response(
            response, context, task_type
        )
        
        calibration_info = {
            "task_type": task_type.value,
            "temperature_used": self.get_temperature(task_type),
            "hallucination_check": {
                "is_hallucination": hallucination_result.is_hallucination,
                "confidence": hallucination_result.confidence,
                "issues": hallucination_result.issues,
                "suggestions": hallucination_result.suggestions,
            },
            "calibrated": False,
        }
        
        calibrated_response = response
        
        if hallucination_result.is_hallucination:
            calibrated_response = self._apply_calibration(
                response, hallucination_result
            )
            calibration_info["calibrated"] = True
        
        self._calibration_history.append({
            "task_type": task_type.value,
            "original_length": len(response),
            "calibrated_length": len(calibrated_response),
            "confidence": hallucination_result.confidence,
        })
        
        return calibrated_response, calibration_info
    
    def _apply_calibration(
        self,
        response: str,
        hallucination_result: HallucinationCheckResult,
    ) -> str:
        """应用校准修正"""
        disclaimer = "\n\n[注：以上内容中部分数据可能需要进一步验证]"
        
        if hallucination_result.confidence < 0.5:
            warning = "【提示】以下内容可能包含不确定信息，请谨慎参考：\n"
            return warning + response + disclaimer
        
        return response + disclaimer
    
    def check_consistency(
        self,
        responses: List[str],
        task_type: TaskType,
    ) -> Dict[str, Any]:
        """检查多次输出的一致性"""
        if len(responses) < 2:
            return {"consistent": True, "similarity": 1.0}
        
        def extract_key_info(text: str) -> set:
            numbers = set(re.findall(r'\d+(?:\.\d+)?', text))
            keywords = set(re.findall(r'[\u4e00-\u9fa5]{2,}', text))
            return numbers | keywords
        
        key_infos = [extract_key_info(r) for r in responses]
        
        similarities = []
        for i in range(len(key_infos)):
            for j in range(i + 1, len(key_infos)):
                intersection = len(key_infos[i] & key_infos[j])
                union = len(key_infos[i] | key_infos[j])
                similarity = intersection / union if union > 0 else 0
                similarities.append(similarity)
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        threshold = TEMPERATURE_PRESETS[task_type].consistency_threshold
        is_consistent = avg_similarity >= threshold
        
        return {
            "consistent": is_consistent,
            "similarity": avg_similarity,
            "threshold": threshold,
            "sample_count": len(responses),
        }
    
    def get_calibration_stats(self) -> Dict[str, Any]:
        """获取校准统计信息"""
        if not self._calibration_history:
            return {"total_calibrations": 0}
        
        total = len(self._calibration_history)
        avg_confidence = sum(
            h["confidence"] for h in self._calibration_history
        ) / total
        
        task_counts = Counter(h["task_type"] for h in self._calibration_history)
        
        return {
            "total_calibrations": total,
            "average_confidence": avg_confidence,
            "task_distribution": dict(task_counts),
        }


output_calibrator = OutputCalibrator()
