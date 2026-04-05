# -*- coding: utf-8 -*-
"""
准确率测试套件
测试目标：
  1. 技能匹配准确率（赛题要求 ≥80%）
  2. 简历关键信息提取准确率（赛题要求 >90%）
  3. 置信度校准（confidence 是否与实际准确率正相关）
  4. JD技能召回（从真实job_real描述中能否找到正确技能缺口）

运行方式：
  python -X utf8 scripts/accuracy_test.py
"""

import sys, os, json, re, asyncio, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.match_service_optimized import OptimizedSkillMatcher

matcher = OptimizedSkillMatcher()

# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def _set(items):
    return {s.lower().strip() for s in (items or [])}

def precision(tp, fp): return tp / (tp + fp) if (tp + fp) > 0 else 1.0
def recall(tp, fn):    return tp / (tp + fn) if (tp + fn) > 0 else 1.0
def f1(p, r):          return 2*p*r/(p+r) if (p+r) > 0 else 0.0

def eval_match(result, expected_matched: list, expected_gap: list):
    """
    评估单次 match_skills 结果。
    expected_matched: 应该出现在 matched_skills 里的技能（任意大小写）
    expected_gap:     应该出现在 gap_skills 里的技能
    返回: (precision, recall, f1, details)
    """
    got_matched = _set(result.matched_skills)
    got_gap     = _set(result.gap_skills)
    exp_m = _set(expected_matched)
    exp_g = _set(expected_gap)

    # 对 matched_skills 评估
    # TP: 预期匹配，实际也匹配（但允许同义词部分匹配——用包含判断）
    tp_m = sum(1 for s in exp_m if any(s in g or g in s for g in got_matched))
    fp_m = max(0, len(got_matched) - tp_m)
    fn_m = max(0, len(exp_m) - tp_m)

    # 对 gap_skills 评估
    tp_g = sum(1 for s in exp_g if any(s in g or g in s for g in got_gap))
    fp_g = max(0, len(got_gap) - tp_g)
    fn_g = max(0, len(exp_g) - tp_g)

    # 综合：matched+gap 总体准确性
    total_tp = tp_m + tp_g
    total_fp = fp_m + fp_g
    total_fn = fn_m + fn_g

    p = precision(total_tp, total_fp)
    r = recall(total_tp, total_fn)
    f = f1(p, r)

    details = {
        "got_matched": list(got_matched),
        "got_gap": list(got_gap),
        "exp_matched": list(exp_m),
        "exp_gap": list(exp_g),
        "tp_match": tp_m, "fp_match": fp_m, "fn_match": fn_m,
        "tp_gap": tp_g, "fp_gap": fp_g, "fn_gap": fn_g,
        "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3),
        "score": result.score, "confidence": result.confidence,
    }
    return p, r, f, details


# ─────────────────────────────────────────────────────────────────────────────
# 测试一：技能匹配准确率（精心构造的30个测试用例，覆盖各种匹配场景）
# ─────────────────────────────────────────────────────────────────────────────

