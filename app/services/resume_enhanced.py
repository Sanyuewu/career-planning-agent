# -*- coding: utf-8 -*-
"""
简历解析增强模块
目标：将特征提取完整度从46.7%提升至85%
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class FieldExtractionResult:
    """字段提取结果"""
    value: Any
    confidence: float = 1.0
    source: str = "regex"  # regex, llm, default
    raw_text: str = ""


class ResumeFieldExtractor:
    """
    简历字段提取器
    使用正则表达式+规则引擎增强关键信息提取
    """
    
    def __init__(self):
        self.degree_patterns = [
            r"(博士|PhD|phd)",
            r"(硕士|研究生|Master|master|M\.S\.|MS)",
            r"(本科|学士|Bachelor|bachelor|B\.S\.|BS)",
            r"(专科|大专|高职|Associate)",
        ]
        
        self.grade_patterns = [
            r"(大一|大二|大三|大四|研一|研二|研三)",
            r"(应届|往届|毕业生)",
            r"(20\d{2})\s*届",
            r"(20\d{2})\s*级",
        ]
        
        self.intent_keywords = [
            "求职意向", "期望职位", "应聘职位", "目标岗位",
            "职业目标", "期望工作", "意向岗位", "应聘",
        ]
        
        self.school_keywords = [
            "大学", "学院", "研究院", "研究所",
            "University", "College", "Institute",
        ]
        
        self.elite_schools = [
            "清华", "北大", "浙大", "复旦", "交大", "上海交大",
            "南京大学", "武汉大学", "中山大学", "华中科技",
            "西安交通", "同济", "南开", "天津大学",
            "北京理工", "东南大学", "华东师范", "厦门大学",
            "985", "211", "双一流",
        ]
        
        self.skill_indicators = [
            "技能", "技术栈", "编程语言", "开发工具",
            "框架", "数据库", "编程", "开发",
            "Skills", "Technologies", "Programming",
        ]
        
        self.cert_keywords = [
            "证书", "认证", "资格", "资质",
            "Certificate", "Certification", "License",
            "CET", "英语四六级", "雅思", "托福",
            "CPA", "CFA", "ACCA", "PMP",
        ]
        
        self.award_keywords = [
            "奖项", "荣誉", "获奖", "竞赛",
            "Award", "Honor", "Prize", "Competition",
            "一等奖", "二等奖", "三等奖", "优秀奖",
            "国家级", "省级", "市级",
        ]
        
        self.internship_keywords = [
            "实习", "兼职", "工作经历", "工作经验",
            "Intern", "Internship", "Work Experience",
        ]
        
        self.project_keywords = [
            "项目", "课题", "研究", "作品",
            "Project", "Research", "Thesis",
        ]

    def extract_degree(self, text: str) -> FieldExtractionResult:
        """提取学历信息"""
        for pattern in self.degree_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                degree = match.group(1)
                normalized = self._normalize_degree(degree)
                return FieldExtractionResult(
                    value=normalized,
                    confidence=0.95,
                    source="regex",
                    raw_text=degree
                )
        return FieldExtractionResult(value="本科", confidence=0.5, source="default")

    def _normalize_degree(self, degree: str) -> str:
        """标准化学历名称"""
        degree = degree.lower()
        if "博士" in degree or "phd" in degree:
            return "博士"
        elif "硕士" in degree or "研究生" in degree or "master" in degree or "m.s" in degree:
            return "硕士"
        elif "本科" in degree or "学士" in degree or "bachelor" in degree or "b.s" in degree:
            return "本科"
        elif "专科" in degree or "大专" in degree or "高职" in degree or "associate" in degree:
            return "专科"
        return "本科"

    def extract_grade(self, text: str) -> FieldExtractionResult:
        """提取年级信息"""
        for pattern in self.grade_patterns:
            match = re.search(pattern, text)
            if match:
                grade = match.group(1)
                return FieldExtractionResult(
                    value=grade,
                    confidence=0.9,
                    source="regex",
                    raw_text=grade
                )
        return FieldExtractionResult(value="应届", confidence=0.5, source="default")

    def extract_career_intent(self, text: str) -> FieldExtractionResult:
        """提取求职意向"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            for keyword in self.intent_keywords:
                if keyword in line_stripped:
                    intent_match = re.search(
                        r'[:：]\s*(.+?)(?:\s*$|\s*[,，]|\s*[/／])',
                        line_stripped
                    )
                    if intent_match:
                        intent = intent_match.group(1).strip()
                        if intent and len(intent) < 30:
                            return FieldExtractionResult(
                                value=intent,
                                confidence=0.9,
                                source="regex",
                                raw_text=line_stripped
                            )
                    
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and len(next_line) < 30 and not any(kw in next_line for kw in self.intent_keywords):
                            return FieldExtractionResult(
                                value=next_line,
                                confidence=0.8,
                                source="regex",
                                raw_text=next_line
                            )
        
        job_title_patterns = [
            r"((?:前端|后端|全栈|Java|Python|Go|测试|运维|产品|运营|数据|算法|UI|设计)[开发工程师]*?(?:/[\u4e00-\u9fa5]+)?)",
            r"((?:软件|硬件|系统|网络|安全)[工程师]*)",
        ]
        
        for pattern in job_title_patterns:
            match = re.search(pattern, text)
            if match:
                return FieldExtractionResult(
                    value=match.group(1),
                    confidence=0.7,
                    source="regex",
                    raw_text=match.group(0)
                )
        
        return FieldExtractionResult(value=None, confidence=0.0, source="default")

    def extract_school_info(self, text: str) -> Tuple[FieldExtractionResult, FieldExtractionResult]:
        """提取学校和专业信息"""
        school_result = FieldExtractionResult(value=None, confidence=0.0, source="default")
        major_result = FieldExtractionResult(value=None, confidence=0.0, source="default")
        
        edu_patterns = [
            r'(\d{4}[-–—]\d{0,4})\s*([^\s]+(?:大学|学院)[^\s]*)\s+([^\s]+专业?[^\s]*)',
            r'([^\s]*(?:大学|学院)[^\s]*)\s+([^\s]+专业)',
            r'([^\s]*(?:大学|学院)[^\s]*)',
        ]
        
        for pattern in edu_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    for g in groups:
                        g = g.strip()
                        if any(kw in g for kw in self.school_keywords):
                            school_result = FieldExtractionResult(
                                value=g,
                                confidence=0.9,
                                source="regex",
                                raw_text=g
                            )
                        elif "专业" in g or len(g) > 2 and len(g) < 20:
                            major_result = FieldExtractionResult(
                                value=g.replace("专业", ""),
                                confidence=0.8,
                                source="regex",
                                raw_text=g
                            )
                break
        
        return school_result, major_result

    def extract_skills_enhanced(self, text: str) -> FieldExtractionResult:
        """增强版技能提取"""
        skills = set()
        
        skill_section = ""
        lines = text.split('\n')
        in_skill_section = False
        
        for line in lines:
            line_stripped = line.strip()
            if any(kw in line_stripped for kw in self.skill_indicators):
                in_skill_section = True
                skill_section = line_stripped
                continue
            
            if in_skill_section:
                if line_stripped and not any(kw in line_stripped for kw in ["经历", "教育", "项目", "工作"]):
                    skill_section += " " + line_stripped
                else:
                    in_skill_section = False
        
        tech_patterns = [
            r'\b(Python|Java|JavaScript|TypeScript|Go|C\+\+|C#|Ruby|PHP|Swift|Kotlin|Rust)\b',
            r'\b(React|Vue|Angular|Node\.js|Spring|Django|Flask|Express|FastAPI)\b',
            r'\b(MySQL|PostgreSQL|MongoDB|Redis|Oracle|SQL Server|Elasticsearch)\b',
            r'\b(Docker|Kubernetes|Jenkins|Git|Linux|Nginx|Apache)\b',
            r'\b(TensorFlow|PyTorch|Keras|Scikit-learn|Pandas|NumPy)\b',
            r'\b(AWS|Azure|GCP|阿里云|腾讯云|华为云)\b',
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(matches)
        
        chinese_skill_pattern = r'[\u4e00-\u9fa5]{2,8}(?:开发|设计|分析|测试|运维|管理)'
        cn_matches = re.findall(chinese_skill_pattern, text)
        skills.update(cn_matches)
        
        return FieldExtractionResult(
            value=list(skills),
            confidence=0.85 if skills else 0.0,
            source="regex",
            raw_text=skill_section[:200] if skill_section else ""
        )

    def extract_internships_enhanced(self, text: str) -> FieldExtractionResult:
        """增强版实习经历提取"""
        internships = []
        
        intern_pattern = r'(\d{4}[./-]\d{1,2})\s*[-–—~至]*\s*(\d{4}[./-]\d{1,2}|至今|present)?\s*([^\s]+)\s+([^\s]+(?:实习生|工程师|助理|专员|经理)?)'
        
        matches = re.findall(intern_pattern, text)
        for match in matches:
            start_date, end_date, company, role = match
            if any(kw in company.lower() or kw in role.lower() for kw in ["实习", "intern"]):
                internships.append({
                    "company": company,
                    "role": role,
                    "start_date": start_date,
                    "end_date": end_date if end_date else "至今",
                    "duration_months": self._estimate_duration(start_date, end_date),
                    "description": ""
                })
        
        return FieldExtractionResult(
            value=internships,
            confidence=0.8 if internships else 0.0,
            source="regex",
            raw_text=""
        )

    def _estimate_duration(self, start: str, end: str) -> int:
        """估算实习时长（月）"""
        try:
            start_parts = re.findall(r'\d+', start)
            if len(start_parts) >= 2:
                start_year = int(start_parts[0])
                start_month = int(start_parts[1])
            else:
                return 3
            
            if end and end not in ["至今", "present"]:
                end_parts = re.findall(r'\d+', end)
                if len(end_parts) >= 2:
                    end_year = int(end_parts[0])
                    end_month = int(end_parts[1])
                    return (end_year - start_year) * 12 + (end_month - start_month)
            
            return 3
        except:
            return 3

    def extract_certs_and_awards(self, text: str) -> Tuple[FieldExtractionResult, FieldExtractionResult]:
        """提取证书和奖项"""
        certs = []
        awards = []
        
        cert_patterns = [
            r'(CET[-\s]?[46]|英语[四六]级|雅思|托福|GRE)',
            r'(CPA|CFA|ACCA|FRM|PMP|软考|计算机等级)',
            r'([\u4e00-\u9fa5]{2,10}(?:证书|认证|资格))',
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            certs.extend(matches)
        
        award_patterns = [
            r'((?:国家级|省级|市级)[^\s]*(?:奖|荣誉|称号))',
            r'((?:一等|二等|三等|优秀)[^\s]*(?:奖|荣誉))',
            r'([\u4e00-\u9fa5]{2,15}(?:竞赛|比赛)[^\s]*(?:奖)?)',
        ]
        
        for pattern in award_patterns:
            matches = re.findall(pattern, text)
            awards.extend(matches)
        
        return (
            FieldExtractionResult(value=list(set(certs)), confidence=0.8 if certs else 0.0, source="regex"),
            FieldExtractionResult(value=list(set(awards)), confidence=0.8 if awards else 0.0, source="regex")
        )


class ResumeParseQualityEvaluator:
    """
    简历解析质量评估器
    设定最低解析阈值，确保输出质量
    """
    
    MIN_REQUIRED_FIELDS = ["name", "education", "skills"]
    MIN_COMPLETENESS = 0.3
    
    def __init__(self):
        self.extractor = ResumeFieldExtractor()
    
    def evaluate_parse_result(self, result: Dict) -> Dict:
        """评估解析结果质量"""
        issues = []
        warnings = []
        
        for field in self.MIN_REQUIRED_FIELDS:
            if field == "name":
                if not result.get("basic_info", {}).get("name"):
                    issues.append(f"缺少必填字段: {field}")
            elif field == "education":
                if not result.get("education"):
                    issues.append(f"缺少必填字段: {field}")
            elif field == "skills":
                if not result.get("skills") or len(result.get("skills", [])) < 1:
                    warnings.append("技能字段为空或过少")
        
        completeness = result.get("completeness", 0)
        if completeness < self.MIN_COMPLETENESS:
            issues.append(f"完整度{completeness:.0%}低于最低阈值{self.MIN_COMPLETENESS:.0%}")
        
        if not result.get("career_intent"):
            warnings.append("未提取到求职意向")
        
        if not result.get("internships"):
            warnings.append("未提取到实习经历")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "quality_score": self._calculate_quality_score(result, issues, warnings),
        }
    
    def _calculate_quality_score(self, result: Dict, issues: List, warnings: List) -> float:
        """计算解析质量分数"""
        base_score = result.get("completeness", 0) * 100
        
        issue_penalty = len(issues) * 20
        warning_penalty = len(warnings) * 5
        
        return max(0, base_score - issue_penalty - warning_penalty)
    
    def enhance_parse_result(self, original_text: str, llm_result: Dict) -> Dict:
        """使用规则引擎增强LLM解析结果"""
        enhanced = llm_result.copy()
        
        degree_result = self.extractor.extract_degree(original_text)
        if degree_result.value and degree_result.confidence > 0.8:
            if enhanced.get("education"):
                for edu in enhanced["education"]:
                    if not edu.get("degree"):
                        edu["degree"] = degree_result.value
        
        intent_result = self.extractor.extract_career_intent(original_text)
        if intent_result.value and intent_result.confidence > 0.7:
            if not enhanced.get("career_intent"):
                enhanced["career_intent"] = intent_result.value
        
        grade_result = self.extractor.extract_grade(original_text)
        if grade_result.value and grade_result.confidence > 0.7:
            if enhanced.get("basic_info"):
                if not enhanced["basic_info"].get("grade"):
                    enhanced["basic_info"]["grade"] = grade_result.value
        
        skills_result = self.extractor.extract_skills_enhanced(original_text)
        if skills_result.value:
            existing_skills = set(enhanced.get("skills", []))
            new_skills = set(skills_result.value)
            enhanced["skills"] = list(existing_skills | new_skills)
        
        certs_result, awards_result = self.extractor.extract_certs_and_awards(original_text)
        if certs_result.value:
            existing_certs = set(enhanced.get("certs", []))
            enhanced["certs"] = list(existing_certs | set(certs_result.value))
        if awards_result.value:
            existing_awards = set(enhanced.get("awards", []))
            enhanced["awards"] = list(existing_awards | set(awards_result.value))
        
        school_result, major_result = self.extractor.extract_school_info(original_text)
        if school_result.value and school_result.confidence > 0.8:
            if enhanced.get("basic_info"):
                if not enhanced["basic_info"].get("school"):
                    enhanced["basic_info"]["school"] = school_result.value
        if major_result.value and major_result.confidence > 0.8:
            if enhanced.get("basic_info"):
                if not enhanced["basic_info"].get("major"):
                    enhanced["basic_info"]["major"] = major_result.value
        
        return enhanced


resume_field_extractor = ResumeFieldExtractor()
resume_quality_evaluator = ResumeParseQualityEvaluator()
