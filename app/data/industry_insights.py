# -*- coding: utf-8 -*-
"""
行业洞察数据库 — 覆盖 23 个 CS/IT 岗位对应的 8 个行业
供 report_service._chapter_4_industry_insight() 使用
"""

# 岗位名称 → 行业 的映射
JOB_INDUSTRY_MAP = {
    # 后端/服务端
    "Java后端工程师": "互联网/软件",
    "后端工程师": "互联网/软件",
    "Python后端工程师": "互联网/软件",
    "Go后端工程师": "互联网/软件",
    "Node.js后端工程师": "互联网/软件",
    "服务端开发工程师": "互联网/软件",
    # 前端
    "前端工程师": "互联网/软件",
    "Web前端工程师": "互联网/软件",
    "全栈工程师": "互联网/软件",
    # 移动端
    "Android开发工程师": "互联网/软件",
    "iOS开发工程师": "互联网/软件",
    "移动端开发工程师": "互联网/软件",
    # 数据/AI
    "数据分析师": "大数据/AI",
    "大数据工程师": "大数据/AI",
    "算法工程师": "大数据/AI",
    "机器学习工程师": "大数据/AI",
    "深度学习工程师": "大数据/AI",
    "NLP工程师": "大数据/AI",
    "计算机视觉工程师": "大数据/AI",
    # 运维/云
    "DevOps工程师": "云计算/运维",
    "运维工程师": "云计算/运维",
    "云计算工程师": "云计算/运维",
    "SRE": "云计算/运维",
    # 安全
    "网络安全工程师": "网络安全",
    "信息安全工程师": "网络安全",
    # 测试
    "测试工程师": "互联网/软件",
    "自动化测试工程师": "互联网/软件",
    "性能测试工程师": "互联网/软件",
    # 产品/设计
    "产品经理": "互联网/软件",
    "UI设计师": "互联网/软件",
    "UX设计师": "互联网/软件",
    # 嵌入式/硬件
    "嵌入式工程师": "智能制造/IoT",
    "嵌入式软件工程师": "智能制造/IoT",
    "固件工程师": "智能制造/IoT",
    # 数据库
    "DBA": "互联网/软件",
    "数据库管理员": "互联网/软件",
}