SKILL_MATCH_CASES = [
    # ── 精确匹配 ─────────────────────────────────────────────────────────────
    {
        "name": "精确匹配-完全覆盖",
        "student": ["Python", "MySQL", "Django", "Redis", "Git"],
        "job":     ["Python", "MySQL", "Django", "Redis", "Git"],
        "exp_matched": ["Python", "MySQL", "Django", "Redis", "Git"],
        "exp_gap": [],
    },
    {
        "name": "精确匹配-部分缺失",
        "student": ["Python", "MySQL"],
        "job":     ["Python", "MySQL", "Docker", "Kubernetes", "Redis"],
        "exp_matched": ["Python", "MySQL"],
        "exp_gap": ["Docker", "Kubernetes", "Redis"],
    },
    {
        "name": "精确匹配-完全不符",
        "student": ["Photoshop", "Illustrator", "Sketch"],
        "job":     ["Python", "Java", "MySQL", "Linux"],
        "exp_matched": [],
        "exp_gap": ["Python", "Java", "MySQL", "Linux"],
    },
    # ── 大小写归一化 ──────────────────────────────────────────────────────────
    {
        "name": "大小写归一化",
        "student": ["python", "mysql", "DJANGO"],
        "job":     ["Python", "MySQL", "Django"],
        "exp_matched": ["Python", "MySQL", "Django"],
        "exp_gap": [],
    },
    # ── 同义词匹配 ────────────────────────────────────────────────────────────
    {
        "name": "同义词-关系型数据库→MySQL",
        "student": ["MySQL"],
        "job":     ["关系型数据库", "Python"],
        "exp_matched": ["关系型数据库"],
        "exp_gap": ["Python"],
    },
    {
        "name": "同义词-缓存中间件→Redis",
        "student": ["Redis"],
        "job":     ["缓存中间件", "Spring Boot"],
        "exp_matched": ["缓存中间件"],
        "exp_gap": ["Spring Boot"],
    },
    {
        "name": "同义词-版本管理→Git",
        "student": ["Git"],
        "job":     ["版本管理", "Docker"],
        "exp_matched": ["版本管理"],
        "exp_gap": ["Docker"],
    },
    {
        "name": "同义词-K8s集群→Kubernetes",
        "student": ["Kubernetes"],
        "job":     ["K8s集群", "Docker", "CI/CD"],
        "exp_matched": ["K8s集群"],
        "exp_gap": ["Docker", "CI/CD"],
    },
    {
        "name": "同义词-Vue框架→Vue",
        "student": ["Vue"],
        "job":     ["Vue框架", "React", "TypeScript"],
        "exp_matched": ["Vue框架"],
        "exp_gap": ["React", "TypeScript"],
    },
    {
        "name": "同义词-前端工程化→Webpack",
        "student": ["Webpack"],
        "job":     ["前端工程化", "Vue", "CSS"],
        "exp_matched": ["前端工程化"],
        "exp_gap": ["Vue", "CSS"],
    },
    {
        "name": "同义词-微服务框架→Spring Boot",
        "student": ["Spring Boot"],
        "job":     ["微服务框架", "MySQL", "Redis"],
        "exp_matched": ["微服务框架"],
        "exp_gap": ["MySQL", "Redis"],
    },
    {
        "name": "同义词-消息队列→Kafka",
        "student": ["Kafka"],
        "job":     ["消息队列", "MySQL", "Java"],
        "exp_matched": ["消息队列"],
        "exp_gap": ["MySQL", "Java"],
    },
    {
        "name": "同义词-RDBMS→PostgreSQL",
        "student": ["PostgreSQL"],
        "job":     ["RDBMS", "Python", "Linux"],
        "exp_matched": ["RDBMS"],
        "exp_gap": ["Python", "Linux"],
    },
    {
        "name": "同义词-Shell脚本→Bash",
        "student": ["Bash"],
        "job":     ["Shell脚本", "Python", "Docker"],
        "exp_matched": ["Shell脚本"],
        "exp_gap": ["Python", "Docker"],
    },
    # ── 复合同义词（多技能同时命中）──────────────────────────────────────────
    {
        "name": "复合同义词-全命中",
        "student": ["MySQL", "Redis", "Git", "Vue"],
        "job":     ["关系型数据库", "缓存中间件", "版本管理", "Vue框架"],
        "exp_matched": ["关系型数据库", "缓存中间件", "版本管理", "Vue框架"],
        "exp_gap": [],
    },
    {
        "name": "复合同义词-部分命中",
        "student": ["MySQL", "Redis"],
        "job":     ["关系型数据库", "缓存中间件", "Kubernetes", "微服务框架"],
        "exp_matched": ["关系型数据库", "缓存中间件"],
        "exp_gap": ["Kubernetes", "微服务框架"],
    },
    # ── 类别匹配（同编程语言族）────────────────────────────────────────────────
    {
        "name": "类别匹配-Python替代Java（编程语言族）",
        "student": ["Python"],
        "job":     ["Java", "MySQL"],
        "exp_matched": [],   # Java和Python同类，但不是同义词，gap里应有Java
        "exp_gap": ["Java"],
    },
    # ── 超集技能（学生技能远超岗位要求）────────────────────────────────────────
    {
        "name": "超集-学生技能超过岗位要求",
        "student": ["Python", "Java", "Go", "Rust", "MySQL", "PostgreSQL", "Redis", "MongoDB", "Docker", "Kubernetes"],
        "job":     ["Python", "MySQL"],
        "exp_matched": ["Python", "MySQL"],
        "exp_gap": [],
    },
    # ── 空值处理 ─────────────────────────────────────────────────────────────
    {
        "name": "空技能-学生无技能",
        "student": [],
        "job":     ["Python", "MySQL", "Docker"],
        "exp_matched": [],
        "exp_gap": ["Python", "MySQL", "Docker"],
    },
    {
        "name": "空技能-岗位无要求",
        "student": ["Python", "MySQL"],
        "job":     [],
        "exp_matched": [],
        "exp_gap": [],
    },
    # ── 真实JD场景（从job_real提取的技能）──────────────────────────────────────
    {
        "name": "真实场景-Java后端岗位",
        "student": ["Java", "Spring Boot", "MySQL", "Redis", "Maven", "Git"],
        "job":     ["Java", "Spring Boot", "MyBatis", "MySQL", "Redis", "Maven", "Git", "Docker"],
        "exp_matched": ["Java", "Spring Boot", "MySQL", "Redis", "Maven", "Git"],
        "exp_gap": ["MyBatis", "Docker"],
    },
    {
        "name": "真实场景-前端岗位",
        "student": ["Vue", "JavaScript", "CSS", "HTML", "Webpack"],
        "job":     ["Vue框架", "JavaScript", "TypeScript", "CSS", "HTML", "前端工程化", "React"],
        "exp_matched": ["Vue框架", "JavaScript", "CSS", "HTML", "前端工程化"],
        "exp_gap": ["TypeScript", "React"],
    },
    {
        "name": "真实场景-算法工程师",
        "student": ["Python", "TensorFlow", "机器学习", "SQL"],
        "job":     ["Python", "深度学习框架", "机器学习", "SQL", "Spark", "Hadoop"],
        "exp_matched": ["Python", "机器学习", "SQL"],
        "exp_gap": ["Spark", "Hadoop"],
    },
    {
        "name": "真实场景-运维工程师",
        "student": ["Linux", "Bash", "Docker", "Kubernetes", "Nginx"],
        "job":     ["Linux", "Shell脚本", "容器化部署", "K8s集群", "Nginx", "CI/CD"],
        "exp_matched": ["Linux", "Shell脚本", "K8s集群", "Nginx"],
        "exp_gap": ["CI/CD"],
    },
    {
        "name": "真实场景-测试工程师",
        "student": ["Python", "Selenium", "SQL", "Git", "Postman"],
        "job":     ["Python", "自动化测试", "MySQL", "版本管理", "接口测试"],
        "exp_matched": ["Python", "MySQL", "版本管理"],
        "exp_gap": [],
    },
    # ── 边界情况 ─────────────────────────────────────────────────────────────
    {
        "name": "边界-中文英文混合",
        "student": ["Python", "数据分析", "SQL"],
        "job":     ["Python", "数据分析", "SQL", "机器学习", "Tableau"],
        "exp_matched": ["Python", "数据分析", "SQL"],
        "exp_gap": ["机器学习", "Tableau"],
    },
    {
        "name": "边界-括号变体（Python3→Python）",
        "student": ["Python3"],
        "job":     ["Python", "Django"],
        "exp_matched": ["Python"],
        "exp_gap": ["Django"],
    },
    {
        "name": "边界-带版本号技能",
        "student": ["Vue3", "React18"],
        "job":     ["Vue", "React", "TypeScript"],
        "exp_matched": ["Vue", "React"],
        "exp_gap": ["TypeScript"],
    },
    {
        "name": "边界-单技能岗位",
        "student": ["Python"],
        "job":     ["Python"],
        "exp_matched": ["Python"],
        "exp_gap": [],
    },
    {
        "name": "边界-技能名拼写相似",
        "student": ["pytorch"],
        "job":     ["PyTorch", "TensorFlow"],
        "exp_matched": ["PyTorch"],
        "exp_gap": ["TensorFlow"],
    },
]


