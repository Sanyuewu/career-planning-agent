# -*- coding: utf-8 -*-
"""
准确率测试 V2 — 五个新视角

视角一：匹配分数单调性
  技能从0→部分→全部，分数必须单调递增。
  违反 = 系统存在非线性跳变，影响用户信任。

视角二：岗位排名区分度
  给定特定技能学生，正确岗位排名必须高于跨行业错误岗位。
  违反 = 推荐系统无法区分对口岗位与错误岗位。

视角三：画像推断质量
  ability_profile/竞争力/软技能推断必须在合理范围内，
  且呈现内部一致性（技能多→技能维度分高）。

视角四：鲁棒性
  空输入/超长列表/特殊字符/重复技能不应崩溃或产生异常高分。

视角五：置信度-分数相关性
  高置信度的匹配，其技能覆盖率（matched/total）应高于低置信度。
  违反 = 置信度指标失效，不具备参考价值。
"""

import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.services.match_service_optimized import OptimizedSkillMatcher
from app.services.portrait_service import PortraitService, StudentPortrait
from app.services.resume_service import ResumeParseResult

matcher = OptimizedSkillMatcher()
portrait_svc = PortraitService()

# ── 从真实岗位画像加载数据 ─────────────────────────────────────────────────────

def load_profiles():
    with open(ROOT / "data" / "job_profiles.json", encoding="utf-8") as f:
        return json.load(f)

def normalize(skills):
    """简单拆分复合技能条目"""
    import re
    result = []
    for s in skills:
        parts = re.split(r'[/、]', s)
        for p in parts:
            p = re.sub(r'^(精通|熟悉|掌握|了解|熟练|基础)', '', p.strip()).strip()
            p = re.sub(r'[（(][^）)]*[）)]', '', p).strip()
            if p and len(p) > 1:
                result.append(p)
    return result

# ─────────────────────────────────────────────────────────────────────────────
# 视角一：分数单调性
# ─────────────────────────────────────────────────────────────────────────────

