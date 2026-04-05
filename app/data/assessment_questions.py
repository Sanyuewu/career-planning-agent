# -*- coding: utf-8 -*-
"""
能力测评题库 — 三套题：逻辑推理 / 职业倾向 / 技术自评
供 POST /api/assessment/submit 使用
"""
from typing import List, Dict, Any

# -------- 逻辑推理题（5题，单选）--------
LOGIC_QUESTIONS: List[Dict[str, Any]] = [
    {
        "q_id": "L1",
        "type": "single",
        "question": "如果 A > B，B > C，C > D，那么以下哪个一定正确？",
        "options": ["A > D", "B > D", "A = D", "C > A"],
        "answer": "A",
        "dimension": "逻辑推理",
        "score": 20,
    },
    {
        "q_id": "L2",
        "type": "single",
        "question": "一段程序运行后，输出序列为 1, 1, 2, 3, 5, 8, 13，下一个数字是？",
        "options": ["18", "21", "24", "20"],
        "answer": "B",
        "dimension": "数学逻辑",
        "score": 20,
    },
    {
        "q_id": "L3",
        "type": "single",
        "question": "某公司有 200 人，60% 会 Python，50% 会 Java，至少同时会两种语言的人数最少为多少？",
        "options": ["10", "20", "30", "40"],
        "answer": "B",
        "dimension": "数学逻辑",
        "score": 20,
    },
    {
        "q_id": "L4",
        "type": "single",
        "question": "以下哪种数据结构最适合实现「撤销操作」功能？",
        "options": ["队列", "栈", "链表", "哈希表"],
        "answer": "B",
        "dimension": "计算机思维",
        "score": 20,
    },
    {
        "q_id": "L5",
        "type": "single",
        "question": "一个二叉树有 n 个叶节点，则非叶节点数为？",
        "options": ["n", "n-1", "n+1", "2n"],
        "answer": "B",
        "dimension": "计算机思维",
        "score": 20,
    },
]