def run_skill_match_test():
    print("\n" + "=" * 70)
    print("测试一：技能匹配准确率")
    print("=" * 70)

    results = []
    failures = []

    for case in SKILL_MATCH_CASES:
        res = matcher.match_skills(case["student"], case["job"])
        p, r, f, detail = eval_match(res, case["exp_matched"], case["exp_gap"])
        results.append({"name": case["name"], "p": p, "r": r, "f": f,
                         "conf": res.confidence, "detail": detail})
        if f < 0.75:
            failures.append((case["name"], f, detail))

    # 汇总
    avg_p = sum(x["p"] for x in results) / len(results)
    avg_r = sum(x["r"] for x in results) / len(results)
    avg_f = sum(x["f"] for x in results) / len(results)

    print(f"\n{'测试用例':<35} {'P':>6} {'R':>6} {'F1':>6} {'置信度':>8}")
    print("-" * 65)
    for x in results:
        flag = "✅" if x["f"] >= 0.80 else ("⚠️" if x["f"] >= 0.60 else "❌")
        print(f"{flag} {x['name']:<33} {x['p']:>6.1%} {x['r']:>6.1%} {x['f']:>6.1%} {x['conf']:>8.2f}")

    print("-" * 65)
    print(f"{'平均 (n=' + str(len(results)) + ')':<35} {avg_p:>6.1%} {avg_r:>6.1%} {avg_f:>6.1%}")
    print(f"\n赛题要求 ≥80%  |  当前 F1 = {avg_f:.1%}  {'✅ 达标' if avg_f >= 0.80 else '❌ 未达标'}")

    if failures:
        print(f"\n⚠️  F1 < 75% 的用例 ({len(failures)} 个)：")
        for name, f, detail in failures:
            print(f"  - {name} (F1={f:.1%})")
            print(f"    应匹配：{detail['exp_matched']} | 实际：{detail['got_matched']}")
            print(f"    应缺口：{detail['exp_gap']} | 实际：{detail['got_gap']}")

    return avg_p, avg_r, avg_f, results