def test_monotonicity():
    print("\n" + "=" * 70)
    print("视角一：匹配分数单调性（技能递增→分数递增）")
    print("=" * 70)

    profiles = load_profiles()
    violations = []
    results = []

    for p in profiles:
        job_skills = normalize(p.get('必需技能', []) + p.get('优先技能', [])[:1])
        if len(job_skills) < 2:
            continue

        # 0 技能
        r0 = matcher.match_skills([], job_skills)
        # 一半技能
        half = job_skills[:len(job_skills)//2 + 1]
        r1 = matcher.match_skills(half, job_skills)
        # 全部技能
        r2 = matcher.match_skills(job_skills, job_skills)

        score0, score1, score2 = r0.score, r1.score, r2.score
        mono = score0 <= score1 <= score2
        if not mono:
            violations.append({
                "job": p["岗位名称"],
                "scores": (round(score0,2), round(score1,2), round(score2,2)),
                "issue": f"{'0>half' if score0>score1 else 'half>full'}",
            })
        results.append({
            "job": p["岗位名称"],
            "industry": p.get("行业分类", "?"),
            "scores": (round(score0,2), round(score1,2), round(score2,2)),
            "mono": mono,
        })

    pass_n = sum(1 for r in results if r["mono"])
    rate = pass_n / len(results) if results else 0

    print(f"\n  测试岗位数: {len(results)}")
    print(f"  单调性通过: {pass_n}/{len(results)}  ({rate:.1%})")

    if violations:
        print(f"\n  ⚠️  违反单调性的岗位 ({len(violations)} 个)：")
        for v in violations[:5]:
            print(f"    {v['job']}: 0技能={v['scores'][0]}, 半技能={v['scores'][1]}, 全技能={v['scores'][2]}  [{v['issue']}]")
    else:
        print("  ✅ 所有岗位单调性通过")

    # 全技能分数分布
    full_scores = [r["scores"][2] for r in results]
    print(f"\n  全技能匹配分数分布：")
    print(f"    最低={min(full_scores):.2f}  最高={max(full_scores):.2f}  均值={sum(full_scores)/len(full_scores):.2f}")
    low_ceiling = [r for r in results if r["scores"][2] < 0.7]
    if low_ceiling:
        print(f"  ⚠️  全技能匹配仍低于0.7的岗位 ({len(low_ceiling)} 个，可能岗位技能描述过于模糊)：")
        for r in low_ceiling[:3]:
            print(f"    {r['job']} [{r['industry']}]: 全技能={r['scores'][2]}")

    return rate, len(violations)


# ─────────────────────────────────────────────────────────────────────────────
# 视角二：岗位排名区分度
# ─────────────────────────────────────────────────────────────────────────────

# 定义「学生+正确岗位+错误岗位」三元组
# 学生技能 = 正确岗位的必需技能（规范化后），确保必然匹配
# 错误岗位 = 跨行业岗位，不应有重叠
RANKING_CASES = [
    {
        "name": "Java后端学生",
        # Java岗: 必需=['Java开发','数据库操作与优化']
        "student_skills": ["Java", "MySQL", "Spring Boot", "Redis"],
        "correct_jobs": ["Java"],
        "wrong_jobs": ["BD经理", "招聘专员/助理", "培训师"],
    },
    {
        "name": "前端开发学生",
        # 前端开发: 必需=['HTML/CSS/JavaScript', 'Vue/React框架']
        "student_skills": ["HTML", "CSS", "JavaScript", "Vue", "React"],
        "correct_jobs": ["前端开发"],
        "wrong_jobs": ["BD经理", "培训师", "法务专员/助理"],
    },
    {
        "name": "BD销售学生",
        # BD经理: 必需=['市场开拓与客户开发','商务谈判与方案制定']
        "student_skills": ["市场开拓与客户开发", "商务谈判与方案制定", "销售流程与项目管理"],
        "correct_jobs": ["BD经理"],
        "wrong_jobs": ["Java", "前端开发", "招聘专员/助理"],
    },
    {
        "name": "HR招聘学生",
        # 招聘专员/助理 — 看其必需技能
        "student_skills": ["招聘", "人才招募", "面试", "简历筛选", "沟通表达"],
        "correct_jobs": ["招聘专员/助理"],
        "wrong_jobs": ["Java", "前端开发", "BD经理"],
    },
    {
        "name": "运营学生",
        # 运营助理/专员 — 看其必需技能
        "student_skills": ["内容运营", "用户运营", "数据分析通用", "方案策划与执行"],
        "correct_jobs": ["运营助理/专员"],
        "wrong_jobs": ["Java", "法务专员/助理", "培训师"],
    },
    {
        "name": "C/C++嵌入式学生",
        # C/C++: 必需=['精通C/C++编程语言','熟悉嵌入式开发/操作系统/网络协议']
        "student_skills": ["C/C++", "嵌入式开发", "操作系统", "网络协议"],
        "correct_jobs": ["C/C++"],
        "wrong_jobs": ["BD经理", "招聘专员/助理", "运营助理/专员"],
    },
]


def test_job_ranking():
    print("\n" + "=" * 70)
    print("视角二：岗位排名区分度（正确岗位 > 错误岗位）")
    print("=" * 70)

    profiles = load_profiles()
    job_skill_map = {}
    for p in profiles:
        skills = normalize(p.get('必需技能', []) + p.get('优先技能', []))
        job_skill_map[p['岗位名称']] = skills

    total_pairs = 0
    pass_pairs = 0
    case_results = []

    print(f"\n  {'学生类型':<15} {'正确岗位':<20} {'错误岗位':<20} {'正确分':>6} {'错误分':>6} {'通过'}")
    print("  " + "-" * 78)

    for case in RANKING_CASES:
        student = case["student_skills"]
        case_pass = True

        for correct_job in case["correct_jobs"]:
            cskills = job_skill_map.get(correct_job, [])
            if not cskills:
                continue
            r_correct = matcher.match_skills(student, cskills)

            for wrong_job in case["wrong_jobs"]:
                wskills = job_skill_map.get(wrong_job, [])
                if not wskills:
                    continue
                r_wrong = matcher.match_skills(student, wskills)

                passed = r_correct.score > r_wrong.score
                total_pairs += 1
                if passed:
                    pass_pairs += 1
                else:
                    case_pass = False

                flag = "✅" if passed else "❌"
                print(f"  {case['name']:<15} {correct_job:<20} {wrong_job:<20} {r_correct.score:>6.2f} {r_wrong.score:>6.2f} {flag}")

        case_results.append({"name": case["name"], "pass": case_pass})

    rate = pass_pairs / total_pairs if total_pairs else 0
    print(f"\n  总对比对数: {total_pairs}  通过: {pass_pairs}  区分度: {rate:.1%}")

    if rate < 1.0:
        fail_cases = [c["name"] for c in case_results if not c["pass"]]
        print(f"  ⚠️  排名不正确的学生类型: {fail_cases}")

    return rate


# ─────────────────────────────────────────────────────────────────────────────
# 视角三：画像推断质量
# ─────────────────────────────────────────────────────────────────────────────

def make_parse_result(**kwargs) -> ResumeParseResult:
    defaults = dict(
        basic_info={"name": "测试学生", "school": "北京大学", "major": "计算机科学", "grade": "大四"},
        education=[{"degree": "本科", "school": "北京大学", "major": "计算机科学", "gpa": 3.5}],
        skills=[], internships=[], projects=[], certs=[], awards=[],
        career_intent="后端开发工程师",
        # inferred_soft_skills 格式：{维度名: {"score": int}} 或 {}
        inferred_soft_skills={"学习能力": {"score": 80}, "沟通能力": {"score": 70}, "抗压能力": {"score": 75}},
        completeness=0.8,
        raw_text="",
    )
    defaults.update(kwargs)
    return ResumeParseResult(**defaults)


PORTRAIT_CASES = [
    {
        "name": "顶配学生（技能多+实习+985）",
        "skills": ["Python", "Java", "MySQL", "Redis", "Docker", "Spring Boot", "TensorFlow"],
        "internships": [{"company": "阿里巴巴", "duration_months": 6}, {"company": "腾讯", "duration_months": 3}],
        "school": "清华大学",
        "expected": {
            # 无项目/奖证，顶配上限约 60-75；有实习+985+7技能 → 应 ≥ 普通学生
            "competitiveness": (50, 100),
            "level": ("A", "B", "C"),      # 允许C，关键是高于普通
            "ability_skill_min": 60,        # 技术能力维度应 ≥ 60
        },
    },
    {
        "name": "普通学生（技能少+无实习）",
        "skills": ["Python", "MySQL"],
        "internships": [],
        "school": "普通二本",
        "expected": {
            "competitiveness": (0, 50),
            "level": ("C", "D"),
            "ability_skill_min": 0,
        },
    },
    {
        "name": "非IT学生（软技能+无编程）",
        "skills": ["市场调研", "商务谈判", "办公软件", "沟通表达"],
        "internships": [{"company": "某销售公司", "duration_months": 3}],
        "school": "普通一本",
        "expected": {
            "completeness_min": 0.4,
            "ability_no_negative": True,
        },
    },
]


def test_portrait_quality():
    print("\n" + "=" * 70)
    print("视角三：画像推断质量（合理性 + 内部一致性）")
    print("=" * 70)

    total = 0
    passed = 0
    issues = []

    for case in PORTRAIT_CASES:
        pr = make_parse_result(
            skills=case["skills"],
            internships=case.get("internships", []),
            basic_info={"name": "测试", "school": case.get("school", "普通大学"), "major": "计算机科学"},
        )
        portrait = portrait_svc.build_portrait(pr)

        total += 1
        case_ok = True
        case_issues = []

        exp = case.get("expected", {})

        # 竞争力范围
        if "competitiveness" in exp:
            lo, hi = exp["competitiveness"]
            if not (lo <= portrait.competitiveness <= hi):
                case_issues.append(f"竞争力={portrait.competitiveness:.1f}，期望[{lo},{hi}]")
                case_ok = False

        # 竞争力等级
        if "level" in exp:
            levels = exp["level"]
            if portrait.competitiveness_level not in levels:
                case_issues.append(f"等级={portrait.competitiveness_level}，期望{levels}")
                case_ok = False

        # ability_profile 技能维度（key 可能是"技术能力"/"专业技能"/"skill"）
        if "ability_skill_min" in exp:
            skill_score = (portrait.ability_profile.get("技术能力")
                           or portrait.ability_profile.get("专业技能")
                           or portrait.ability_profile.get("skill", 0))
            if skill_score < exp["ability_skill_min"]:
                case_issues.append(f"技能维度={skill_score:.1f}<{exp['ability_skill_min']}")
                case_ok = False

        # 无负数
        if exp.get("ability_no_negative"):
            negatives = {k: v for k, v in portrait.ability_profile.items() if v < 0}
            if negatives:
                case_issues.append(f"ability_profile含负数: {negatives}")
                case_ok = False

        # ability_profile 所有值在 [0,100]
        for k, v in portrait.ability_profile.items():
            if not (0 <= v <= 100):
                case_issues.append(f"ability_profile[{k}]={v}超范围")
                case_ok = False

        # field_confidence 所有值在 [0,1]
        for k, v in portrait.field_confidence.items():
            if not (0 <= v <= 1):
                case_issues.append(f"field_confidence[{k}]={v}超范围")
                case_ok = False

        if case_ok:
            passed += 1
            flag = "✅"
        else:
            flag = "❌"
            issues.append({"name": case["name"], "issues": case_issues})

        print(f"\n  {flag} {case['name']}")
        print(f"     竞争力={portrait.competitiveness:.1f}  等级={portrait.competitiveness_level}")
        ap = portrait.ability_profile
        if ap:
            print(f"     能力雷达: {', '.join(f'{k}={v:.0f}' for k,v in list(ap.items())[:5])}")
        fc = portrait.field_confidence
        if fc:
            low_fields = {k: round(v,2) for k,v in fc.items() if v < 0.75}
            print(f"     低置信字段: {low_fields if low_fields else '无'}")
        if case_issues:
            for issue in case_issues:
                print(f"     ⚠️  {issue}")

    rate = passed / total if total else 0
    print(f"\n  通过: {passed}/{total}  ({rate:.1%})")
    return rate


# ─────────────────────────────────────────────────────────────────────────────
# 视角四：鲁棒性
# ─────────────────────────────────────────────────────────────────────────────

ROBUSTNESS_CASES = [
    {"name": "空学生技能",         "student": [],          "job": ["Python", "MySQL"]},
    {"name": "空岗位技能",         "student": ["Python"],  "job": []},
    {"name": "双空",               "student": [],          "job": []},
    {"name": "单技能完全匹配",     "student": ["Python"],  "job": ["Python"]},
    {"name": "50个重复技能",       "student": ["Python"]*50, "job": ["Python", "MySQL"]},
    {"name": "特殊字符技能",       "student": ["C++", "C#", "Node.js", "ASP.NET"], "job": ["C++", "Node.js"]},
    {"name": "超长技能名",         "student": ["熟练使用Python进行数据分析和机器学习建模工作"], "job": ["Python"]},
    {"name": "纯数字技能",         "student": ["2023", "123"],  "job": ["Python"]},
    {"name": "全是非IT通用技能",   "student": ["市场开拓", "客户关系", "商务谈判"], "job": ["市场开拓与客户开发"]},
    {"name": "混合IT+非IT",       "student": ["Python", "市场调研", "MySQL", "商务谈判"], "job": ["Python", "市场调研"]},
]


def test_robustness():
    print("\n" + "=" * 70)
    print("视角四：鲁棒性（异常输入不崩溃，输出在合理范围）")
    print("=" * 70)

    total = 0
    passed = 0
    print(f"\n  {'用例':<25} {'学生→岗位':>5} {'score':>7} {'conf':>7} {'matched':>8}  结果")
    print("  " + "-" * 70)

    for case in ROBUSTNESS_CASES:
        total += 1
        try:
            r = matcher.match_skills(case["student"], case["job"])
            # score 范围 0-100，confidence 范围 0-1
            score_ok  = 0.0 <= r.score <= 100.0
            conf_ok   = 0.0 <= r.confidence <= 1.0
            matched_ok = isinstance(r.matched_skills, list)
            gap_ok     = isinstance(r.gap_skills, list)
            # 空岗位 → score=100 是合理行为（无要求=全满足），不算异常
            # 但空学生+有岗位 → score=0 才合理
            semantic_ok = True
            if not case["job"] and r.score > 100:
                semantic_ok = False
            if not case["student"] and case["job"] and r.score > 5:
                semantic_ok = False  # 空学生不应得高分

            case_ok = score_ok and conf_ok and matched_ok and gap_ok and semantic_ok
            flag = "✅" if case_ok else "❌"
            issue = ""
            if not score_ok:   issue += f" score={r.score:.1f}超范围"
            if not conf_ok:    issue += f" conf={r.confidence:.2f}超范围"
            if not semantic_ok: issue += f" 语义异常(score={r.score:.1f})"
            print(f"  {flag} {case['name']:<25} {len(case['student'])}→{len(case['job'])}  {r.score:>7.1f} {r.confidence:>7.3f} {str(r.matched_skills)[:18]}{issue}")
            if case_ok:
                passed += 1
        except Exception as e:
            print(f"  ❌ {case['name']:<25} 崩溃: {type(e).__name__}: {e}")

    rate = passed / total if total else 0
    print(f"\n  通过: {passed}/{total}  ({rate:.1%})")
    return rate


# ─────────────────────────────────────────────────────────────────────────────
# 视角五：置信度-覆盖率相关性
# ─────────────────────────────────────────────────────────────────────────────

def test_confidence_correlation():
    print("\n" + "=" * 70)
    print("视角五：置信度-技能覆盖率相关性（高置信度→高覆盖率）")
    print("=" * 70)

    profiles = load_profiles()
    records = []

    for p in profiles:
        job_skills = normalize(p.get('必需技能', []) + p.get('优先技能', []))
        if len(job_skills) < 2:
            continue
        for n in [0, len(job_skills)//3, 2*len(job_skills)//3, len(job_skills)]:
            student = job_skills[:n]
            r = matcher.match_skills(student, job_skills)
            coverage = n / len(job_skills)
            records.append({
                "job": p["岗位名称"],
                "coverage": coverage,
                "confidence": r.confidence,
                "score": r.score,
                "matched_n": len(r.matched_skills),
            })

    # 按置信度分桶，看每桶的平均覆盖率
    high = [r for r in records if r["confidence"] >= 0.8]
    mid  = [r for r in records if 0.6 <= r["confidence"] < 0.8]
    low  = [r for r in records if r["confidence"] < 0.6]

    def avg(lst, key): return sum(x[key] for x in lst) / len(lst) if lst else 0

    print(f"\n  置信度桶    样本数   均覆盖率   均得分")
    print("  " + "-" * 40)
    print(f"  高(≥0.8)  {len(high):>6}   {avg(high,'coverage'):>8.1%}  {avg(high,'score'):>7.3f}")
    print(f"  中(0.6-0.8){len(mid):>5}   {avg(mid,'coverage'):>8.1%}  {avg(mid,'score'):>7.3f}")
    print(f"  低(<0.6)  {len(low):>6}   {avg(low,'coverage'):>8.1%}  {avg(low,'score'):>7.3f}")

    # 相关性判断：高桶覆盖率 > 中桶 > 低桶
    mono = avg(high, "coverage") >= avg(mid, "coverage") >= avg(low, "coverage")

    # Spearman相关（简单实现）
    scores = [r["confidence"] for r in records]
    coverages = [r["coverage"] for r in records]
    n = len(scores)
    mean_s = sum(scores)/n
    mean_c = sum(coverages)/n
    cov = sum((s-mean_s)*(c-mean_c) for s,c in zip(scores, coverages))
    std_s = (sum((s-mean_s)**2 for s in scores)/n)**0.5
    std_c = (sum((c-mean_c)**2 for c in coverages)/n)**0.5
    pearson = cov / (n * std_s * std_c) if std_s * std_c > 0 else 0

    print(f"\n  置信度与覆盖率 Pearson 相关系数: {pearson:.3f}")
    print(f"  桶间单调性: {'✅' if mono else '⚠️ 不单调'}")

    if pearson >= 0.5:
        print(f"  ✅ 置信度指标有效（强正相关）")
        quality = "strong"
    elif pearson >= 0.2:
        print(f"  ⚠️  置信度指标弱相关，仅供参考")
        quality = "weak"
    else:
        print(f"  ❌ 置信度与覆盖率无明显相关，指标可能失效")
        quality = "invalid"

    return pearson, quality


# ─────────────────────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("█" * 70)
    print("  准确率测试 V2 — 五视角全面评估")
    print(f"  测试时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("█" * 70)

    t0 = time.time()

    mono_rate, mono_violations = test_monotonicity()
    ranking_rate = test_job_ranking()
    portrait_rate = test_portrait_quality()
    robust_rate = test_robustness()
    pearson, conf_quality = test_confidence_correlation()

    elapsed = time.time() - t0

    print("\n" + "=" * 70)
    print("  最终汇总")
    print("=" * 70)
    rows = [
        ("分数单调性",     mono_rate,    0.95, f"{mono_violations}个违反"),
        ("岗位区分度",     ranking_rate, 0.90, "正确岗位>错误岗位"),
        ("画像推断质量",   portrait_rate,0.85, "合理范围+内部一致"),
        ("鲁棒性",         robust_rate,  1.00, "异常输入不崩溃"),
        ("置信度有效性",   min(max(pearson, 0), 1), 0.50, f"Pearson={pearson:.3f} ({conf_quality})"),
    ]
    all_pass = True
    for label, score, threshold, note in rows:
        ok = score >= threshold
        if not ok:
            all_pass = False
        flag = "✅" if ok else "❌"
        print(f"  {flag} {label:<15} {score:>6.1%}  (阈值{threshold:.0%})  {note}")

    print(f"\n  总耗时: {elapsed:.1f}s")
    if all_pass:
        print("\n  🎉 五个视角全部达标")
    else:
        print("\n  ⚠️  存在未达标视角，见上方详情")


if __name__ == "__main__":
    main()