# -------- 职业倾向题（10题，单选，MBTI-like）--------
CAREER_TENDENCY_QUESTIONS: List[Dict[str, Any]] = [
    {
        "q_id": "C1",
        "type": "single",
        "question": "在团队项目中，你更倾向于：",
        "options": [
            "A. 负责整体规划和协调",
            "B. 深入技术实现某个核心模块",
            "C. 与用户/客户沟通需求",
            "D. 负责测试和质量保障",
        ],
        "dimension_map": {"A": "管理/产品", "B": "技术", "C": "运营/销售", "D": "质量/运维"},
    },
    {
        "q_id": "C2",
        "type": "single",
        "question": "当遇到技术难题时，你的第一反应是：",
        "options": [
            "A. 自己深入研究，花时间彻底搞懂",
            "B. 快速搜索解决方案，先解决问题再说",
            "C. 和同事讨论，集思广益",
            "D. 评估影响范围，先找临时方案",
        ],
        "dimension_map": {"A": "钻研型", "B": "务实型", "C": "协作型", "D": "决策型"},
    },
    {
        "q_id": "C3",
        "type": "single",
        "question": "你认为最有价值的工作成果是：",
        "options": [
            "A. 性能提升50%的技术优化",
            "B. 用户满意度提升的产品改版",
            "C. 节省团队效率的工具/流程",
            "D. 发现并修复重大安全漏洞",
        ],
        "dimension_map": {"A": "技术导向", "B": "用户导向", "C": "效率导向", "D": "风险意识"},
    },
    {
        "q_id": "C4",
        "type": "single",
        "question": "你更喜欢哪类工作节奏？",
        "options": [
            "A. 快节奏，不断接新挑战",
            "B. 稳定，能深耕某个领域",
            "C. 灵活，可以尝试各种方向",
            "D. 按计划有序推进",
        ],
        "dimension_map": {"A": "挑战型", "B": "专精型", "C": "探索型", "D": "计划型"},
    },
    {
        "q_id": "C5",
        "type": "single",
        "question": "五年后，你最理想的状态是：",
        "options": [
            "A. 成为技术专家/架构师",
            "B. 转向管理/产品方向",
            "C. 创业或做独立开发者",
            "D. 在大厂某业务线深耕",
        ],
        "dimension_map": {"A": "技术路线", "B": "管理路线", "C": "创业路线", "D": "业务路线"},
    },
    {
        "q_id": "C6",
        "type": "single",
        "question": "你通常如何学习新技术？",
        "options": [
            "A. 系统阅读官方文档/书籍",
            "B. 找实际项目练手",
            "C. 看视频课程",
            "D. 通过社区/开源贡献学习",
        ],
        "dimension_map": {"A": "系统型", "B": "实践型", "C": "跟随型", "D": "社区型"},
    },
    {
        "q_id": "C7",
        "type": "single",
        "question": "在代码 Review 时，你最在意：",
        "options": [
            "A. 性能和算法效率",
            "B. 代码可读性和规范",
            "C. 功能是否满足需求",
            "D. 安全性和边界处理",
        ],
        "dimension_map": {"A": "性能意识", "B": "工程素养", "C": "产品思维", "D": "安全意识"},
    },
    {
        "q_id": "C8",
        "type": "single",
        "question": "收到用户反馈「功能有问题」时，你的第一步是：",
        "options": [
            "A. 查日志找根因",
            "B. 复现问题",
            "C. 评估影响范围",
            "D. 向用户确认具体场景",
        ],
        "dimension_map": {"A": "分析型", "B": "实证型", "C": "全局型", "D": "沟通型"},
    },
    {
        "q_id": "C9",
        "type": "single",
        "question": "你对开源贡献的态度是：",
        "options": [
            "A. 积极参与，是技术影响力的体现",
            "B. 有兴趣但工作太忙",
            "C. 不感兴趣，专注做好本职工作",
            "D. 有计划，等自己技术更成熟再参与",
        ],
        "dimension_map": {"A": "技术热情高", "B": "务实型", "C": "专注型", "D": "成长型"},
    },
    {
        "q_id": "C10",
        "type": "single",
        "question": "你认为衡量一个工程师价值的最重要指标是：",
        "options": [
            "A. 解决了多少技术难题",
            "B. 给团队/公司带来了多少业务价值",
            "C. 是否在技术社区有影响力",
            "D. 代码质量和工程规范",
        ],
        "dimension_map": {"A": "技术深度", "B": "商业价值", "C": "行业影响", "D": "工程素养"},
    },
]