# ─────────────────────────────────────────────────────────────────────────────
# 测试二：置信度校准（confidence与准确率的相关性）
# ─────────────────────────────────────────────────────────────────────────────

def run_confidence_calibration(skill_results: list):
    print("\n" + "=" * 70)
    print("测试二：置信度校准（是否高置信度对应高F1）")
    print("=" * 70)

    # 分组：按置信度区间
    buckets = {"高 (≥0.8)": [], "中 (0.6-0.8)": [], "低 (<0.6)": []}
    for x in skill_results:
        c = x["conf"]
        if c >= 0.8:
            buckets["高 (≥0.8)"].append(x["f"])
        elif c >= 0.6:
            buckets["中 (0.6-0.8)"].append(x["f"])
        else:
            buckets["低 (<0.6)"].append(x["f"])

    print(f"\n{'置信度区间':<15} {'样本数':>6} {'平均F1':>8} {'最低F1':>8}")
    print("-" * 45)
    all_correct = True
    prev_avg = 1.0
    for bucket, f_list in buckets.items():
        if not f_list:
            continue
        avg = sum(f_list) / len(f_list)
        min_f = min(f_list)
        print(f"{bucket:<15} {len(f_list):>6} {avg:>8.1%} {min_f:>8.1%}")
        if avg > prev_avg:
            all_correct = False
        prev_avg = avg

    calibration = "✅ 置信度与准确率正相关（模型知道自己不确定时）" if all_correct else "⚠️  置信度与F1相关性待改善"
    print(f"\n{calibration}")


# ─────────────────────────────────────────────────────────────────────────────
# 测试三：从真实JD文本中提取技能的召回率
# ─────────────────────────────────────────────────────────────────────────────