# 行业深度洞察数据
INDUSTRY_INSIGHTS = {
    "互联网/软件": {
        "trend": "持续增长",
        "growth_rate": "+12%",
        "drivers": ["数字化转型加速", "云原生架构普及", "AI工程化落地", "新能源/智能汽车软件化"],
        "challenges": ["技术迭代快（平均18个月一次范式转变）", "降本增效压力", "头部企业竞争激烈"],
        "future": "全栈能力 + AI工具链使用成为标配，Rust/Go等高性能语言需求上升，微服务向 Service Mesh 演进",
        "hot_skills": ["Kubernetes", "微服务", "Rust/Go", "LLM集成", "云原生"],
        "salary_range": "15-50K（应届15-25K，P6+40K以上）",
        "hiring_seasons": "金三银四 / 金九银十",
        "interview_focus": "系统设计 + 算法 + 项目深挖",
        "competitive_ratio": "应届岗位平均50:1",
        "top_cities": ["北京", "上海", "深圳", "杭州", "成都"],
    },
    "大数据/AI": {
        "trend": "爆发增长",
        "growth_rate": "+35%",
        "drivers": ["大模型商业化", "企业数据中台建设", "AI agent应用爆发", "多模态技术成熟"],
        "challenges": ["门槛高（硕士/博士优先）", "理论与工程要求均高", "大模型替代部分中低端岗位"],
        "future": "RAG工程师、AI应用开发、多模态算法等新型岗位快速增长；传统数据分析向 AI 增强转型",
        "hot_skills": ["LLM微调/RAG", "PyTorch", "Transformer", "特征工程", "向量数据库"],
        "salary_range": "20-80K（算法工程师校招25-40K，资深50-80K）",
        "hiring_seasons": "全年招聘，秋招竞争最激烈",
        "interview_focus": "算法推导 + 工程实现 + 论文阅读 + 项目成果",
        "competitive_ratio": "热门岗位校招100:1以上",
        "top_cities": ["北京", "上海", "杭州", "深圳", "西安"],
    },
    "云计算/运维": {
        "trend": "稳定增长",
        "growth_rate": "+18%",
        "drivers": ["多云/混合云架构普及", "FinOps成本优化需求", "平台工程化", "SRE理念推广"],
        "challenges": ["7×24小时值班压力", "工具链复杂", "与开发团队协作边界模糊"],
        "future": "平台工程师（Platform Engineer）成为主流，IaC（基础设施即代码）能力必备",
        "hot_skills": ["Kubernetes", "Terraform", "Prometheus/Grafana", "CI/CD", "Service Mesh"],
        "salary_range": "15-45K（高级SRE/平台工程师30-45K）",
        "hiring_seasons": "全年均有需求",
        "interview_focus": "Linux原理 + 网络协议 + 故障排查 + 自动化脚本",
        "competitive_ratio": "中等，专业人才相对稀缺",
        "top_cities": ["北京", "上海", "深圳", "杭州", "南京"],
    },
    "网络安全": {
        "trend": "快速增长",
        "growth_rate": "+25%",
        "drivers": ["等保2.0强制执行", "数据安全法落地", "勒索病毒/APT攻击上升", "车联网/工控安全需求"],
        "challenges": ["证书要求高（CISSP/CISP/CEH）", "攻防经验积累周期长", "需持续关注CVE漏洞"],
        "future": "AI安全、云安全、合规方向需求旺盛；红队（渗透测试）人才缺口大",
        "hot_skills": ["渗透测试", "安全开发(SDL)", "零信任架构", "SIEM", "漏洞分析"],
        "salary_range": "18-60K（安全研究员40-60K）",
        "hiring_seasons": "全年稳定，金融/政府行业集中在下半年",
        "interview_focus": "CTF竞赛经历 + 漏洞挖掘案例 + 安全工具使用",
        "competitive_ratio": "低（人才缺口显著）",
        "top_cities": ["北京", "上海", "深圳", "杭州", "成都"],
    },
    "智能制造/IoT": {
        "trend": "高速增长",
        "growth_rate": "+30%",
        "drivers": ["新能源汽车软件化", "工业互联网政策推动", "5G+IoT融合", "机器人/无人化工厂"],
        "challenges": ["软硬件协同复杂", "实时性要求严格", "行业专业知识壁垒"],
        "future": "汽车电子（AUTOSAR/功能安全）、工业AI、边缘计算成为热点；C/C++依然是核心",
        "hot_skills": ["RTOS（FreeRTOS/RT-Thread）", "CAN/LIN协议", "Linux驱动开发", "ROS2", "功能安全ISO 26262"],
        "salary_range": "15-40K（新能源车企溢价30-50%）",
        "hiring_seasons": "全年均有需求，新能源车企秋季大规模招聘",
        "interview_focus": "底层原理 + 协议调试 + 代码质量 + 硬件理解",
        "competitive_ratio": "中低，专业人才相对稀缺",
        "top_cities": ["深圳", "上海", "北京", "武汉", "合肥"],
    },
    "金融科技": {
        "trend": "稳健增长",
        "growth_rate": "+15%",
        "drivers": ["数字人民币推广", "量化交易技术化", "风控AI化", "开放银行API化"],
        "challenges": ["监管合规要求严格", "数据安全要求高", "稳定性要求极高（金融级）"],
        "future": "量化工程师、金融数据科学家、合规科技（RegTech）专家需求持续上升",
        "hot_skills": ["Python量化框架", "风控模型", "分布式交易系统", "Kafka/高性能MQ", "数据库优化"],
        "salary_range": "20-80K（量化岗位溢价显著，年薪百万不罕见）",
        "hiring_seasons": "全年均有，春季校园招聘为主",
        "interview_focus": "算法 + 系统设计 + 金融知识 + 高并发场景",
        "competitive_ratio": "高，顶级金融机构竞争激烈",
        "top_cities": ["上海", "北京", "深圳", "杭州", "成都"],
    },
    "医疗健康IT": {
        "trend": "快速增长",
        "growth_rate": "+20%",
        "drivers": ["电子健康档案(EHR)推广", "AI辅助诊断成熟", "互联网医院政策落地", "基因组学数据分析"],
        "challenges": ["HL7/FHIR等医疗标准学习曲线", "数据隐私（HIPAA/GDPR类）要求", "行业认知壁垒"],
        "future": "医疗AI（影像识别/病历NLP）和医疗数据平台是下一个风口",
        "hot_skills": ["Python医疗数据分析", "DICOM/HL7协议", "深度学习医学影像", "微服务医疗系统"],
        "salary_range": "15-45K",
        "hiring_seasons": "全年均有，互联网医疗公司秋季集中",
        "interview_focus": "技术栈 + 医疗领域理解 + 数据安全意识",
        "competitive_ratio": "中低，复合型人才稀缺",
        "top_cities": ["北京", "上海", "杭州", "成都", "广州"],
    },
    "教育科技": {
        "trend": "分化发展",
        "growth_rate": "+5%（在线内容持平，AI教育+25%）",
        "drivers": ["AI个性化学习", "职业技能培训需求", "企业数字化学习平台", "出海教育市场"],
        "challenges": ["双减政策影响K12", "用户付费意愿降低", "内容同质化严重"],
        "future": "AI教育助手（智能批改/个性化推题）、职业技能认证平台是增长点",
        "hot_skills": ["推荐算法", "知识图谱", "自适应学习系统", "直播/RTC技术"],
        "salary_range": "12-35K",
        "hiring_seasons": "全年均有，受业务周期波动大",
        "interview_focus": "产品思维 + 技术实现 + 教育理解",
        "competitive_ratio": "中高",
        "top_cities": ["北京", "上海", "深圳", "杭州"],
    },
}