# -------- 技术自评题（8题，按岗位分组，1-5分评分）--------
TECH_ASSESSMENT_BY_JOB: Dict[str, List[Dict[str, Any]]] = {
    "后端开发": [
        {"q_id": "T_BE_1", "question": "熟悉至少一种后端语言（Java/Python/Go/Node.js）并有实际项目经验", "dimension": "编程语言"},
        {"q_id": "T_BE_2", "question": "理解 HTTP/HTTPS 协议、RESTful API 设计", "dimension": "网络基础"},
        {"q_id": "T_BE_3", "question": "掌握关系型数据库（MySQL/PostgreSQL）的 CRUD + 索引优化", "dimension": "数据库"},
        {"q_id": "T_BE_4", "question": "了解缓存（Redis）的使用场景和常见数据结构", "dimension": "中间件"},
        {"q_id": "T_BE_5", "question": "熟悉 Spring Boot / Django / FastAPI 等主流框架", "dimension": "框架"},
        {"q_id": "T_BE_6", "question": "能独立进行 Git 版本管理和代码 Review", "dimension": "工程能力"},
        {"q_id": "T_BE_7", "question": "理解并发和线程安全的基本概念", "dimension": "系统知识"},
        {"q_id": "T_BE_8", "question": "有微服务或分布式系统的开发经验", "dimension": "架构能力"},
    ],
    "前端开发": [
        {"q_id": "T_FE_1", "question": "熟练使用 HTML5 / CSS3，能实现常见布局（Flex/Grid）", "dimension": "基础"},
        {"q_id": "T_FE_2", "question": "熟练使用 JavaScript/TypeScript，理解事件循环和异步", "dimension": "JS核心"},
        {"q_id": "T_FE_3", "question": "掌握 Vue3 或 React 主流框架的组件开发", "dimension": "框架"},
        {"q_id": "T_FE_4", "question": "能使用 Vite/Webpack 构建和配置前端工程", "dimension": "工程化"},
        {"q_id": "T_FE_5", "question": "了解浏览器渲染原理和性能优化方法", "dimension": "性能"},
        {"q_id": "T_FE_6", "question": "能独立开发响应式/移动端适配的页面", "dimension": "适配"},
        {"q_id": "T_FE_7", "question": "能与后端联调接口，处理 token/权限等场景", "dimension": "前后端协作"},
        {"q_id": "T_FE_8", "question": "了解微前端或 SSR/SSG 相关技术", "dimension": "进阶"},
    ],
    "数据分析": [
        {"q_id": "T_DA_1", "question": "熟练编写复杂 SQL（多表关联、窗口函数）", "dimension": "SQL"},
        {"q_id": "T_DA_2", "question": "能用 Python（pandas/numpy）进行数据清洗和分析", "dimension": "Python"},
        {"q_id": "T_DA_3", "question": "熟练使用 Excel/Google Sheets 进行数据透视和可视化", "dimension": "Excel"},
        {"q_id": "T_DA_4", "question": "掌握至少一种 BI 工具（Tableau/PowerBI/FineBI）", "dimension": "可视化"},
        {"q_id": "T_DA_5", "question": "理解 A/B 测试原理和显著性检验", "dimension": "统计"},
        {"q_id": "T_DA_6", "question": "能撰写数据分析报告并向非技术人员讲解结论", "dimension": "表达"},
        {"q_id": "T_DA_7", "question": "了解用户行为分析（留存/漏斗/LTV）等指标体系", "dimension": "业务理解"},
        {"q_id": "T_DA_8", "question": "有机器学习建模经验（分类/回归/聚类）", "dimension": "建模"},
    ],
    "算法/AI": [
        {"q_id": "T_AI_1", "question": "掌握常用机器学习算法（线性回归/决策树/SVM/集成方法）", "dimension": "ML基础"},
        {"q_id": "T_AI_2", "question": "熟练使用 PyTorch 或 TensorFlow 构建和训练神经网络", "dimension": "深度学习"},
        {"q_id": "T_AI_3", "question": "了解 Transformer 架构和大语言模型的基本原理", "dimension": "LLM"},
        {"q_id": "T_AI_4", "question": "能独立完成特征工程和模型调优（超参数搜索）", "dimension": "工程能力"},
        {"q_id": "T_AI_5", "question": "理解模型评估指标（AUC/F1/BLEU等）及其适用场景", "dimension": "评估"},
        {"q_id": "T_AI_6", "question": "有完整的 ML 项目经验（数据采集→训练→部署）", "dimension": "项目经验"},
        {"q_id": "T_AI_7", "question": "能阅读英文技术论文并复现核心算法", "dimension": "研究能力"},
        {"q_id": "T_AI_8", "question": "了解模型量化/蒸馏/推理加速等工程优化方法", "dimension": "部署优化"},
    ],
    "DevOps": [
        {"q_id": "T_DO_1", "question": "熟悉 Linux 系统管理和 Shell 脚本编写", "dimension": "Linux"},
        {"q_id": "T_DO_2", "question": "熟练使用 Docker 构建和管理容器", "dimension": "容器"},
        {"q_id": "T_DO_3", "question": "掌握 Kubernetes 核心概念（Pod/Service/Ingress/Deployment）", "dimension": "K8s"},
        {"q_id": "T_DO_4", "question": "能搭建 CI/CD 流水线（Jenkins/GitLab CI/GitHub Actions）", "dimension": "CI/CD"},
        {"q_id": "T_DO_5", "question": "熟悉监控告警体系（Prometheus + Grafana）", "dimension": "监控"},
        {"q_id": "T_DO_6", "question": "了解 IaC 工具（Terraform/Ansible）", "dimension": "自动化"},
        {"q_id": "T_DO_7", "question": "有云平台（AWS/阿里云/腾讯云）使用经验", "dimension": "云平台"},
        {"q_id": "T_DO_8", "question": "能处理生产环境故障排查和性能分析", "dimension": "运维能力"},
    ],
}

