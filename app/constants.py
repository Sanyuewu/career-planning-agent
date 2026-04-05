# -*- coding: utf-8 -*-
"""
全局常量管理 - 所有业务常量集中于此，各模块从此处导入
避免 hardcode 散落在各业务文件中
"""

# ---------- 学历相关 ----------

# 用于人岗匹配：学历 → 匹配得分（0-100）
DEGREE_MAP = {
    "专科": 40, "本科": 60, "硕士": 80, "博士": 100,
    "junior": 40, "bachelor": 60, "master": 80, "phd": 100,
}

# 用于竞争力评分：学历 → 基础竞争力分（0-100）
DEGREE_COMPETITIVENESS_MAP = {
    "专科": 40, "本科": 70, "硕士": 88, "博士": 100,
}

# 精英院校关键词（用于竞争力加分）
ELITE_SCHOOL_KEYWORDS = [
    "985", "211", "双一流",
    "清华", "北大", "浙大", "复旦", "交大",
    "同济", "南京大学", "武汉大学", "中山大学",
    "华中科技", "西安交通",
]

# ---------- 人岗匹配权重预设 ----------

WEIGHT_PRESETS = {
    "tech":       {"basic": 0.20, "skills": 0.45, "qualities": 0.20, "potential": 0.15},
    "management": {"basic": 0.20, "skills": 0.30, "qualities": 0.35, "potential": 0.15},
    "research":   {"basic": 0.25, "skills": 0.40, "qualities": 0.20, "potential": 0.15},
    "default":    {"basic": 0.20, "skills": 0.35, "qualities": 0.25, "potential": 0.20},
    "operation":  {"basic": 0.20, "skills": 0.30, "qualities": 0.30, "potential": 0.20},
}

# ---------- 技能学习建议 ----------

SKILL_SUGGESTIONS = {
    "Python":     "建议完成Python官方教程+1个数据分析项目实践，预计2-3周",
    "Java":       "建议学习Java核心技术卷I+完成1个Spring Boot项目，预计4-6周",
    "JavaScript": "建议学习MDN Web教程+完成1个Vue/React项目，预计3-4周",
    "SQL":        "建议学习SQL必知必会+在LeetCode完成20道SQL题，预计2周",
    "Vue":        "建议完成Vue3官方教程+1个Todo项目实践，预计2-3周",
    "React":      "建议完成React官方教程+1个实战项目，预计3-4周",
    "TypeScript": "建议学习TypeScript官方文档+重构1个JS项目，预计2周",
    "Docker":     "建议学习Docker官方教程+部署1个微服务项目，预计1-2周",
    "Git":        "建议完成Git官方教程+参与1个开源项目，预计1周",
    "Linux":      "建议学习Linux命令行+在云服务器实践，预计2周",
    "MySQL":      "建议学习MySQL必知必会+完成1个数据库设计项目，预计2-3周",
    "Redis":      "建议学习Redis官方文档+完成1个缓存实战项目，预计1-2周",
    "Spring":     "建议学习Spring官方教程+完成1个Web应用，预计3-4周",
    "SpringBoot": "建议学习Spring Boot实战+完成1个RESTful API项目，预计2-3周",
    "Go":         "建议学习Go语言圣经+完成1个HTTP服务项目，预计3-4周",
    "C++":        "建议学习C++ Primer+完成1个数据结构项目，预计4-6周",
    "C":          "建议学习C程序设计+完成1个系统编程项目，预计3-4周",
    "Kubernetes": "建议学习Kubernetes官方文档+部署1个微服务集群，预计2-3周",
    "Nginx":      "建议学习Nginx实战+配置1个负载均衡环境，预计1周",
    "算法":       "建议在LeetCode完成200题+学习《算法导论》基础章节，预计8-12周",
    "数据结构":   "建议系统学习数据结构与算法+在LeetCode刷100题，预计6-8周",
    "机器学习":   "建议学习吴恩达机器学习课程+完成1个Kaggle项目，预计6-8周",
    "深度学习":   "建议学习PyTorch官方教程+完成1个图像分类项目，预计4-6周",
}

# ---------- 技能重要性分层 ----------

# 岗位技能列表前 N 比例的技能视为 must_have，其余为 nice_to_have
SKILL_MUST_HAVE_RATIO = 2 / 3

# ---------- 技能组合效应（O2-c） ----------
# 学生同时掌握组合中所有技能时，技能维度得分额外加权
# 格式: {组合名: (技能列表（小写）, 加权系数)}
SKILL_COMBOS = {
    "前端三件套":  (["vue", "react", "typescript"], 1.20),
    "后端标准栈":  (["java", "spring", "mysql"], 1.15),
    "Python后端":  (["python", "fastapi", "mysql"], 1.12),
    "数据工程":    (["python", "sql", "spark"], 1.15),
    "云原生":      (["docker", "kubernetes"], 1.10),
    "全栈组合":    (["vue", "spring", "mysql"], 1.18),
    "算法工程":    (["python", "pytorch", "numpy"], 1.15),
    "测试自动化":  (["python", "selenium", "git"], 1.10),
}