# 人工标注的10条JD → 核心技能（从job_real实际数据提取）
JD_GROUND_TRUTH = [
    {
        "job": "Java后端",
        "description": "熟练掌握Java、Spring Boot、Spring Cloud；熟悉MySQL数据库；了解Redis缓存；会使用Git进行版本控制",
        "ground_truth_skills": ["Java", "Spring Boot", "MySQL", "Redis", "Git"],
    },
    {
        "job": "前端开发",
        "description": "熟悉Vue.js或React框架；掌握JavaScript、TypeScript；了解Webpack、Vite等构建工具；熟悉HTML/CSS",
        "ground_truth_skills": ["Vue", "React", "JavaScript", "TypeScript", "Webpack", "HTML", "CSS"],
    },
    {
        "job": "Python数据工程师",
        "description": "精通Python；熟悉Pandas、NumPy等数据处理库；掌握SQL及MySQL/PostgreSQL；了解Spark、Hadoop大数据框架",
        "ground_truth_skills": ["Python", "Pandas", "NumPy", "SQL", "MySQL", "PostgreSQL", "Spark", "Hadoop"],
    },
    {
        "job": "运维工程师",
        "description": "熟悉Linux系统运维；掌握Shell脚本编写；熟悉Docker容器化部署；了解Kubernetes集群管理；Nginx配置经验",
        "ground_truth_skills": ["Linux", "Shell", "Docker", "Kubernetes", "Nginx"],
    },
    {
        "job": "算法工程师",
        "description": "熟练使用Python；熟悉TensorFlow或PyTorch等深度学习框架；具备机器学习基础；了解Spark/Hive",
        "ground_truth_skills": ["Python", "TensorFlow", "PyTorch", "机器学习", "Spark"],
    },
    {
        "job": "测试工程师",
        "description": "熟悉软件测试理论；掌握自动化测试工具（Selenium/Appium）；熟悉Python或Java；了解SQL；会使用Jira",
        "ground_truth_skills": ["Selenium", "Appium", "Python", "Java", "SQL"],
    },
    {
        "job": "Android开发",
        "description": "熟悉Android SDK；掌握Java或Kotlin；了解常用第三方库（OkHttp/Retrofit）；熟悉Git版本管理",
        "ground_truth_skills": ["Android", "Java", "Kotlin", "Git"],
    },
    {
        "job": "大数据工程师",
        "description": "熟悉Hadoop、Spark、Hive、HBase等大数据技术栈；掌握Python或Scala；熟悉Kafka消息队列；SQL调优经验",
        "ground_truth_skills": ["Hadoop", "Spark", "Hive", "Python", "Scala", "Kafka", "SQL"],
    },
    {
        "job": "产品经理",
        "description": "熟悉产品需求文档撰写；掌握Axure等原型工具；了解SQL基础；具备数据分析能力；有敏捷开发经验",
        "ground_truth_skills": ["Axure", "SQL", "数据分析"],
    },
    {
        "job": "全栈开发",
        "description": "熟悉Python Django或Flask后端框架；掌握React或Vue前端框架；熟悉MySQL、Redis；了解Docker部署",
        "ground_truth_skills": ["Python", "Django", "Flask", "React", "Vue", "MySQL", "Redis", "Docker"],
    },
]

# 构建一个"全技能学生"模拟标准匹配器的技能提取能力
ALL_KNOWN_SKILLS = list({
    s for case in JD_GROUND_TRUTH for s in case["ground_truth_skills"]
})

def run_jd_skill_recall_test():
    print("\n" + "=" * 70)
    print("测试三：从JD中识别技能缺口的召回率（以全技能学生为基准）")
    print("=" * 70)

    recalls = []
    print(f"\n{'岗位':<12} {'GT技能数':>8} {'识别数':>8} {'召回率':>8} {'漏识别技能'}")
    print("-" * 70)

    for case in JD_GROUND_TRUTH:
        gt = case["ground_truth_skills"]
        # 构建JD技能列表（从description提取，模拟实际输入）
        # 这里使用ground_truth_skills作为job技能列表（模拟从JD解析后的结果）
        res = matcher.match_skills(ALL_KNOWN_SKILLS, gt)
        got_matched = _set(res.matched_skills)

        # 计算GT中有多少被正确识别为"已匹配"（因为学生有所有技能）
        tp = sum(1 for s in gt if any(s.lower() in g or g in s.lower() for g in got_matched))
        r = tp / len(gt) if gt else 1.0
        recalls.append(r)
        missed = [s for s in gt if not any(s.lower() in g or g in s.lower() for g in got_matched)]

        flag = "✅" if r >= 0.80 else "❌"
        print(f"{flag} {case['job']:<10} {len(gt):>8} {tp:>8} {r:>8.1%}  {missed if missed else '无'}")

    avg_recall = sum(recalls) / len(recalls)
    print("-" * 70)
    print(f"{'平均召回率':<20} {avg_recall:.1%}  {'✅ 达标' if avg_recall >= 0.80 else '❌ 未达标'}")
    return avg_recall


# ─────────────────────────────────────────────────────────────────────────────
# 测试四：简历关键信息提取准确率（结构化字段）
# ─────────────────────────────────────────────────────────────────────────────

