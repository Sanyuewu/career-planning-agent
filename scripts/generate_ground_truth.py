# -*- coding: utf-8 -*-
"""
Ground Truth 生成器
从 data/job_profiles.json（51个真实岗位）自动生成系统性测试用例，
输出到 data/eval/ground_truth.jsonl

生成策略（每个岗位生成4类学生画像）：
  1. full_match    — 持有所有必需+部分优先技能，期望全匹配
  2. partial_match — 只持有50%必需技能，期望部分匹配
  3. synonym_match — 只持有必需技能的同义词，测试同义词召回
  4. no_match      — 持有另一域技能，期望零匹配

同时生成 skill_pair 文件：所有 SKILL_SYNONYMS 对的 is_match ground truth。
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── 技能规范化：拆分 "HTML/CSS/JavaScript" 等组合条目 ──────────────────────────

def _split_compound(skill: str) -> list:
    """把 'HTML/CSS/JavaScript' 拆成 ['HTML', 'CSS', 'JavaScript']"""
    parts = re.split(r'[/、]', skill)
    result = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 去掉括号内的说明性文字
        p = re.sub(r'[（(][^）)]*[）)]', '', p).strip()
        # 去掉前缀限定词：精通/熟悉/掌握/了解/熟练
        p = re.sub(r'^(精通|熟悉|掌握|了解|熟练|基础|能够|具备)', '', p).strip()
        if p and len(p) > 1:
            result.append(p)
    return result or [skill]


def normalize_skill_list(raw_skills: list) -> list:
    """将原始技能列表规范化（拆分组合、去前缀）"""
    result = []
    for s in raw_skills:
        result.extend(_split_compound(s))
    return list(dict.fromkeys(result))  # 去重保序


# ── 同义词映射（与 match_service_optimized 保持同步） ─────────────────────────

SYNONYM_PAIRS: list = [
    # IT 技术同义词
    ("关系型数据库", "MySQL"),
    ("MySQL", "关系型数据库"),
    ("缓存中间件", "Redis"),
    ("Redis", "缓存中间件"),
    ("版本管理", "Git"),
    ("Git", "版本管理"),
    ("K8s集群", "Kubernetes"),
    ("Kubernetes", "K8s集群"),
    ("前端工程化", "Webpack"),
    ("Webpack", "前端工程化"),
    ("消息队列", "Kafka"),
    ("Kafka", "消息队列"),
    ("Shell脚本", "Bash"),
    ("Bash", "Shell脚本"),
    ("Vue框架", "Vue"),
    ("Vue", "Vue框架"),
    ("微服务框架", "Spring Boot"),
    ("Spring Boot", "微服务框架"),
    ("RDBMS", "PostgreSQL"),
    # 非IT行业同义词（销售/运营/管理/HR/财务）
    ("市场开拓与客户开发", "市场开拓"),
    ("客情维护与销售", "客户关系"),
    ("客户关系维护", "客户关系"),
    ("市场调研与数据分析", "市场调研"),
    ("竞品分析与报告撰写", "竞品分析"),
    ("商务谈判与方案制定", "商务谈判"),
    ("团队管理与建设", "团队管理"),
    ("方案策划与执行", "方案策划"),
    ("销售与业务拓展", "销售技能"),
    ("沟通与演讲", "沟通表达"),
    ("办公软件及系统操作", "办公软件"),
    ("基础数据分析", "数据分析通用"),
    ("市场与行业分析", "市场调研"),
    ("客户沟通与情绪安抚", "沟通表达"),
    ("标书制作与投标流程管理", "标书投标"),
    ("销售流程与项目管理", "项目管理"),
]


def get_synonym(skill: str):
    """返回一个技能的同义词（如果存在）"""
    for a, b in SYNONYM_PAIRS:
        if a.lower() == skill.lower():
            return b
    return None


# ── 跨域技能库（用于 no_match 学生） ────────────────────────────────────────

_DOMAIN_SKILLS: dict = {
    "it_backend":  ["Java", "Spring Boot", "MySQL", "Redis", "Docker", "Maven"],
    "it_frontend": ["Vue", "React", "TypeScript", "Webpack", "HTML", "CSS"],
    "data":        ["Python", "Pandas", "TensorFlow", "SQL", "Hadoop", "Spark"],
    "devops":      ["Kubernetes", "Jenkins", "Ansible", "Linux", "Prometheus", "Nginx"],
    "marketing":   ["市场调研", "活动策划", "数据分析", "SEO优化", "内容运营", "品牌推广"],
    "product":     ["原型设计", "需求分析", "数据分析", "用户研究", "竞品分析", "Axure"],
    "finance":     ["财务分析", "Excel", "数据建模", "成本管控", "预算管理", "SAP"],
}


def _get_no_match_skills(required_skills: list) -> list:
    """选择与required_skills最不相关的域技能"""
    req_lower = {s.lower() for s in required_skills}
    best_domain = None
    best_overlap = len(required_skills) + 1
    for domain, skills in _DOMAIN_SKILLS.items():
        overlap = sum(1 for s in skills if s.lower() in req_lower)
        if overlap < best_overlap:
            best_overlap = overlap
            best_domain = domain
    return _DOMAIN_SKILLS[best_domain][:4]


# ── 主生成逻辑 ────────────────────────────────────────────────────────────────

def generate_cases_for_profile(profile: dict) -> list:
    """为单个岗位画像生成4类测试用例"""
    job_name = profile["岗位名称"]
    raw_required = profile.get("必需技能", [])
    raw_optional = profile.get("优先技能", [])
    raw_bonus = profile.get("加分技能", [])

    required = normalize_skill_list(raw_required)
    optional = normalize_skill_list(raw_optional)
    bonus = normalize_skill_list(raw_bonus)

    if not required:
        return []  # 没有必需技能的岗位跳过

    all_job_skills = required + optional[:2]  # 测试用：必需+前2个优先

    cases = []

    # ── Case 1: full_match ────────────────────────────────────────────────────
    student_full = required + optional[:2] + bonus[:1]
    cases.append({
        "job": job_name,
        "type": "full_match",
        "student_skills": student_full,
        "job_skills": all_job_skills,
        "expected_matched": all_job_skills,
        "expected_gap": [],
        "note": "学生持有全部必需+优先技能",
    })

    # ── Case 2: partial_match ─────────────────────────────────────────────────
    half = max(1, len(required) // 2)
    student_partial = required[:half]
    missing = required[half:] + optional[:1]
    cases.append({
        "job": job_name,
        "type": "partial_match",
        "student_skills": student_partial,
        "job_skills": all_job_skills,
        "expected_matched": student_partial,
        "expected_gap": missing,
        "note": f"学生只持有{half}/{len(required)}必需技能",
    })

    # ── Case 3: synonym_match ─────────────────────────────────────────────────
    syn_student = []
    syn_expected_matched = []
    for skill in required:
        syn = get_synonym(skill)
        if syn:
            syn_student.append(syn)
            syn_expected_matched.append(skill)  # 期望通过同义词命中原技能

    if syn_student:
        cases.append({
            "job": job_name,
            "type": "synonym_match",
            "student_skills": syn_student,
            "job_skills": required,
            "expected_matched": syn_expected_matched,
            "expected_gap": [s for s in required if s not in syn_expected_matched],
            "note": "学生只持有同义词，测试同义词召回",
        })

    # ── Case 4: no_match ─────────────────────────────────────────────────────
    no_match_skills = _get_no_match_skills(required)
    cases.append({
        "job": job_name,
        "type": "no_match",
        "student_skills": no_match_skills,
        "job_skills": required,
        "expected_matched": [],
        "expected_gap": required,
        "note": "学生来自不同领域，期望零匹配",
    })

    return cases


def generate_skill_pairs() -> list:
    """
    生成技能对 Ground Truth：所有 SYNONYM_PAIRS 都标记为 is_match=True，
    所有跨域具体技术对标记为 is_match=False。
    """
    pairs = []
    # 正例：同义词对
    for a, b in SYNONYM_PAIRS:
        pairs.append({"skill_a": a, "skill_b": b, "is_match": True, "reason": "synonym"})

    # 负例：编程语言之间不应互匹配
    no_cross = ["Java", "Python", "Go", "PHP", "Ruby", "Rust", "TypeScript"]
    for i, a in enumerate(no_cross):
        for b in no_cross[i+1:]:
            pairs.append({"skill_a": a, "skill_b": b, "is_match": False, "reason": "different_language"})

    # 负例：Java vs JavaScript（子串误命中）
    pairs.append({"skill_a": "Java", "skill_b": "JavaScript", "is_match": False, "reason": "substring_false_positive"})

    # 正例：通用类别名 vs 具体技术（IT）
    pairs.append({"skill_a": "后端开发", "skill_b": "Java", "is_match": True, "reason": "category_generic"})
    pairs.append({"skill_a": "前端开发", "skill_b": "Vue", "is_match": True, "reason": "category_generic"})
    pairs.append({"skill_a": "数据库", "skill_b": "MySQL", "is_match": True, "reason": "category_generic"})

    # 负例：不同领域不应互匹配（跨行业）
    pairs.append({"skill_a": "Java", "skill_b": "市场开拓", "is_match": False, "reason": "cross_industry"})
    pairs.append({"skill_a": "Python", "skill_b": "商务谈判", "is_match": False, "reason": "cross_industry"})
    pairs.append({"skill_a": "MySQL", "skill_b": "团队管理", "is_match": False, "reason": "cross_industry"})
    pairs.append({"skill_a": "React", "skill_b": "招聘", "is_match": False, "reason": "cross_industry"})

    # 正例：非IT同义词（覆盖全行业）
    non_it_positive = [
        ("市场开拓与客户开发", "市场开拓"),
        ("客情维护与销售", "客户关系"),
        ("客户关系维护", "客户关系"),
        ("市场调研与数据分析", "市场调研"),
        ("商务谈判与方案制定", "商务谈判"),
        ("团队管理与建设", "团队管理"),
        ("沟通与演讲", "沟通表达"),
        ("办公软件及系统操作", "办公软件"),
        ("基础数据分析", "数据分析通用"),
        ("销售与业务拓展", "销售技能"),
    ]
    for a, b in non_it_positive:
        pairs.append({"skill_a": a, "skill_b": b, "is_match": True, "reason": "non_it_synonym"})

    return pairs


def main():
    profiles_path = ROOT / "data" / "job_profiles.json"
    out_dir = ROOT / "data" / "eval"
    out_dir.mkdir(exist_ok=True)

    with open(profiles_path, encoding="utf-8") as f:
        profiles = json.load(f)

    # 生成技能匹配 Ground Truth
    all_cases = []
    for profile in profiles:
        all_cases.extend(generate_cases_for_profile(profile))

    cases_path = out_dir / "ground_truth.jsonl"
    with open(cases_path, "w", encoding="utf-8") as f:
        for case in all_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    # 生成技能对 Ground Truth
    pairs = generate_skill_pairs()
    pairs_path = out_dir / "skill_pairs.jsonl"
    with open(pairs_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # 汇总报告
    type_counts = {}
    for c in all_cases:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1

    print(f"Ground Truth 生成完成")
    print(f"  岗位数:       {len(profiles)}")
    print(f"  测试用例总数:  {len(all_cases)}")
    for t, n in type_counts.items():
        print(f"    {t:<20}: {n}")
    print(f"  技能对数:     {len(pairs)}")
    print(f"  输出目录:     {out_dir}")
    print(f"  文件:")
    print(f"    {cases_path.name}  ({cases_path.stat().st_size} bytes)")
    print(f"    {pairs_path.name}  ({pairs_path.stat().st_size} bytes)")

    return len(all_cases), len(pairs)


if __name__ == "__main__":
    main()