# ---------- 图谱语义匹配阈值 ----------

# pipeline 构建时的 Jaccard 相似度阈值（阈值降低以覆盖更多语义相关技能）
SEMANTIC_SIMILARITY_THRESHOLD = 0.6

# ---------- 行业权重覆盖（动态调整） ----------

INDUSTRY_WEIGHT_OVERRIDES = {
    "互联网/软件": {"skills": 0.40, "basic": 0.20, "qualities": 0.20, "potential": 0.20},
    "算法/AI":    {"skills": 0.45, "basic": 0.25, "qualities": 0.15, "potential": 0.15},
    "金融/银行":  {"skills": 0.25, "basic": 0.20, "qualities": 0.35, "potential": 0.20},
    "咨询/管理":  {"skills": 0.25, "basic": 0.20, "qualities": 0.30, "potential": 0.25},
    "硬件/嵌入式": {"skills": 0.45, "basic": 0.30, "qualities": 0.15, "potential": 0.10},
}

# ---------- 真实项目实践与竞赛推荐 ----------

REAL_PROJECT_SUGGESTIONS = {
    "后端开发": [
        "GitHub: spring-petclinic（Spring Boot 入门实践）",
        "LeetCode 热题 100（算法与数据结构）",
        "阿里云天池大数据竞赛",
        "GitHub: mall（电商系统完整实战）",
    ],
    "前端开发": [
        "GitHub: vue3-admin（Vue3 管理后台实战）",
        "GitHub: ant-design-vue-pro（企业级前端实战）",
        "掘金前端技术挑战赛",
        "MDN Web 开发入门教程",
    ],
    "数据分析": [
        "Kaggle Titanic 入门赛（数据分析基础）",
        "天池大数据竞赛（真实业务数据）",
        "DataWhale 开源学习社区",
        "GitHub: pandas-exercises（Pandas 练习集）",
    ],
    "机器学习": [
        "Kaggle 机器学习实战竞赛",
        "天池 AI 算法竞赛",
        "吴恩达 Machine Learning Specialization（Coursera）",
        "GitHub: ml-for-beginners（微软 ML 入门项目）",
    ],
    "深度学习": [
        "Kaggle 图像分类/NLP 竞赛",
        "GitHub: PyTorch-Tutorial（PyTorch 实战教程）",
        "百度飞桨 AI 竞赛平台",
        "CV 方向：GitHub: YOLO 系列目标检测实践",
    ],
    "产品经理": [
        "人人都是产品经理社区竞赛（产品设计大赛）",
        "Axure 原型设计练习项目",
        "GitHub: awesome-product-manager（PM 资源汇总）",
        "腾讯 CDC 用户体验设计竞赛",
    ],
    "运营": [
        "各大平台数据分析运营实战（微信公众号/抖音）",
        "Google Analytics 数据分析认证",
        "DataWhale 运营分析学习计划",
    ],
    "测试": [
        "GitHub: selenium-python-helium（UI 自动化测试）",
        "GitHub: locust（性能测试框架实践）",
        "LeetCode SQL 专项练习（数据库测试）",
    ],
    "DevOps": [
        "GitHub: kubernetes-the-hard-way（K8s 从零搭建）",
        "Docker 官方入门 Play with Docker",
        "GitHub Actions CI/CD 流水线实践",
    ],
    "default": [
        "LeetCode 热题 100（通用算法练习）",
        "GitHub 开源项目贡献（选择感兴趣领域）",
        "Coursera / 中国大学 MOOC 相关课程",
    ],
}

# ---------- 真实实习机会推荐（含平台 + 目标公司 + 申请策略） ----------