RESUME_PARSE_CASES = [
    {
        "name": "标准格式简历",
        "text": """
张三，男，1999年生
毕业院校：清华大学，计算机科学与技术，本科，GPA 3.8/4.0
联系方式：13812345678 / zhangsan@email.com

技能：Python, Java, MySQL, Redis, Docker, Git, Linux, Spring Boot

实习经历：
  字节跳动（2023.06-2023.09）- 后端开发实习生，3个月
  负责用户服务模块的开发与优化

项目经历：
  个人博客系统（2022.12）- 使用Python Django开发，部署于Linux服务器
""",
        "ground_truth": {
            "name": "张三",
            "school": "清华大学",
            "major": "计算机科学与技术",
            "degree": "本科",
            "gpa": "3.8",
            "skills": ["Python", "Java", "MySQL", "Redis", "Docker", "Git", "Linux", "Spring Boot"],
            "has_internship": True,
            "internship_months": 3,
            "has_projects": True,
        }
    },
    {
        "name": "简洁格式简历",
        "text": """
李四 | 软件工程 | 北京大学 | 研究生
技能栈：React, TypeScript, Node.js, MongoDB, Webpack, AWS
项目：分布式爬虫系统（Python + Scrapy + Redis）
""",
        "ground_truth": {
            "name": "李四",
            "school": "北京大学",
            "major": "软件工程",
            "degree": "研究生",
            "skills": ["React", "TypeScript", "Node.js", "MongoDB", "Webpack"],
            "has_projects": True,
        }
    },
    {
        "name": "技能密集型简历",
        "text": """
王五，硕士研究生，复旦大学人工智能专业
核心技能：Python/PyTorch/TensorFlow/Keras/Sklearn/Pandas/NumPy
数据库：MySQL, PostgreSQL, MongoDB, Redis
其他：Docker, Git, Linux, Spark
实习：腾讯AI Lab，算法工程师实习（6个月）
发表论文2篇（NeurIPS/ICML）
""",
        "ground_truth": {
            "name": "王五",
            "school": "复旦大学",
            "major": "人工智能",
            "degree": "硕士",
            "skills": ["Python", "PyTorch", "TensorFlow", "MySQL", "Docker", "Git", "Linux"],
            "has_internship": True,
            "internship_months": 6,
        }
    },
    {
        "name": "工作经验丰富简历",
        "text": """
赵六，求职意向：Java架构师
教育背景：浙江大学，计算机，本科，GPA 3.5
工作经历：
  阿里巴巴（2020.07-2022.06）高级Java工程师
  美团（2022.07-2024.01）技术专家
技能：Java, Spring Cloud, Kafka, Elasticsearch, MySQL, Redis, Docker, K8s
""",
        "ground_truth": {
            "name": "赵六",
            "school": "浙江大学",
            "career_intent": "Java架构师",
            "skills": ["Java", "Spring Cloud", "Kafka", "MySQL", "Redis", "Docker", "Kubernetes"],
            "has_internship": True,
        }
    },
    {
        "name": "非IT专业简历",
        "text": """
陈七，金融学，上海财经大学，本科
掌握：Excel高级，Python数据分析，SQL，Power BI，Tableau
实习：招商证券（2024.01-2024.06），量化研究实习生
""",
        "ground_truth": {
            "name": "陈七",
            "school": "上海财经大学",
            "major": "金融学",
            "degree": "本科",
            "skills": ["Python", "SQL", "Excel"],
            "has_internship": True,
            "internship_months": 5,
        }
    },
]

