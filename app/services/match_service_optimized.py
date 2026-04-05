# -*- coding: utf-8 -*-
"""
优化版匹配算法服务
目标：提升匹配准确率、响应速度、系统稳定性

优化内容：
1. 多层次技能匹配策略（精确→模糊→语义）
2. 技能熟练度权重计算
3. 缓存机制提升性能
4. 完善的异常处理和降级策略
5. 性能指标监控
"""

import json
import math
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Set
from dataclasses import dataclass, field
from functools import lru_cache
from collections import defaultdict
import asyncio

from app.constants import SKILL_COMBOS

logger = logging.getLogger(__name__)

# 已知误判的子串对：a 是 b 的子串但两者不是同一技术
# 例如 "java" ⊂ "javascript"，但 Java 和 JavaScript 是完全不同的语言
_SUBSTRING_EXCLUSIONS: frozenset = frozenset({
    ('java', 'javascript'), ('javascript', 'java'),
})

# 具体技术名称集合：这些技术之间不允许通过"同属一类"进行跨匹配
# 例如：Python 和 Java 都是"后端开发"，但 Python 不能替代 Java
_CATEGORY_SPECIFIC_TECHS: frozenset = frozenset({
    # 编程语言
    'java', 'python', 'javascript', 'js', 'typescript', 'go', 'golang', 'php', 'ruby', 'rust',
    'c#', 'csharp', 'node', 'nodejs', 'kotlin', 'swift', 'scala',
    # 前端框架
    'vue', 'react', 'angular', 'svelte', 'html', 'css',
    # 数据库
    'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite', 'memcached', 'elasticsearch',
    # 大数据/ML
    'hadoop', 'spark', 'hive', 'flink', 'kafka', 'tensorflow', 'pytorch', 'pandas', 'numpy',
    # 容器/DevOps
    'docker', 'kubernetes', 'k8s',
})


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_time_ms: float = 0.0
    skill_match_time_ms: float = 0.0
    basic_match_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    cache_hit: bool = False
    degraded: bool = False


@dataclass
class SkillMatchResult:
    """技能匹配结果"""
    matched_skills: List[str]
    gap_skills: List[str]
    score: float
    confidence: float
    match_details: List[Dict]