REAL_INTERNSHIP_SUGGESTIONS = {
    "后端开发": {
        "platforms": ["实习僧 internshiper.com（搜索 'Java后端实习'/'后端开发实习'）", "Boss直聘（筛选'实习'岗位）", "牛客网 nowcoder.com（校招/实习专区）"],
        "target_companies": ["字节跳动、腾讯、阿里巴巴、美团、滴滴（大厂储备营）", "快手、京东、网易、58同城（中大厂实习）", "各地互联网独角兽企业（成长快、给核返率高）"],
        "tips": "优先投递有'转正机会'标注的岗位；提前准备 LeetCode 中等题 50 道；简历突出项目中的并发/性能优化点",
    },
    "前端开发": {
        "platforms": ["实习僧（搜索'前端开发实习'/'H5开发实习'）", "拉勾网（前端岗位丰富）", "智联招聘（互联网公司前端实习）"],
        "target_companies": ["字节跳动、腾讯、阿里（大厂前端体系完善）", "美团、京东（电商前端）", "各地设计驱动型创业公司"],
        "tips": "准备 1-2 个有完整 GitHub 仓库的项目作品；熟悉 Vue3/React 至少一种；准备跨域/性能优化常见问题",
    },
    "数据分析": {
        "platforms": ["实习僧（搜索'数据分析实习'/'BI实习'）", "Boss直聘（数据岗实习）", "天池数据竞赛社区（竞赛→实习直通）"],
        "target_companies": ["字节跳动数据平台部、腾讯数据分析、阿里数据中台", "快手、美团（用户增长数据岗）", "咨询公司麦肯锡/BCG/Accenture（数据顾问方向）"],
        "tips": "Kaggle/天池有公开竞赛成绩会极大提高面试通过率；熟练 SQL + Python pandas；准备数据驱动决策的项目案例",
    },
    "算法工程师": {
        "platforms": ["实习僧（搜索'算法实习'/'机器学习实习'）", "Boss直聘（AI/算法岗）", "旷视/商汤/百度AI等官网校招页"],
        "target_companies": ["字节跳动AI Lab、腾讯AI Lab、百度飞桨团队", "旷视科技、商汤科技、第四范式（CV/NLP方向）", "各大互联网公司推荐系统/搜索/广告算法组"],
        "tips": "准备 1 篇或以上 arXiv/顶会投稿经历；Kaggle 前 10% 奖牌；熟练 PyTorch/TensorFlow",
    },
    "产品经理": {
        "platforms": ["实习僧（搜索'产品经理实习'/'产品运营实习'）", "拉勾网（互联网产品岗）", "人人都是产品经理社区（产品竞赛和内推）"],
        "target_companies": ["字节、腾讯、阿里产品线（C端产品经验）", "美团、滴滴（出行/本地生活方向）", "B端SaaS公司（ToB产品方向）"],
        "tips": "准备竞品分析报告（3份以上）；熟练 Axure/Figma；用数据量化之前的项目成果",
    },
    "测试工程师": {
        "platforms": ["实习僧（搜索'软件测试实习'/'QA实习'）", "Boss直聘（测试工程师实习）", "牛客网（测试专区）"],
        "target_companies": ["字节跳动、腾讯（自动化测试体系成熟）", "阿里巴巴（质量工程师方向）", "各大银行/金融科技公司（稳定性要求高）"],
        "tips": "熟练 Selenium + Python 或 Java；准备性能测试（JMeter）项目；理解 CI/CD 流水线",
    },
    "运维工程师": {
        "platforms": ["实习僧（搜索'运维实习'/'DevOps实习'）", "Boss直聘（SRE/运维岗）", "云厂商官网实习（阿里云/腾讯云/华为云）"],
        "target_companies": ["阿里云、腾讯云、华为云（云厂商SRE）", "各大互联网公司基础架构部", "字节跳动、美团基础设施团队"],
        "tips": "熟练 Linux + Docker + K8s；获得 AWS/阿里云认证加分；准备容量规划和故障处理案例",
    },
    "default": {
        "platforms": ["实习僧 internshiper.com（全品类实习信息最全）", "Boss直聘（直接与 HR 沟通效率高）", "牛客网（技术岗校招/实习内推）"],
        "target_companies": ["互联网大厂（字节、腾讯、阿里等）暑期/学年实习项目", "外资咨询/金融（麦肯锡、高盛等）寒假/暑假项目", "本地优质创业公司（增长快、给核转正率高）"],
        "tips": "提前 3-4 个月准备简历和面试；主动在 LinkedIn 联系目标公司员工内推；关注各公司校招官网和微信公众号",
    },
}

# ---------- 领域术语词典（注入 LLM system prompt 减少幻觉） ----------

DOMAIN_GLOSSARY = {
    "产品经理": {
        "PRD": "产品需求文档（Product Requirements Document）",
        "DAU": "日活跃用户数（Daily Active Users）",
        "MAU": "月活跃用户数（Monthly Active Users）",
        "A/B测试": "对照实验，通过对比两个版本验证效果",
        "ROI": "投资回报率（Return on Investment）",
        "MVP": "最小可行产品（Minimum Viable Product）",
    },
    "数据分析": {
        "ETL": "数据抽取/转换/加载流程（Extract Transform Load）",
        "OLAP": "联机分析处理（多维数据分析）",
        "数据仓库": "面向分析的集成数据存储系统",
        "漏斗分析": "用户转化路径各环节的逐步流失分析",
    },
    "后端开发": {
        "微服务": "将应用拆分为独立部署的小服务架构",
        "中间件": "连接应用与基础设施的软件层（如消息队列、缓存）",
        "RPC": "远程过程调用（Remote Procedure Call）",
        "熔断": "在服务故障时快速失败避免级联崩溃的机制",
    },
    "算法": {
        "时间复杂度": "算法执行时间随输入规模增长的度量",
        "贪心算法": "每步选择局部最优解的算法策略",
        "动态规划": "通过分解子问题和记忆化避免重复计算的算法",
        "图神经网络": "在图结构数据上进行学习的深度学习模型（GNN）",
    },
}