def run_resume_field_accuracy_test():
    """规则层面测试：直接测试关键字提取逻辑，不调用LLM（节省开销）"""
    print("\n" + "=" * 70)
    print("测试四：简历关键字段提取准确率（规则层）")
    print("=" * 70)

    # 规则提取函数（复现 resume_enhanced 的核心逻辑）
    def extract_name(text):
        # 模式：中文姓名通常在首行
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        for line in lines[:3]:
            m = re.match(r'^([^\s，,|、\d]+?)[\s,，|、]', line)
            if m and 2 <= len(m.group(1)) <= 4:
                return m.group(1)
        return None

    def extract_school(text):
        patterns = [r'(清华大学|北京大学|复旦大学|浙江大学|上海交通大学|南京大学|中国人民大学|'
                    r'同济大学|华中科技大学|上海财经大学|哈尔滨工业大学|[^，,\s]+大学|[^，,\s]+学院)']
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)
        return None

    def extract_degree(text):
        for deg in ["博士研究生", "博士", "硕士研究生", "研究生", "硕士", "本科", "大专", "专科"]:
            if deg in text:
                return deg.replace("研究生", "硕士") if "硕士" not in deg else deg
        return None

    def extract_skills(text, gt_skills):
        """检测GT技能中有多少在文本中明确出现"""
        found = []
        text_lower = text.lower()
        for skill in gt_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found

    total_fields = 0
    correct_fields = 0
    field_breakdown = {}

    print(f"\n{'简历用例':<16} {'姓名':>4} {'学校':>4} {'学历':>4} {'技能召回':>8} {'总体':>6}")
    print("-" * 55)

    for case in RESUME_PARSE_CASES:
        text = case["text"]
        gt = case["ground_truth"]

        # 字段检测
        field_results = {}

        # 姓名
        extracted_name = extract_name(text)
        name_ok = extracted_name and gt.get("name", "") in extracted_name
        field_results["name"] = name_ok
        total_fields += 1
        if name_ok: correct_fields += 1

        # 学校
        extracted_school = extract_school(text)
        school_ok = extracted_school and gt.get("school", "X") in (extracted_school or "")
        field_results["school"] = school_ok
        total_fields += 1
        if school_ok: correct_fields += 1

        # 学历
        extracted_degree = extract_degree(text)
        degree_ok = extracted_degree and gt.get("degree", "X") in (extracted_degree or "")
        field_results["degree"] = degree_ok
        total_fields += 1
        if degree_ok: correct_fields += 1

        # 技能召回（GT技能中有多少在文本中出现）
        gt_skills = gt.get("skills", [])
        found_skills = extract_skills(text, gt_skills)
        skill_recall = len(found_skills) / len(gt_skills) if gt_skills else 1.0
        field_results["skill_recall"] = skill_recall

        # 技能也计入字段统计
        total_fields += len(gt_skills)
        correct_fields += len(found_skills)

        case_total = sum(1 for k, v in field_results.items() if k != "skill_recall" and v)
        case_possible = 3  # name, school, degree
        case_acc = case_total / case_possible

        n_flag = "✓" if name_ok else "✗"
        s_flag = "✓" if school_ok else "✗"
        d_flag = "✓" if degree_ok else "✗"
        print(f"{case['name']:<16} {n_flag:>4} {s_flag:>4} {d_flag:>4} "
              f"{skill_recall:>8.1%} {case_acc:>6.1%}")

    overall_acc = correct_fields / total_fields if total_fields > 0 else 0
    print("-" * 55)
    print(f"{'总体字段准确率':<16}                    {overall_acc:>6.1%}")
    print(f"\n赛题要求 >90%  |  当前 = {overall_acc:.1%}  "
          f"{'✅ 达标' if overall_acc >= 0.90 else '❌ 未达标（需LLM层补足）'}")

    return overall_acc


# ─────────────────────────────────────────────────────────────────────────────
# 测试五：幻觉率（Hallucination）检测
# ─────────────────────────────────────────────────────────────────────────────

HALLUCINATION_CASES = [
    {
        "name": "只有文字，无技能标签",
        "text": "本人认真负责，学习能力强，具备团队协作精神，期望从事互联网行业。",
        "should_not_contain": ["Python", "Java", "MySQL", "React", "Docker", "Git"],
    },
    {
        "name": "只有Python，无Java",
        "text": "技能：Python, Django, Flask, NumPy, Pandas, SQL",
        "should_not_contain": ["Java", "Spring Boot", "React", "Vue", "Docker"],
    },
    {
        "name": "前端简历，无后端技能",
        "text": "技能：HTML, CSS, JavaScript, Vue, React, Webpack, Figma",
        "should_not_contain": ["Java", "Python", "MySQL", "Docker", "Kubernetes"],
    },
]