class OptimizedSkillMatcher:
    """
    优化版技能匹配器
    采用多层次匹配策略：精确匹配 → 模糊匹配 → 语义匹配
    """
    
    SKILL_SYNONYMS = {
        'java': {'java', 'javaee', 'jdk', 'jvm', 'spring', 'springboot', 'spring boot', 'java开发', 'java后端', 'java工程师'},
        'python': {'python', 'py', 'django', 'flask', 'fastapi', 'python开发', 'python后端', 'python数据分析'},
        'javascript': {'javascript', 'js', 'ecmascript', 'es6', 'es7', 'es8', '前端开发', '前端', 'js开发'},
        'typescript': {'typescript', 'ts', 'ts开发'},
        'react': {'react', 'reactjs', 'react.js', 'react native', 'react开发'},
        'vue': {'vue', 'vuejs', 'vue.js', 'vue2', 'vue3', 'vue开发', 'vue前端', 'vue框架', 'vue/react框架'},
        'angular': {'angular', 'angularjs', 'angular.js', 'angular开发'},
        'node': {'node', 'nodejs', 'node.js', 'express', 'node开发', 'node后端'},
        # 关系型数据库（具体技术 → 概念名）
        'mysql': {
            'mysql', 'mariadb', 'sql', '数据库', '数据库设计', '数据库开发', '数据库优化',
            'mysql开发', '数据库操作与优化', '关系型数据库', 'rdbms', '关系数据库',
            '数据库管理', '结构化数据库',
        },
        'postgresql': {'postgresql', 'postgres', 'psql', 'pg数据库', '关系型数据库', 'rdbms', '关系数据库'},
        'mongodb': {'mongodb', 'mongo', 'nosql', '非关系型数据库', 'nosql数据库'},
        'oracle': {'oracle', 'oracle数据库', 'oracle开发', '关系型数据库'},
        # 缓存（具体技术 → 概念名）
        'redis': {
            'redis', 'redis缓存', '缓存', '缓存技术', '缓存系统', '分布式缓存',
            '缓存设计', '缓存中间件', '缓存优化', '内存数据库', '高速缓存',
        },
        'memcached': {'memcached', '缓存', '缓存技术', '缓存中间件'},
        # 容器化（具体技术 → 概念名）
        'docker': {
            'docker', '容器', 'container', '容器化', '容器化部署', 'docker容器',
            '容器技术', 'docker容器化',
        },
        'kubernetes': {
            'kubernetes', 'k8s', 'k3s', '容器编排', 'k8s部署', 'k8s集群',
            'kubernetes集群', '容器集群', '云原生', 'k8s运维',
        },
        # Linux/运维
        'linux': {
            'linux', 'ubuntu', 'centos', 'unix', 'linux运维', 'linux服务器',
            'linux系统管理', 'linux系统', '操作系统', 'linux操作系统',
        },
        # Shell
        'shell': {
            'shell', 'shell脚本', 'bash', 'shell编程', 'bash脚本', 'shell开发',
            '脚本编程', '自动化脚本', 'linux脚本',
        },
        # Git/版本控制
        'git': {
            'git', 'github', 'gitlab', '版本控制', 'git版本控制',
            '代码版本管理', '代码管理', '版本管理', 'svn', '代码仓库',
        },
        'ml': {'ml', 'machine learning', '机器学习', '机器学习算法', 'ml算法'},
        'dl': {'dl', 'deep learning', '深度学习', '深度学习算法', '神经网络'},
        'ai': {'ai', 'artificial intelligence', '人工智能', 'ai算法'},
        'nlp': {'nlp', 'natural language processing', '自然语言处理', 'nlp算法'},
        'cv': {'cv', 'computer vision', '计算机视觉', '图像处理', '视觉算法'},
        'html': {'html', 'html5', 'html/css', '网页开发', 'web前端', 'html/css/javascript'},
        'css': {'css', 'css3', 'html/css', '样式', '样式开发'},
        'sql': {
            'sql', 'sql查询', 'sql开发', '数据库查询', '结构化查询',
            '数据库操作与优化', 'sql语句', 'sql优化',
        },
        'pandas': {'pandas', 'pandas数据分析', '数据分析', '数据可视化'},
        'numpy': {'numpy', 'numpy计算', '数值计算'},
        'tensorflow': {'tensorflow', 'tf', 'tensorflow框架', 'pytorch/tensorflow'},
        'pytorch': {'pytorch', 'torch', 'pytorch框架', 'pytorch/tensorflow'},
        'spring': {
            'spring', 'spring框架', 'springboot', 'spring boot', 'springmvc',
            'spring/springboot/springcloud',
        },
        'mybatis': {'mybatis', 'mybatis框架', 'mybatis-plus', 'orm框架'},
        'nginx': {'nginx', 'nginx配置', '反向代理', '负载均衡'},
        'jenkins': {'jenkins', 'ci/cd', '持续集成', '持续部署', 'devops', 'cicd'},
        # 消息队列
        'kafka': {
            'kafka', '消息队列', 'kafka消息队列', 'mq', '消息中间件',
            '消息系统', '事件驱动', '异步消息',
        },
        'rabbitmq': {'rabbitmq', 'rabbitmq消息队列', '消息中间件', '消息队列'},
        'rocketmq': {'rocketmq', '消息队列', '消息中间件'},
        'elasticsearch': {'elasticsearch', 'es', '搜索引擎', '全文检索', 'es搜索'},
        'spark': {'spark', 'spark大数据', '大数据处理', 'spark计算'},
        'hadoop': {'hadoop', 'hdfs', 'mapreduce', '大数据平台'},
        'hive': {'hive', 'hive数据仓库', '数据仓库'},
        'flink': {'flink', 'flink流处理', '实时计算'},
        # 微服务框架（Spring Boot/Gin/gRPC/Dubbo → 微服务框架）
        'microservice': {
            '微服务', '微服务架构', '微服务框架', '微服务开发',
            'spring boot', 'springboot', 'spring cloud', 'springcloud',
            'gin', 'gin框架', 'grpc', 'dubbo',
            'thrift', 'servicemesh', 'istio',
        },
        # 前端工程化
        'frontend_engineering': {
            '前端工程化', '工程化', 'webpack', 'vite', 'rollup', 'babel',
            'webpack打包', '构建工具', '模块打包', '前端构建',
        },
        'c': {'c', 'c语言', 'c编程', 'c/c++'},
        'cpp': {'c++', 'cpp', 'c/c++', '精通c/c++编程语言'},
        '日语': {'日语', '日语沟通能力', '日语能力', 'n1', 'n2', 'n3'},
        '英语': {'英语', '英语沟通', '英语能力', '英语四级', '英语六级'},
        # ── 非IT行业通用能力（覆盖销售/运营/管理/HR/金融） ───────────────────
        # 注意：规范键必须包含在自身的同义词集合中（与IT技能规范一致）
        '市场开拓': {
            '市场开拓', '市场开拓与客户开发', '业务拓展', '客户开发', '市场开发',
            '拓客', '新客户开发', '市场拓展',
        },
        '客户关系': {
            '客户关系', '客户关系维护', '客情维护', '客情维护与销售',
            '客户管理', '客户维护', '客户关系管理', 'crm', '客户跟进', '客户开发与维护',
        },
        '市场调研': {
            '市场调研', '市场调研与数据分析', '行业研究', '市场分析', '市场研究',
            '竞品调研', '用户调研', '市场与行业分析',
        },
        '竞品分析': {
            '竞品分析', '竞品分析与报告撰写', '竞争分析', '竞品研究',
            '市场竞争分析', '竞对分析',
        },
        '商务谈判': {
            '商务谈判', '商务谈判与方案制定', '谈判技巧', '商务沟通',
            '商务洽谈', '谈判与沟通',
        },
        '团队管理': {
            '团队管理', '团队管理与建设', '人员管理', '团队建设', '组织管理',
            '人员培训', '下属管理', '带队经验',
        },
        '方案策划': {
            '方案策划', '方案策划与执行', '活动策划', '策划执行', '项目策划',
            '创意策划', '营销策划', '内容策划',
        },
        '销售技能': {
            '销售技能', '销售', '销售与业务拓展', '销售技巧', '直销', '电话销售',
            '销售谈判', '客户销售', '销售推广', '线下地推与拉新',
        },
        '沟通表达': {
            '沟通表达', '沟通与演讲', '演讲能力', '公众演讲', '口头表达',
            '汇报能力', '表达能力', '客户沟通与情绪安抚',
        },
        '办公软件': {
            '办公软件', 'office', 'microsoft office', '办公软件及系统操作',
            'word', 'excel', 'ppt', 'wps', '办公套件',
            '熟练操作office办公软件（word/excel/ppt）',
        },
        '数据分析通用': {
            '数据分析通用', '数据分析', '基础数据分析', '数据分析报告',
            '数据统计', '数据处理', '基础运营分析', '数据分析与可视化',
        },
        '招聘': {
            '招聘', '招聘专员', '人才招募', '简历筛选', '面试', '招聘流程',
            '校园招聘', '社招', '人员招募',
        },
        '培训': {
            '培训', '员工培训', '培训设计', '课程开发', '培训实施', '讲师',
        },
        '内容运营': {
            '内容运营', '内容创作', '文案撰写', '新媒体运营', '社交媒体运营',
            '公众号运营', '短视频运营',
        },
        '用户运营': {
            '用户运营', '社区运营', '用户增长', '用户维护', '粉丝运营',
        },
        '财务分析': {
            '财务分析', '财务报告', '成本分析', '预算管理', '财务建模',
            '财务数据分析',
        },
        '法务合规': {
            '法务合规', '法务', '合同审核', '法律合规', '合规管理', '风险控制',
            '律师助理', '法律事务',
        },
        '标书投标': {
            '标书投标', '标书制作', '标书制作与投标流程管理', '投标', '招投标',
            '投标文件编制',
        },
        '项目管理': {
            '项目管理', '项目协调', '项目专员', '项目推进', '项目跟进',
            '项目实施', 'pmp',
        },
    }

    SKILL_CATEGORY_MAP = {
        '前端开发': ['javascript', 'js', 'vue', 'react', 'angular', 'html', 'css', 'typescript', '前端', 'web前端', '前端开发'],
        '后端开发': ['java', 'python', 'node', 'go', 'php', '后端', '服务端', '后端开发'],
        '数据库': ['mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sql', '数据库', '数据库设计', '数据库优化', '数据库开发'],
        '缓存技术': ['redis', 'memcached', '缓存', '分布式缓存', '缓存系统'],
        '容器化部署': ['docker', 'kubernetes', 'k8s', '容器', '容器化', '容器编排'],
        # 非IT行业技能类别
        '销售运营': ['市场开拓', '客户关系', '商务谈判', '销售技能', '业务拓展', '客户开发', '市场调研', '线下地推与拉新', '客情维护'],
        '产品内容': ['竞品分析', '方案策划', '数据分析通用', '内容运营', '用户运营', '产品规划'],
        '管理行政': ['团队管理', '沟通表达', '办公软件', '项目管理', '行政管理'],
        '人力资源': ['招聘', '培训', '绩效管理', '员工关系'],
        '金融财务': ['财务分析', '数据分析通用', 'excel', '财务管理'],
        '法律合规': ['法务合规', '标书投标', '合同管理'],
        '大数据': ['hadoop', 'spark', 'hive', 'flink', 'kafka', '大数据', '大数据处理'],
        '机器学习': ['ml', 'machine learning', '机器学习', '深度学习', 'ai', '人工智能', 'tensorflow', 'pytorch'],
        '数据分析': ['python', 'sql', 'pandas', 'numpy', '数据分析', '数据可视化', '数据挖掘'],
    }
    
    PROFICIENCY_WEIGHTS = {
        '精通': 1.0,
        '熟练': 0.85,
        '掌握': 0.7,
        '熟悉': 0.6,
        '了解': 0.4,
        'default': 0.85,
    }
    
    SKILL_CATEGORIES = {
        'programming': ['java', 'python', 'javascript', 'typescript', 'go', 'c++', 'c#', 'rust', 'ruby', 'php'],
        'frontend': ['react', 'vue', 'angular', 'html', 'css', 'webpack', 'vite', '前端开发', '前端'],
        'backend': ['spring', 'django', 'flask', 'fastapi', 'express', 'node', '后端开发', '后端'],
        'database': ['mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'elasticsearch', '数据库', '数据库设计'],
        'devops': ['docker', 'kubernetes', 'jenkins', 'git', 'linux', 'nginx', '容器化部署', '容器'],
        'ai_ml': ['tensorflow', 'pytorch', 'keras', 'pandas', 'numpy', 'scikit-learn', '机器学习', '深度学习'],
    }
    
    def __init__(self):
        self._synonym_cache: Dict[str, Set[str]] = {}
        self._category_cache: Dict[str, str] = {}
        self._build_synonym_cache()
        self._build_category_cache()
        self._confidence_calibration: Dict[str, Dict] = self._load_confidence_calibration()

    @staticmethod
    def _load_confidence_calibration() -> Dict[str, Dict]:
        """
        加载 data/eval/confidence_cal.json（由 scripts/benchmark.py 生成）。
        格式：{"buckets": {"high": {"empirical_accuracy": 0.94, ...}, ...}}
        若文件不存在则返回空 dict，系统降级为显示固定文字。
        """
        try:
            cal_path = Path(__file__).parent.parent.parent / "data" / "eval" / "confidence_cal.json"
            if cal_path.exists():
                with open(cal_path, encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("buckets", {})
        except Exception:
            pass
        return {}

    def get_empirical_accuracy(self, confidence: float) -> Optional[float]:
        """
        根据置信度返回该桶的经验准确率（来自基准测试数据）。
        若无校准数据返回 None（调用方降级为固定文字）。
        """
        if not self._confidence_calibration:
            return None
        if confidence >= 0.8:
            bucket = "high"
        elif confidence >= 0.6:
            bucket = "mid"
        else:
            bucket = "low"
        info = self._confidence_calibration.get(bucket, {})
        return info.get("empirical_accuracy")
    
    def _build_synonym_cache(self):
        """构建同义词缓存"""
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            for syn in synonyms:
                self._synonym_cache[syn.lower()] = synonyms
    
    def _build_category_cache(self):
        """构建技能类别缓存"""
        for category, skills in self.SKILL_CATEGORY_MAP.items():
            for skill in skills:
                self._category_cache[skill.lower()] = category
    
    def clean_skill_name(self, skill: str) -> Tuple[str, str]:
        """
        清洗技能名称，返回(清洗后名称, 熟练度)
        
        Examples:
            'Java（精通）' -> ('java', '精通')
            'Python(熟练)' -> ('python', '熟练')
            'MySQL' -> ('mysql', 'default')
        """
        skill_lower = skill.lower().strip()
        
        proficiency = 'default'
        for prof in self.PROFICIENCY_WEIGHTS.keys():
            if prof in skill_lower:
                proficiency = prof
                break
        
        for char in ['（', '(', '【', '[']:
            if char in skill_lower:
                skill_lower = skill_lower.split(char)[0].strip()
        
        for suffix in ['开发', '工程师', '技术', '框架', '语言']:
            if skill_lower.endswith(suffix) and len(skill_lower) > len(suffix):
                skill_lower = skill_lower[:-len(suffix)]
        
        return skill_lower, proficiency
    
    def get_skill_category(self, skill: str) -> str:
        """获取技能所属类别"""
        skill_lower = skill.lower()
        for category, skills in self.SKILL_CATEGORIES.items():
            if any(s in skill_lower or skill_lower in s for s in skills):
                return category
        return 'other'
    
    def match_skills(
        self,
        student_skills: List[str],
        job_skills: List[str],
        job_graph=None,
        job_type: str = "general",
        student_major: str = "",
    ) -> SkillMatchResult:
        """
        多层次技能匹配
        
        策略：
        1. 精确匹配（权重1.0）
        2. 同义词匹配（权重0.9）
        3. 包含匹配（权重0.8）
        4. 语义扩展匹配（权重0.7）
        """
        start_time = time.time()
        
        # 基于岗位类型的技能权重调整
        job_type_weights = {
            'frontend': {'frontend': 1.2, 'programming': 1.1, 'database': 0.8},
            'backend': {'backend': 1.2, 'database': 1.1, 'devops': 0.9},
            'data': {'database': 1.2, 'ai_ml': 1.1, 'programming': 1.0},
            'devops': {'devops': 1.2, 'backend': 1.0, 'database': 0.9},
            'ai': {'ai_ml': 1.3, 'programming': 1.1, 'database': 1.0},
        }
        
        # 基于专业的技能权重调整
        major_skill_weights = {
            '计算机科学与技术': {'programming': 1.2, 'frontend': 1.1, 'backend': 1.2, 'database': 1.1, 'ai_ml': 1.1, 'devops': 1.0},
            '软件工程': {'programming': 1.2, 'frontend': 1.1, 'backend': 1.2, 'devops': 1.1, 'database': 1.0, 'ai_ml': 1.0},
            '电子信息工程': {'programming': 1.1, 'backend': 1.1, 'ai_ml': 1.1, 'database': 1.0, 'frontend': 0.9, 'devops': 1.0},
            '通信工程': {'programming': 1.0, 'backend': 1.0, 'ai_ml': 1.0, 'database': 0.9, 'frontend': 0.9, 'devops': 1.0},
            '自动化': {'programming': 1.0, 'backend': 1.0, 'ai_ml': 1.1, 'database': 0.9, 'frontend': 0.8, 'devops': 1.0},
            '数学与应用数学': {'programming': 1.0, 'ai_ml': 1.2, 'database': 1.0, 'backend': 0.9, 'frontend': 0.8, 'devops': 0.8},
            '物理学': {'programming': 0.9, 'ai_ml': 1.1, 'database': 0.9, 'backend': 0.8, 'frontend': 0.8, 'devops': 0.8},
            '化学': {'programming': 0.8, 'ai_ml': 1.0, 'database': 0.9, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.7},
            '生物学': {'programming': 0.8, 'ai_ml': 1.0, 'database': 0.9, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.7},
            '经济学': {'database': 1.2, 'ai_ml': 1.0, 'programming': 0.9, 'backend': 0.8, 'frontend': 0.8, 'devops': 0.7},
            '金融学': {'database': 1.2, 'ai_ml': 1.0, 'programming': 0.9, 'backend': 0.8, 'frontend': 0.8, 'devops': 0.7},
            '会计学': {'database': 1.2, 'ai_ml': 0.9, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.6},
            '市场营销': {'database': 1.0, 'ai_ml': 0.9, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.8, 'devops': 0.6},
            '工商管理': {'database': 1.0, 'ai_ml': 0.9, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.6},
            '人力资源管理': {'database': 0.9, 'ai_ml': 0.8, 'programming': 0.7, 'backend': 0.6, 'frontend': 0.7, 'devops': 0.5},
            '法学': {'database': 0.9, 'ai_ml': 0.8, 'programming': 0.7, 'backend': 0.6, 'frontend': 0.6, 'devops': 0.5},
            '教育学': {'database': 0.9, 'ai_ml': 0.8, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.8, 'devops': 0.6},
            '心理学': {'database': 0.9, 'ai_ml': 0.9, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.6},
            '英语': {'database': 0.8, 'ai_ml': 0.7, 'programming': 0.7, 'backend': 0.6, 'frontend': 0.7, 'devops': 0.5},
            '汉语言文学': {'database': 0.8, 'ai_ml': 0.7, 'programming': 0.7, 'backend': 0.6, 'frontend': 0.7, 'devops': 0.5},
            '新闻学': {'database': 0.9, 'ai_ml': 0.8, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.9, 'devops': 0.6},
            '历史学': {'database': 0.8, 'ai_ml': 0.7, 'programming': 0.7, 'backend': 0.6, 'frontend': 0.7, 'devops': 0.5},
            '哲学': {'database': 0.8, 'ai_ml': 0.7, 'programming': 0.7, 'backend': 0.6, 'frontend': 0.6, 'devops': 0.5},
            '艺术设计': {'database': 0.7, 'ai_ml': 0.8, 'programming': 0.8, 'backend': 0.6, 'frontend': 1.1, 'devops': 0.5},
            '医学': {'database': 1.0, 'ai_ml': 0.9, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.6},
            '护理学': {'database': 0.9, 'ai_ml': 0.8, 'programming': 0.7, 'backend': 0.6, 'frontend': 0.6, 'devops': 0.5},
            '药学': {'database': 0.9, 'ai_ml': 0.9, 'programming': 0.8, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.6},
            '化学工程': {'programming': 0.9, 'ai_ml': 1.0, 'database': 0.9, 'backend': 0.8, 'frontend': 0.7, 'devops': 0.8},
            '生物工程': {'programming': 0.9, 'ai_ml': 1.1, 'database': 0.9, 'backend': 0.8, 'frontend': 0.7, 'devops': 0.7},
            '环境工程': {'programming': 0.8, 'ai_ml': 1.0, 'database': 0.9, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.7},
            '材料科学与工程': {'programming': 0.8, 'ai_ml': 1.0, 'database': 0.9, 'backend': 0.7, 'frontend': 0.7, 'devops': 0.7},
        }
        
        cleaned_student_skills = {}
        student_proficiency = {}
        for skill in student_skills:
            clean_name, prof = self.clean_skill_name(skill)
            cleaned_student_skills[clean_name] = skill
            student_proficiency[clean_name] = prof
        
        cleaned_job_skills = {}
        for skill in job_skills:
            clean_name, _ = self.clean_skill_name(skill)
            cleaned_job_skills[clean_name] = skill
        
        matched = []
        match_details = []
        total_weight = 0.0
        matched_weight = 0.0
        
        for job_skill_clean, job_skill_orig in cleaned_job_skills.items():
            # 计算技能权重
            skill_category = self.get_skill_category(job_skill_clean)
            base_weight = 1.0
            
            # 基于岗位类型调整权重
            if job_type in job_type_weights:
                type_weights = job_type_weights[job_type]
                if skill_category in type_weights:
                    base_weight *= type_weights[skill_category]
            
            # 基于学生专业调整权重
            if student_major:
                for major, weights in major_skill_weights.items():
                    if major in student_major:
                        if skill_category in weights:
                            base_weight *= weights[skill_category]
                        break
            
            total_weight += base_weight
            best_match = None
            best_score = 0.0
            match_type = 'none'
            
            for stu_skill_clean, stu_skill_orig in cleaned_student_skills.items():
                score, mtype = self._compute_match_score(
                    stu_skill_clean, job_skill_clean
                )
                if score > best_score:
                    best_score = score
                    best_match = stu_skill_orig
                    match_type = mtype
            
            if best_match and best_score >= 0.6:
                proficiency = student_proficiency.get(
                    self.clean_skill_name(best_match)[0], 'default'
                )
                prof_weight = self.PROFICIENCY_WEIGHTS.get(proficiency, 0.5)
                final_score = best_score * prof_weight * base_weight
                
                matched.append(job_skill_orig)
                matched_weight += final_score
                match_details.append({
                    'job_skill': job_skill_orig,
                    'student_skill': best_match,
                    'match_type': match_type,
                    'match_score': best_score,
                    'proficiency': proficiency,
                    'final_score': final_score,
                    'skill_category': skill_category,
                    'weight': base_weight,
                })
        
        if job_graph:
            semantic_matches = self._semantic_expand(
                list(cleaned_student_skills.keys()),
                list(cleaned_job_skills.keys()),
                job_graph,
            )
            for sem_match in semantic_matches:
                if sem_match['job_skill'] not in matched:
                    matched.append(sem_match['job_skill'])
                    matched_weight += 0.7
                    sem_skill_category = self.get_skill_category(self.clean_skill_name(sem_match['job_skill'])[0])
                    match_details.append({
                        'job_skill': sem_match['job_skill'],
                        'student_skill': sem_match['student_skill'],
                        'match_type': 'semantic',
                        'match_score': sem_match['similarity'],
                        'proficiency': 'default',
                        'final_score': 0.7 * sem_match['similarity'],
                        'skill_category': sem_skill_category,
                    })
        
        gap_skills = [s for s in job_skills if self.clean_skill_name(s)[0] not in 
                      [self.clean_skill_name(m)[0] for m in matched]]
        
        if total_weight > 0:
            score = min((matched_weight / total_weight) * 100, 100)
        else:
            score = 100.0
        
        confidence = min(len(matched) / max(len(job_skills), 1), 1.0) if job_skills else 1.0
        
        # 考虑专业相关性对置信度的影响
        if student_major:
            job_skill_categories = [self.get_skill_category(self.clean_skill_name(js)[0]) for js in job_skills]
            relevant_categories = set()
            for major, weights in major_skill_weights.items():
                if major in student_major:
                    relevant_categories.update([cat for cat, weight in weights.items() if weight >= 1.0])
                    break
            if relevant_categories:
                relevant_skills = [cat for cat in job_skill_categories if cat in relevant_categories]
                if relevant_skills:
                    relevant_match_rate = len([m for m in match_details if m['skill_category'] in relevant_categories]) / len(relevant_skills)
                    confidence = confidence * 0.7 + relevant_match_rate * 0.3
        
        # O2-c: 技能组合效应 — 学生同时掌握高价值组合时加权
        if score > 0 and student_skills:
            student_lower = {self.clean_skill_name(s)[0] for s in student_skills}
            for combo_name, (combo_skills, multiplier) in SKILL_COMBOS.items():
                if all(c in student_lower for c in combo_skills):
                    score = min(score * multiplier, 100.0)
                    logger.debug("O2-c 技能组合加权 [%s] ×%.2f → score=%.1f", combo_name, multiplier, score)
                    break  # 只取最高匹配的一个组合

        elapsed = (time.time() - start_time) * 1000
        logger.debug(f"Skill matching completed in {elapsed:.2f}ms")

        return SkillMatchResult(
            matched_skills=matched,
            gap_skills=gap_skills,
            score=round(score, 2),
            confidence=round(confidence, 3),
            match_details=match_details,
        )
    
    def _compute_match_score(self, skill_a: str, skill_b: str) -> Tuple[float, str]:
        """
        计算两个技能的匹配分数
        
        Returns:
            (score, match_type)
        """
        a, b = skill_a.lower().strip(), skill_b.lower().strip()
        
        if a == b:
            return 1.0, 'exact'
        
        if a in self._synonym_cache and b in self._synonym_cache.get(a, set()):
            return 0.95, 'synonym'
        if b in self._synonym_cache and a in self._synonym_cache.get(b, set()):
            return 0.95, 'synonym'
        
        if a in b or b in a:
            if (a, b) not in _SUBSTRING_EXCLUSIONS:
                return 0.85, 'contains'
        
        import re
        a_words = set(re.findall(r'\w+', a))
        b_words = set(re.findall(r'\w+', b))
        if a_words and b_words:
            overlap = a_words & b_words
            if overlap:
                jaccard = len(overlap) / len(a_words | b_words)
                return 0.7 + jaccard * 0.2, 'partial'
        
        cat_a = self._category_cache.get(a)
        cat_b = self._category_cache.get(b)
        if cat_a and cat_b and cat_a == cat_b:
            # 两个都是具体技术（如 Python vs Java），不允许跨匹配
            if a not in _CATEGORY_SPECIFIC_TECHS or b not in _CATEGORY_SPECIFIC_TECHS:
                return 0.75, 'category'

        for category, skills in self.SKILL_CATEGORY_MAP.items():
            skills_lower = [s.lower() for s in skills]
            if a in skills_lower and b in skills_lower:
                # 同上：两个具体技术不允许通过类别互相匹配
                if a not in _CATEGORY_SPECIFIC_TECHS or b not in _CATEGORY_SPECIFIC_TECHS:
                    return 0.75, 'category'
        
        return 0.0, 'none'
    
    def _semantic_expand(
        self,
        student_skills: List[str],
        job_skills: List[str],
        job_graph,
    ) -> List[Dict]:
        """语义扩展匹配"""
        semantic_matches = []
        
        try:
            # 1. 基于图谱的语义扩展
            expanded = job_graph.expand_skills_semantic(student_skills)
            for item in expanded:
                if item.get('expanded_skills'):
                    for exp in item['expanded_skills']:
                        exp_clean = self.clean_skill_name(exp['skill'])[0]
                        if exp_clean in [self.clean_skill_name(js)[0] for js in job_skills]:
                            semantic_matches.append({
                                'student_skill': item['student_skill'],
                                'job_skill': exp['skill'],
                                'similarity': exp.get('similarity', 0.8),
                            })
            
            # 2. 基于技能类别的关联匹配
            for student_skill in student_skills:
                stu_cat = self.get_skill_category(student_skill)
                if stu_cat != 'other':
                    for job_skill in job_skills:
                        job_skill_clean = self.clean_skill_name(job_skill)[0]
                        job_cat = self.get_skill_category(job_skill_clean)
                        if job_cat == stu_cat:
                            # 检查是否已经匹配
                            already_matched = False
                            for match in semantic_matches:
                                if match['job_skill'] == job_skill:
                                    already_matched = True
                                    break
                            if not already_matched:
                                semantic_matches.append({
                                    'student_skill': student_skill,
                                    'job_skill': job_skill,
                                    'similarity': 0.75,
                                })
        except Exception as e:
            logger.debug(f"Semantic expansion failed: {e}")
        
        return semantic_matches


optimized_matcher = OptimizedSkillMatcher()