# 默认通用技术自评（无匹配岗位时使用）
DEFAULT_TECH_QUESTIONS = TECH_ASSESSMENT_BY_JOB["后端开发"]


def get_questions_for_job(job_hint: str) -> List[Dict[str, Any]]:
    """根据岗位意向返回对应技术自评题"""
    if not job_hint:
        return DEFAULT_TECH_QUESTIONS
    jl = job_hint.lower()
    if any(k in jl for k in ["前端", "frontend", "web", "vue", "react"]):
        return TECH_ASSESSMENT_BY_JOB["前端开发"]
    if any(k in jl for k in ["数据分析", "data analyst", "bi", "分析"]):
        return TECH_ASSESSMENT_BY_JOB["数据分析"]
    if any(k in jl for k in ["算法", "ai", "machine", "deep", "nlp", "cv", "机器学习"]):
        return TECH_ASSESSMENT_BY_JOB["算法/AI"]
    if any(k in jl for k in ["devops", "运维", "sre", "k8s", "容器"]):
        return TECH_ASSESSMENT_BY_JOB["DevOps"]
    return TECH_ASSESSMENT_BY_JOB["后端开发"]  # default


def calculate_assessment_score(answers: List[Dict], job_hint: str = "") -> Dict:
    """
    计算测评得分
    answers: [{q_id, answer}] 其中 answer 对于技术题为 1-5，对于逻辑题为 "A"/"B"/"C"/"D"
    Returns: {
        logic_score: 0-100,
        tendency_dimensions: {维度: 频次},
        tech_scores: {维度: 平均分*20},
        ability_profile_update: {7维度: 分数}  # 用于合并到 ability_profile
    }
    """
    answer_map = {a["q_id"]: a["answer"] for a in answers}

    # 逻辑推理得分
    logic_score = 0
    for q in LOGIC_QUESTIONS:
        if answer_map.get(q["q_id"]) == q["answer"]:
            logic_score += q["score"]

    # 职业倾向统计
    tendency_dims: Dict[str, int] = {}
    for q in CAREER_TENDENCY_QUESTIONS:
        ans = answer_map.get(q["q_id"])
        if ans and ans in q.get("dimension_map", {}):
            dim = q["dimension_map"][ans]
            tendency_dims[dim] = tendency_dims.get(dim, 0) + 1

    # 技术自评得分（1-5 → *20 = 0-100）
    tech_qs = get_questions_for_job(job_hint)
    tech_dim_scores: Dict[str, list] = {}
    for q in tech_qs:
        ans = answer_map.get(q["q_id"])
        if ans is not None:
            try:
                score = float(ans) * 20
                dim = q["dimension"]
                tech_dim_scores.setdefault(dim, []).append(score)
            except (ValueError, TypeError):
                pass

    tech_scores = {dim: round(sum(scores) / len(scores), 1) for dim, scores in tech_dim_scores.items()}
    avg_tech = sum(tech_scores.values()) / len(tech_scores) if tech_scores else 50.0

    # 构建 ability_profile 更新量（测评权重 0.4，原始权重 0.6）
    ability_update = {
        "技术能力": round(avg_tech * 0.4, 1),  # 需在调用方与原值合并
        "学习能力": round(logic_score * 0.4, 1),
    }

    return {
        "logic_score": logic_score,
        "tendency_dimensions": tendency_dims,
        "tech_scores": tech_scores,
        "ability_profile_update": ability_update,
        "overall": round((logic_score + avg_tech) / 2, 1),
    }
