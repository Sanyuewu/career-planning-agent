#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
D-3: 技能图谱扩展 - 为缺失IT岗位注入完整节点数据
直接更新 data/job_graph.json，无需重新生成全量图谱
"""

import json
from pathlib import Path

GRAPH_PATH = Path(__file__).parent.parent / "data" / "job_graph.json"

# ── 新IT岗位完整定义 ──────────────────────────────────────────────
IT_JOB_PROFILES = [
    {
        "name": "Python工程师",
        "overview": "负责基于Python的后端服务、数据处理或自动化脚本开发，常见于互联网、金融科技、AI等行业。",
        "industry": "互联网/金融科技",
        "industry_category": "IT/软件",
        "salary": "15-40K",
        "market_heat": 9,
        "skills": ["Python", "Django", "FastAPI", "MySQL", "Redis", "Docker", "Linux", "Git"],
        "required_skills": ["Python", "MySQL", "Git", "Linux"],
        "preferred_skills": ["FastAPI", "Redis", "Docker"],
        "bonus_skills": ["Kafka", "Kubernetes", "机器学习"],
        "certs": ["Python工程师认证", "阿里云ACP"],
        "tags": ["后端开发", "脚本自动化", "数据处理"],
        "promotions": [
            {"job": "初级Python工程师", "years": "0-2年", "desc": "独立完成模块开发与维护"},
            {"job": "中级Python工程师", "years": "2-4年", "desc": "主导子系统设计与性能优化"},
            {"job": "高级Python架构师", "years": "4-7年", "desc": "负责整体技术架构与团队带教"},
            {"job": "技术总监/CTO", "years": "7年+", "desc": "制定技术战略，管理研发团队"},
        ],
        "transfers": [
            {"target": "数据工程师", "match_level": "高", "overlap_pct": 0.75, "advantage": "Python数据处理能力强", "need_learn": "Spark/Hive等大数据框架"},
            {"target": "机器学习工程师", "match_level": "中", "overlap_pct": 0.55, "advantage": "Python基础扎实", "need_learn": "ML算法、PyTorch/TensorFlow"},
            {"target": "运维工程师", "match_level": "中", "overlap_pct": 0.45, "advantage": "脚本自动化能力", "need_learn": "Kubernetes、Ansible、监控体系"},
        ],
    },
    {
        "name": "Java后端工程师",
        "overview": "负责企业级Java后端服务的设计与开发，广泛应用于电商、金融、政务等高并发场景。",
        "industry": "互联网/金融",
        "industry_category": "IT/软件",
        "salary": "15-35K",
        "market_heat": 10,
        "skills": ["Java", "Spring Boot", "MySQL", "Redis", "Kafka", "Docker", "微服务", "Git"],
        "required_skills": ["Java", "Spring Boot", "MySQL", "Git"],
        "preferred_skills": ["Redis", "Kafka", "Docker"],
        "bonus_skills": ["Kubernetes", "ElasticSearch", "RocketMQ"],
        "certs": ["Oracle Java SE认证", "阿里云ACA"],
        "tags": ["后端开发", "高并发", "微服务"],
        "promotions": [
            {"job": "初级Java工程师", "years": "0-2年", "desc": "完成需求开发与bug修复"},
            {"job": "中级Java工程师", "years": "2-4年", "desc": "参与架构设计，主导模块开发"},
            {"job": "高级Java工程师", "years": "4-7年", "desc": "负责系统架构与团队技术指导"},
            {"job": "Java架构师/技术总监", "years": "7年+", "desc": "制定技术规范，主导技术选型"},
        ],
        "transfers": [
            {"target": "大数据工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "Java生态熟悉(Hadoop/Spark均支持Java)", "need_learn": "Hive/Flink大数据生态"},
            {"target": "云原生工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "微服务架构经验", "need_learn": "Kubernetes/Docker深度使用"},
            {"target": "测试工程师", "match_level": "低", "overlap_pct": 0.35, "advantage": "理解代码逻辑", "need_learn": "测试框架、性能测试方法论"},
        ],
    },
    {
        "name": "前端工程师",
        "overview": "负责Web前端页面开发与交互实现，使用Vue/React等框架构建用户界面，与后端协作完成业务功能。",
        "industry": "互联网",
        "industry_category": "IT/软件",
        "salary": "12-30K",
        "market_heat": 8,
        "skills": ["Vue.js", "React", "TypeScript", "JavaScript", "CSS3", "Webpack", "Git"],
        "required_skills": ["JavaScript", "HTML/CSS", "Vue.js", "Git"],
        "preferred_skills": ["TypeScript", "React", "Webpack"],
        "bonus_skills": ["Node.js", "微前端", "性能优化"],
        "certs": ["前端工程师认证", "腾讯前端认证"],
        "tags": ["前端开发", "UI实现", "用户体验"],
        "promotions": [
            {"job": "初级前端工程师", "years": "0-2年", "desc": "独立完成页面开发任务"},
            {"job": "中级前端工程师", "years": "2-4年", "desc": "主导前端架构设计与组件库建设"},
            {"job": "高级前端/前端架构师", "years": "4-7年", "desc": "制定前端规范，推动工程化建设"},
            {"job": "前端技术总监", "years": "7年+", "desc": "管理前端团队，把控技术方向"},
        ],
        "transfers": [
            {"target": "全栈工程师", "match_level": "高", "overlap_pct": 0.7, "advantage": "前端技术栈扎实", "need_learn": "后端框架、数据库、API设计"},
            {"target": "移动端工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "JavaScript/TypeScript基础", "need_learn": "React Native/Flutter或原生开发"},
            {"target": "产品经理", "match_level": "中", "overlap_pct": 0.4, "advantage": "深度理解用户交互与界面逻辑", "need_learn": "产品规划、数据分析、项目管理"},
        ],
    },
    {
        "name": "运维工程师",
        "overview": "负责公司服务器、云平台、CI/CD流水线的运维保障，确保系统高可用与安全稳定运行。",
        "industry": "互联网/云计算",
        "industry_category": "IT/运维",
        "salary": "12-25K",
        "market_heat": 7,
        "skills": ["Linux", "Docker", "Kubernetes", "CI/CD", "Ansible", "Prometheus", "Shell", "Python"],
        "required_skills": ["Linux", "Docker", "Shell脚本", "Git"],
        "preferred_skills": ["Kubernetes", "Ansible", "Prometheus"],
        "bonus_skills": ["Terraform", "ELK Stack", "云厂商认证"],
        "certs": ["CKA（Kubernetes管理员）", "AWS/阿里云认证"],
        "tags": ["系统运维", "DevOps", "云计算"],
        "promotions": [
            {"job": "初级运维工程师", "years": "0-2年", "desc": "负责日常运维巡检与故障处理"},
            {"job": "中级运维工程师", "years": "2-4年", "desc": "主导CI/CD流水线建设与自动化运维"},
            {"job": "高级运维/DevOps工程师", "years": "4-7年", "desc": "负责平台化建设与架构优化"},
            {"job": "运维总监/SRE Lead", "years": "7年+", "desc": "制定运维战略，管理SRE团队"},
        ],
        "transfers": [
            {"target": "云原生工程师", "match_level": "高", "overlap_pct": 0.75, "advantage": "Kubernetes/Docker基础扎实", "need_learn": "Service Mesh、Helm chart开发"},
            {"target": "安全工程师", "match_level": "中", "overlap_pct": 0.45, "advantage": "系统底层理解深", "need_learn": "渗透测试、漏洞分析、安全合规"},
            {"target": "数据工程师", "match_level": "低", "overlap_pct": 0.35, "advantage": "Linux/Shell脚本能力", "need_learn": "Spark/Flink、数仓建模"},
        ],
    },
    {
        "name": "数据工程师",
        "overview": "负责构建和维护企业数据管道与数仓体系，保障数据质量和实时/离线数据流转，支撑业务决策。",
        "industry": "互联网/大数据",
        "industry_category": "IT/数据",
        "salary": "20-45K",
        "market_heat": 8,
        "skills": ["Spark", "Hive", "Flink", "Hadoop", "Python", "SQL", "Kafka", "Airflow"],
        "required_skills": ["SQL", "Python", "Hive", "Spark"],
        "preferred_skills": ["Flink", "Kafka", "Airflow"],
        "bonus_skills": ["ClickHouse", "Delta Lake", "Iceberg"],
        "certs": ["Cloudera数据工程师认证", "阿里云大数据ACP"],
        "tags": ["数据工程", "ETL", "数仓建设"],
        "promotions": [
            {"job": "初级数据工程师", "years": "0-2年", "desc": "开发ETL任务，维护数据管道"},
            {"job": "中级数据工程师", "years": "2-4年", "desc": "主导数仓建模，优化计算性能"},
            {"job": "高级数据工程师/架构师", "years": "4-7年", "desc": "负责数据平台整体架构设计"},
            {"job": "数据总监/首席数据工程师", "years": "7年+", "desc": "制定数据战略，管理数据团队"},
        ],
        "transfers": [
            {"target": "大数据工程师", "match_level": "高", "overlap_pct": 0.8, "advantage": "大数据生态熟悉", "need_learn": "实时计算深度优化"},
            {"target": "数据分析师", "match_level": "中", "overlap_pct": 0.55, "advantage": "SQL/数仓理解深", "need_learn": "BI工具、统计分析、业务理解"},
            {"target": "机器学习工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "数据处理与特征工程能力", "need_learn": "ML模型训练、模型部署"},
        ],
    },
    {
        "name": "安全工程师",
        "overview": "负责企业信息系统的安全防护与渗透测试，识别和修复安全漏洞，保障数据和业务安全。",
        "industry": "互联网/金融/政务",
        "industry_category": "IT/安全",
        "salary": "18-40K",
        "market_heat": 7,
        "skills": ["渗透测试", "Kali Linux", "Python", "网络协议", "漏洞分析", "OWASP", "CTF", "Web安全"],
        "required_skills": ["网络协议", "Linux", "Python", "漏洞分析"],
        "preferred_skills": ["渗透测试", "Kali Linux", "OWASP"],
        "bonus_skills": ["CTF竞赛经验", "CISSP认证", "代码审计"],
        "certs": ["CISP（注册信息安全专业人员）", "CEH（道德黑客）", "OSCP"],
        "tags": ["网络安全", "渗透测试", "漏洞研究"],
        "promotions": [
            {"job": "初级安全工程师", "years": "0-2年", "desc": "执行安全扫描与基础渗透测试"},
            {"job": "中级安全工程师", "years": "2-4年", "desc": "主导红队测试与安全加固方案"},
            {"job": "高级安全工程师/安全架构师", "years": "4-7年", "desc": "设计企业安全体系与应急响应"},
            {"job": "首席安全官CISO", "years": "7年+", "desc": "制定安全战略，负责合规管理"},
        ],
        "transfers": [
            {"target": "运维工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "Linux系统基础扎实", "need_learn": "DevOps工具链、自动化运维"},
            {"target": "数据工程师", "match_level": "低", "overlap_pct": 0.3, "advantage": "Python脚本能力", "need_learn": "大数据技术栈、ETL开发"},
        ],
    },
    {
        "name": "移动端工程师",
        "overview": "负责iOS/Android原生或跨平台移动应用的开发，实现高质量的移动端用户体验。",
        "industry": "互联网/消费品",
        "industry_category": "IT/移动开发",
        "salary": "15-35K",
        "market_heat": 7,
        "skills": ["Android", "iOS", "Flutter", "Swift", "Kotlin", "React Native", "Dart"],
        "required_skills": ["Android或iOS", "Kotlin或Swift"],
        "preferred_skills": ["Flutter", "React Native"],
        "bonus_skills": ["性能优化", "跨平台架构", "音视频开发"],
        "certs": ["Google Android开发者认证", "Apple Developer认证"],
        "tags": ["移动开发", "APP开发", "跨平台"],
        "promotions": [
            {"job": "初级移动端工程师", "years": "0-2年", "desc": "独立开发页面模块，完成功能需求"},
            {"job": "中级移动端工程师", "years": "2-4年", "desc": "主导模块架构设计，推动性能优化"},
            {"job": "高级移动端工程师/架构师", "years": "4-7年", "desc": "负责APP整体架构与跨平台方案"},
            {"job": "移动端技术总监", "years": "7年+", "desc": "制定移动技术规范，管理研发团队"},
        ],
        "transfers": [
            {"target": "前端工程师", "match_level": "中", "overlap_pct": 0.55, "advantage": "JS/TS基础（React Native路线）", "need_learn": "Vue/React Web开发、浏览器API"},
            {"target": "全栈工程师", "match_level": "中", "overlap_pct": 0.45, "advantage": "端侧开发经验", "need_learn": "后端服务、数据库、API设计"},
        ],
    },
    {
        "name": "云原生工程师",
        "overview": "负责基于Kubernetes/Docker的云原生应用构建与运维，推动企业服务容器化与微服务化转型。",
        "industry": "互联网/云计算",
        "industry_category": "IT/云计算",
        "salary": "20-45K",
        "market_heat": 8,
        "skills": ["Kubernetes", "Docker", "Istio", "Helm", "Terraform", "Go", "Prometheus", "ArgoCD"],
        "required_skills": ["Kubernetes", "Docker", "Linux"],
        "preferred_skills": ["Helm", "Istio", "Terraform"],
        "bonus_skills": ["Go语言", "ArgoCD", "多云架构"],
        "certs": ["CKA", "CKS", "阿里云Kubernetes认证"],
        "tags": ["云原生", "容器化", "DevOps"],
        "promotions": [
            {"job": "云原生工程师", "years": "0-3年", "desc": "负责容器化部署与K8s集群维护"},
            {"job": "高级云原生工程师", "years": "3-6年", "desc": "主导Service Mesh与多集群方案设计"},
            {"job": "云原生架构师", "years": "6年+", "desc": "制定云原生技术路线，指导团队实践"},
        ],
        "transfers": [
            {"target": "运维工程师", "match_level": "高", "overlap_pct": 0.75, "advantage": "基础设施自动化能力", "need_learn": "传统运维体系、ITIL规范"},
            {"target": "数据工程师", "match_level": "低", "overlap_pct": 0.35, "advantage": "分布式系统理解", "need_learn": "大数据计算框架、SQL/数仓"},
        ],
    },
    {
        "name": "大数据工程师",
        "overview": "负责PB级别数据的采集、存储、计算与管理，构建离线/实时数仓，支撑业务分析与AI应用。",
        "industry": "互联网/金融/电商",
        "industry_category": "IT/数据",
        "salary": "20-45K",
        "market_heat": 8,
        "skills": ["Hadoop", "Spark", "Hive", "Flink", "Kafka", "HBase", "Python", "Scala"],
        "required_skills": ["Spark", "Hive", "Kafka", "SQL"],
        "preferred_skills": ["Flink", "Scala", "HBase"],
        "bonus_skills": ["ClickHouse", "Presto", "数仓建模"],
        "certs": ["Cloudera CCA/CCP", "阿里云大数据ACP"],
        "tags": ["大数据", "实时计算", "数仓"],
        "promotions": [
            {"job": "初级大数据工程师", "years": "0-2年", "desc": "开发数据ETL任务，维护数据表"},
            {"job": "中级大数据工程师", "years": "2-4年", "desc": "设计数仓分层架构，优化计算任务"},
            {"job": "高级大数据工程师", "years": "4-7年", "desc": "负责实时流计算架构与大规模优化"},
            {"job": "大数据架构师/总监", "years": "7年+", "desc": "制定数据中台战略，管理数据团队"},
        ],
        "transfers": [
            {"target": "数据工程师", "match_level": "高", "overlap_pct": 0.8, "advantage": "大数据生态完全重叠", "need_learn": "数据治理与数仓规范深化"},
            {"target": "机器学习工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "数据处理能力强", "need_learn": "ML算法、特征工程、模型训练"},
            {"target": "算法工程师", "match_level": "低", "overlap_pct": 0.35, "advantage": "Spark MLlib基础", "need_learn": "深度学习框架、研究能力"},
        ],
    },
    {
        "name": "机器学习工程师",
        "overview": "负责机器学习/深度学习模型的研发、训练与部署上线，服务于推荐、搜索、CV、NLP等AI应用场景。",
        "industry": "互联网/AI",
        "industry_category": "IT/人工智能",
        "salary": "25-55K",
        "market_heat": 9,
        "skills": ["Python", "Scikit-learn", "PyTorch", "TensorFlow", "MLflow", "特征工程", "模型部署", "SQL"],
        "required_skills": ["Python", "PyTorch或TensorFlow", "机器学习算法"],
        "preferred_skills": ["MLflow", "模型部署", "分布式训练"],
        "bonus_skills": ["强化学习", "图神经网络", "大模型微调"],
        "certs": ["Google TensorFlow认证", "Kaggle竞赛排名"],
        "tags": ["机器学习", "深度学习", "AI应用"],
        "promotions": [
            {"job": "初级机器学习工程师", "years": "0-2年", "desc": "调参、特征工程、维护模型pipeline"},
            {"job": "中级机器学习工程师", "years": "2-4年", "desc": "主导算法设计，提升模型效果"},
            {"job": "高级ML工程师/算法专家", "years": "4-7年", "desc": "负责算法架构，推进产业落地"},
            {"job": "AI总监/首席科学家", "years": "7年+", "desc": "制定AI战略，管理研发团队"},
        ],
        "transfers": [
            {"target": "算法工程师", "match_level": "高", "overlap_pct": 0.8, "advantage": "技能高度重叠", "need_learn": "更深的数学基础与研究能力"},
            {"target": "数据工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "数据处理与特征工程能力", "need_learn": "大数据计算框架、ETL开发"},
            {"target": "数据分析师", "match_level": "中", "overlap_pct": 0.45, "advantage": "统计分析能力", "need_learn": "BI工具、业务理解、可视化"},
        ],
    },
    {
        "name": "全栈工程师",
        "overview": "同时负责前端和后端开发，能独立完成从页面到服务端的完整功能实现，适合初创/小规模团队。",
        "industry": "互联网",
        "industry_category": "IT/软件",
        "salary": "18-40K",
        "market_heat": 7,
        "skills": ["Vue.js", "React", "Node.js", "Python", "MySQL", "Docker", "REST API", "Git"],
        "required_skills": ["JavaScript/TypeScript", "至少一门后端语言", "MySQL", "Git"],
        "preferred_skills": ["Vue.js或React", "Node.js", "Docker"],
        "bonus_skills": ["GraphQL", "微服务", "Redis"],
        "certs": ["AWS Developer认证", "全栈工程师认证"],
        "tags": ["全栈开发", "前后端", "独立开发"],
        "promotions": [
            {"job": "全栈工程师", "years": "0-3年", "desc": "独立负责小型项目端到端开发"},
            {"job": "高级全栈工程师", "years": "3-6年", "desc": "主导中型项目架构，指导初级工程师"},
            {"job": "技术负责人/CTO", "years": "6年+", "desc": "制定技术路线，管理研发团队"},
        ],
        "transfers": [
            {"target": "前端工程师", "match_level": "高", "overlap_pct": 0.7, "advantage": "前端技能完整", "need_learn": "深化前端工程化与性能优化"},
            {"target": "Java后端工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "后端基础扎实", "need_learn": "Java生态、企业级框架Spring"},
            {"target": "产品经理", "match_level": "中", "overlap_pct": 0.4, "advantage": "技术理解深度高", "need_learn": "产品规划、用户研究、数据分析"},
        ],
    },
    {
        "name": "嵌入式工程师",
        "overview": "负责嵌入式系统的软件开发，涵盖驱动程序、固件、RTOS应用，广泛用于IoT、汽车电子、工业控制等领域。",
        "industry": "制造业/电子/汽车",
        "industry_category": "IT/嵌入式",
        "salary": "12-28K",
        "market_heat": 6,
        "skills": ["C", "C++", "RTOS", "单片机", "ARM", "驱动开发", "Linux内核", "串口/I2C/SPI"],
        "required_skills": ["C/C++", "单片机", "RTOS"],
        "preferred_skills": ["ARM架构", "Linux驱动", "FPGA"],
        "bonus_skills": ["汽车电子（AUTOSAR）", "IoT协议", "低功耗优化"],
        "certs": ["ARM认证工程师", "嵌入式Linux认证"],
        "tags": ["嵌入式开发", "IoT", "驱动开发"],
        "promotions": [
            {"job": "初级嵌入式工程师", "years": "0-2年", "desc": "负责固件开发与驱动调试"},
            {"job": "中级嵌入式工程师", "years": "2-4年", "desc": "主导子系统设计与性能调优"},
            {"job": "高级嵌入式工程师/架构师", "years": "4-7年", "desc": "负责系统架构，选型与团队指导"},
            {"job": "嵌入式技术总监", "years": "7年+", "desc": "制定嵌入式技术规划，管理研发团队"},
        ],
        "transfers": [
            {"target": "云原生工程师", "match_level": "低", "overlap_pct": 0.25, "advantage": "系统底层理解", "need_learn": "容器化、Kubernetes、云平台"},
            {"target": "安全工程师", "match_level": "低", "overlap_pct": 0.3, "advantage": "底层系统分析能力", "need_learn": "网络安全、渗透测试、Web安全"},
        ],
    },
    {
        "name": "区块链工程师",
        "overview": "负责区块链底层平台、智能合约和DApp的研发，应用于金融、供应链、数字资产等去中心化场景。",
        "industry": "金融科技/Web3",
        "industry_category": "IT/区块链",
        "salary": "20-50K",
        "market_heat": 6,
        "skills": ["Solidity", "Web3.js", "Ethereum", "Go", "密码学", "智能合约", "DeFi", "Truffle"],
        "required_skills": ["Solidity", "以太坊生态", "密码学基础"],
        "preferred_skills": ["Web3.js", "Go语言", "Layer2"],
        "bonus_skills": ["ZK-SNARK", "跨链协议", "DeFi协议设计"],
        "certs": ["以太坊开发者认证", "Hyperledger认证"],
        "tags": ["区块链", "Web3", "智能合约"],
        "promotions": [
            {"job": "区块链工程师", "years": "0-3年", "desc": "开发智能合约，参与DApp研发"},
            {"job": "高级区块链工程师", "years": "3-6年", "desc": "主导协议设计，优化链上性能"},
            {"job": "区块链架构师/技术总监", "years": "6年+", "desc": "制定链技术路线，管理Web3团队"},
        ],
        "transfers": [
            {"target": "安全工程师", "match_level": "中", "overlap_pct": 0.5, "advantage": "密码学与漏洞分析能力（合约审计）", "need_learn": "传统网络安全、渗透测试"},
            {"target": "Python工程师", "match_level": "低", "overlap_pct": 0.35, "advantage": "Go/脚本能力", "need_learn": "Python生态、后端框架"},
        ],
    },
    {
        "name": "游戏开发工程师",
        "overview": "负责游戏客户端或服务端的开发，使用Unity/Unreal等引擎实现游戏玩法、图形渲染与网络同步。",
        "industry": "游戏/互联网娱乐",
        "industry_category": "IT/游戏",
        "salary": "15-35K",
        "market_heat": 6,
        "skills": ["Unity", "C#", "Unreal Engine", "C++", "游戏引擎", "图形渲染", "Lua", "网络编程"],
        "required_skills": ["Unity或Unreal", "C#或C++"],
        "preferred_skills": ["图形渲染（Shader）", "Lua脚本", "网络同步"],
        "bonus_skills": ["VR/AR开发", "物理引擎", "性能优化"],
        "certs": ["Unity认证工程师", "Epic Unreal认证"],
        "tags": ["游戏开发", "Unity", "图形渲染"],
        "promotions": [
            {"job": "初级游戏开发工程师", "years": "0-2年", "desc": "实现游戏模块功能，修复bug"},
            {"job": "中级游戏开发工程师", "years": "2-4年", "desc": "主导子系统开发，优化游戏性能"},
            {"job": "高级游戏工程师/技术主管", "years": "4-7年", "desc": "负责引擎架构，带领技术团队"},
            {"job": "技术总监/CTO", "years": "7年+", "desc": "制定技术规范，管理研发团队"},
        ],
        "transfers": [
            {"target": "前端工程师", "match_level": "低", "overlap_pct": 0.35, "advantage": "C#/JavaScript基础", "need_learn": "Web生态、Vue/React、CSS"},
            {"target": "嵌入式工程师", "match_level": "低", "overlap_pct": 0.3, "advantage": "C++底层能力", "need_learn": "RTOS、驱动开发、单片机"},
        ],
    },
]


def build_node(profile: dict) -> dict:
    name = profile["name"]
    return {
        "id": f"job_{name}",
        "attrs": {
            "node_type": "Job",
            "title": name,
            "overview": profile["overview"],
            "industry": profile["industry"],
            "industry_category": profile["industry_category"],
            "salary": profile["salary"],
            "skills": profile["skills"],
            "required_skills": profile["required_skills"],
            "preferred_skills": profile["preferred_skills"],
            "bonus_skills": profile["bonus_skills"],
            "certs": profile["certs"],
            "tags": profile["tags"],
            "market_heat": profile["market_heat"],
            "total_jd_count": 0,
            "education_level": "本科及以上",
            "majors": ["计算机", "软件工程", "信息工程", "电子信息"],
            "top_regions": ["北京", "上海", "深圳", "杭州", "成都"],
            "creativity": "能根据业务需求设计技术方案，解决工程难题。",
            "learning": "能快速学习新技术，持续跟进行业前沿动态。",
            "stress_resistance": "能承受项目压力，在deadline驱动下保质保量交付。",
            "communication": "能与产品、测试、业务等团队有效协作沟通。",
            "internship": "有相关实习或项目经历者优先。",
        }
    }


def build_edges(profile: dict) -> list:
    name = profile["name"]
    edges = []
    from_id = f"job_{name}"

    for i, prom in enumerate(profile.get("promotions", [])):
        target_name = prom["job"]
        to_id = f"job_{target_name}"
        edges.append({
            "from": from_id,
            "to": to_id,
            "props": {
                "edge_type": "PROMOTES_TO",
                "years": prom["years"],
                "description": prom["desc"],
            }
        })

    for trans in profile.get("transfers", []):
        target_name = trans["target"]
        to_id = f"job_{target_name}"
        edges.append({
            "from": from_id,
            "to": to_id,
            "props": {
                "edge_type": "CAN_TRANSFER_TO",
                "match_level": trans["match_level"],
                "overlap_pct": trans["overlap_pct"],
                "advantage": trans["advantage"],
                "need_learn": trans["need_learn"],
            }
        })

    return edges


def build_promotion_nodes(profile: dict) -> list:
    """生成晋升路径中间节点"""
    nodes = []
    for prom in profile.get("promotions", []):
        node_id = f"job_{prom['job']}"
        nodes.append({
            "id": node_id,
            "attrs": {
                "node_type": "Job",
                "title": prom["job"],
                "overview": prom["desc"],
                "industry": profile["industry"],
                "industry_category": profile["industry_category"],
                "salary": "",
                "skills": [],
                "required_skills": [],
                "preferred_skills": [],
                "bonus_skills": [],
                "certs": [],
                "tags": [],
                "market_heat": 5,
                "total_jd_count": 0,
            }
        })
    return nodes


def main():
    print(f"Loading {GRAPH_PATH}")
    data = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))

    existing_ids = {n["id"] for n in data.get("nodes", [])}
    existing_edges = {(e["from"], e["to"]) for e in data.get("edges", [])}

    added_nodes = 0
    added_edges = 0

    for profile in IT_JOB_PROFILES:
        name = profile["name"]
        main_node = build_node(profile)

        # Add/update main job node
        if main_node["id"] in existing_ids:
            # Update existing node with complete data
            for n in data["nodes"]:
                if n["id"] == main_node["id"]:
                    n["attrs"].update(main_node["attrs"])
                    print(f"  Updated: {main_node['id']}")
                    break
        else:
            data["nodes"].append(main_node)
            existing_ids.add(main_node["id"])
            added_nodes += 1
            print(f"  Added main: {main_node['id']}")

        # Add promotion intermediate nodes
        for prom_node in build_promotion_nodes(profile):
            if prom_node["id"] not in existing_ids:
                data["nodes"].append(prom_node)
                existing_ids.add(prom_node["id"])
                added_nodes += 1

        # Add edges
        for edge in build_edges(profile):
            key = (edge["from"], edge["to"])
            if key not in existing_edges:
                data["edges"].append(edge)
                existing_edges.add(key)
                added_edges += 1

    GRAPH_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. Added {added_nodes} nodes, {added_edges} edges.")
    print(f"Total nodes: {len(data['nodes'])}, edges: {len(data['edges'])}")


if __name__ == "__main__":
    main()