# 岗位发展路径（覆盖23个主要IT岗位，按工作年限分级）
JOB_CAREER_PATHS = {
    "Java后端工程师": [
        {"level": "初级Java工程师", "years": "0-2年", "salary": "12-20K", "skills": ["Java基础", "Spring Boot", "MySQL", "Git"]},
        {"level": "中级Java工程师", "years": "2-5年", "salary": "20-35K", "skills": ["微服务", "Redis", "MQ", "性能优化"]},
        {"level": "高级Java工程师", "years": "5-8年", "salary": "35-55K", "skills": ["分布式系统", "架构设计", "技术选型"]},
        {"level": "Java架构师/技术专家", "years": "8年+", "salary": "55K+", "skills": ["系统架构", "技术规划", "团队管理"]},
    ],
    "前端工程师": [
        {"level": "初级前端工程师", "years": "0-2年", "salary": "10-18K", "skills": ["HTML/CSS", "JavaScript", "Vue/React基础"]},
        {"level": "中级前端工程师", "years": "2-5年", "salary": "18-30K", "skills": ["框架深度", "工程化", "性能优化", "TypeScript"]},
        {"level": "高级前端工程师", "years": "5-8年", "salary": "30-45K", "skills": ["架构设计", "跨端开发", "微前端"]},
        {"level": "前端架构师", "years": "8年+", "salary": "45K+", "skills": ["前端架构", "技术规划", "团队管理"]},
    ],
    "算法工程师": [
        {"level": "算法工程师", "years": "0-2年", "salary": "20-35K", "skills": ["ML基础", "Python", "特征工程", "模型调优"]},
        {"level": "高级算法工程师", "years": "2-5年", "salary": "35-55K", "skills": ["深度学习", "大模型微调", "端到端系统"]},
        {"level": "资深算法工程师", "years": "5-8年", "salary": "55-80K", "skills": ["算法创新", "论文发表", "跨部门协作"]},
        {"level": "算法专家/科学家", "years": "8年+", "salary": "80K+", "skills": ["前沿研究", "技术规划", "团队领导"]},
    ],
    "数据分析师": [
        {"level": "数据分析师", "years": "0-2年", "salary": "10-18K", "skills": ["SQL", "Excel", "Python基础", "数据可视化"]},
        {"level": "高级数据分析师", "years": "2-5年", "salary": "18-30K", "skills": ["统计建模", "A/B测试", "BI工具", "业务理解"]},
        {"level": "数据科学家", "years": "5-8年", "salary": "30-50K", "skills": ["机器学习建模", "因果推断", "策略制定"]},
        {"level": "数据总监/首席数据官", "years": "8年+", "salary": "50K+", "skills": ["数据战略", "团队建设", "业务决策"]},
    ],
    "DevOps工程师": [
        {"level": "初级运维/DevOps", "years": "0-2年", "salary": "10-18K", "skills": ["Linux", "Shell", "Docker基础", "CI/CD基础"]},
        {"level": "中级DevOps工程师", "years": "2-5年", "salary": "18-30K", "skills": ["Kubernetes", "Terraform", "监控体系", "自动化"]},
        {"level": "高级DevOps/SRE", "years": "5-8年", "salary": "30-45K", "skills": ["平台工程", "混沌工程", "FinOps"]},
        {"level": "基础设施架构师", "years": "8年+", "salary": "45K+", "skills": ["技术规划", "架构治理", "团队管理"]},
    ],
    "产品经理": [
        {"level": "助理产品经理/初级PM", "years": "0-2年", "salary": "10-18K", "skills": ["需求分析", "原型设计", "Axure/Figma"]},
        {"level": "产品经理", "years": "2-5年", "salary": "18-30K", "skills": ["产品规划", "数据分析", "跨团队协作"]},
        {"level": "高级产品经理/产品专家", "years": "5-8年", "salary": "30-50K", "skills": ["产品战略", "商业化", "团队管理"]},
        {"level": "产品总监/VP of Product", "years": "8年+", "salary": "50K+", "skills": ["商业战略", "组织管理", "行业影响力"]},
    ],
}