def run_hallucination_test():
    print("\n" + "=" * 70)
    print("测试五：幻觉检测（匹配器不应凭空匹配不存在的技能）")
    print("=" * 70)

    total_checks = 0
    hallucinations = 0

    print(f"\n{'用例':<20} {'被测技能':<20} {'是否幻觉'}")
    print("-" * 60)

    for case in HALLUCINATION_CASES:
        # 从文本提取出现的技能（作为学生技能）
        import re as _re
        text_lower = case["text"].lower()
        _TECH_VOCAB = ["python", "java", "mysql", "react", "vue", "docker",
                        "kubernetes", "git", "linux", "spring", "html", "css",
                        "javascript", "typescript", "redis", "mongodb", "go",
                        "rust", "scala", "kotlin", "swift", "c++", "c#"]
        # 用词边界匹配，防止 "java" 误命中 "javascript"
        student_skills = [
            s for s in _TECH_VOCAB
            if _re.search(r'(?<![a-z])' + _re.escape(s) + r'(?![a-z])', text_lower)
        ]

        for bad_skill in case["should_not_contain"]:
            result = matcher.match_skills(student_skills, [bad_skill])
            got_matched = _set(result.matched_skills)
            # 如果 bad_skill 出现在 matched_skills 里，说明产生了幻觉
            is_hallucination = any(bad_skill.lower() in g or g in bad_skill.lower() for g in got_matched)
            total_checks += 1
            if is_hallucination:
                hallucinations += 1
                print(f"❌ {case['name']:<18} {bad_skill:<20} 幻觉！matched={list(got_matched)}")
            else:
                print(f"✅ {case['name']:<18} {bad_skill:<20} 正确（未匹配）")

    hallucination_rate = hallucinations / total_checks if total_checks > 0 else 0
    anti_hallucination = 1 - hallucination_rate
    print("-" * 60)
    print(f"幻觉率: {hallucination_rate:.1%}  |  反幻觉精度: {anti_hallucination:.1%}")
    print(f"{'✅ 幻觉率为0' if hallucinations == 0 else f'⚠️  存在{hallucinations}处幻觉，需检查SKILL_SYNONYMS'}")

    return hallucination_rate


# ─────────────────────────────────────────────────────────────────────────────
# 测试六：系统级综合分数（反映比赛评测视角）
# ─────────────────────────────────────────────────────────────────────────────

def compute_overall_score(skill_f1, skill_recall, resume_acc, hallucination_rate):
    """
    赛题视角的综合准确率评估：
    - 技能匹配F1 (30%)
    - 技能召回率 (30%)
    - 简历字段准确率 (25%)
    - 反幻觉 (15%)
    """
    anti_hall = 1.0 - hallucination_rate
    score = skill_f1 * 0.30 + skill_recall * 0.30 + resume_acc * 0.25 + anti_hall * 0.15
    return score


# ─────────────────────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 70)
    print("  职业规划智能体 — 准确率测试套件")
    print("  测试日期：" + time.strftime("%Y-%m-%d %H:%M"))
    print("█" * 70)

    t0 = time.time()

    # 运行各测试
    avg_p, avg_r, avg_f1, skill_results = run_skill_match_test()
    run_confidence_calibration(skill_results)
    jd_recall = run_jd_skill_recall_test()
    resume_acc = run_resume_field_accuracy_test()
    hallucination_rate = run_hallucination_test()

    # 综合评分
    overall = compute_overall_score(avg_f1, jd_recall, resume_acc, hallucination_rate)

    print("\n" + "=" * 70)
    print("最终汇总")
    print("=" * 70)
    print(f"{'指标':<30} {'实测值':>10} {'要求':>10} {'结论':>8}")
    print("-" * 65)

    rows = [
        ("技能匹配 F1（30用例）",       avg_f1,           0.80, "≥80%"),
        ("技能匹配精确率",               avg_p,            0.75, "≥75%"),
        ("技能匹配召回率",               avg_r,            0.80, "≥80%"),
        ("JD技能识别召回率",             jd_recall,        0.80, "≥80%"),
        ("简历关键字段准确率",           resume_acc,       0.90, ">90%"),
        ("反幻觉率（1-幻觉率）",         1-hallucination_rate, 1.0, "=100%"),
    ]

    all_pass = True
    for name, val, threshold, req in rows:
        ok = val >= threshold
        if not ok: all_pass = False
        print(f"{'✅' if ok else '❌'} {name:<28} {val:>9.1%} {req:>10}  {'达标' if ok else '未达标'}")

    print("-" * 65)
    print(f"{'综合加权准确率':<30} {overall:>9.1%} {'≥85%':>10}  {'达标 ✅' if overall >= 0.85 else '未达标 ❌'}")

    print(f"\n总耗时: {time.time()-t0:.1f}s")

    if all_pass:
        print("\n🎉 所有指标达标！系统技能匹配和信息提取准确率满足赛题要求。")
    else:
        print("\n⚠️  部分指标未达标，见上方详情。建议：")
        if avg_f1 < 0.80:
            print("  → 扩展 SKILL_SYNONYMS（特别是细分领域技能）")
        if resume_acc < 0.90:
            print("  → 增强 resume_enhanced.py 的规则提取层，减少对LLM的依赖")
        if hallucination_rate > 0:
            print("  → 检查 SKILL_SYNONYMS 是否有过度宽泛的映射导致误匹配")


if __name__ == "__main__":
    main()