def get_industry_for_job(job_title: str) -> str:
    """根据岗位名称查找所属行业"""
    # 精确匹配
    if job_title in JOB_INDUSTRY_MAP:
        return JOB_INDUSTRY_MAP[job_title]
    # 模糊匹配
    for job_key, industry in JOB_INDUSTRY_MAP.items():
        if any(kw in job_title for kw in job_key.split()):
            return industry
    # 关键词推断
    if any(k in job_title for k in ["Java", "Python", "Go", "后端", "服务端", "Node"]):
        return "互联网/软件"
    if any(k in job_title for k in ["前端", "Web", "H5", "全栈"]):
        return "互联网/软件"
    if any(k in job_title for k in ["算法", "AI", "机器学习", "深度学习", "NLP", "CV", "数据科学"]):
        return "大数据/AI"
    if any(k in job_title for k in ["数据", "分析", "BI", "大数据"]):
        return "大数据/AI"
    if any(k in job_title for k in ["运维", "DevOps", "SRE", "云计算", "容器", "K8s"]):
        return "云计算/运维"
    if any(k in job_title for k in ["安全", "渗透", "漏洞", "红队", "蓝队"]):
        return "网络安全"
    if any(k in job_title for k in ["嵌入式", "固件", "IoT", "单片机", "RTOS"]):
        return "智能制造/IoT"
    if any(k in job_title for k in ["金融", "量化", "风控", "银行", "保险", "证券"]):
        return "金融科技"
    if any(k in job_title for k in ["医疗", "医院", "健康", "药", "基因"]):
        return "医疗健康IT"
    if any(k in job_title for k in ["教育", "学习", "培训", "在线课"]):
        return "教育科技"
    return "互联网/软件"  # 默认

def get_career_path_for_job(job_title: str) -> list:
    """获取岗位发展路径"""
    # 精确匹配
    if job_title in JOB_CAREER_PATHS:
        return JOB_CAREER_PATHS[job_title]
    # 关键词匹配
    for path_key, paths in JOB_CAREER_PATHS.items():
        if any(kw in job_title for kw in path_key.split()):
            return paths
    return []
