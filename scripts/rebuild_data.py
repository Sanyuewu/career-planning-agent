#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从真实 XLS 数据重建 job_profiles.json 和 job_graph.json
用法：python scripts/rebuild_data.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
XLS_PATH   = ROOT / "20260226105856_457.xls"
PROFILES_PATH = ROOT / "data" / "job_profiles.json"
GRAPH_PATH    = ROOT / "data" / "job_graph.json"

# ──────────────────────────────────────────────────────────────────────────────
# 1. 解析 XLS → 每个岗位的真实统计
# ──────────────────────────────────────────────────────────────────────────────

def parse_xls(xls_path: Path) -> dict:
    """返回 {岗位名称: {count, salaries, industries, jd_samples}}"""
    import xlrd
    wb = xlrd.open_workbook(str(xls_path), encoding_override="gbk")
    sh = wb.sheet_by_index(0)
    headers = [sh.cell_value(0, i) for i in range(sh.ncols)]

    stats = defaultdict(lambda: {
        "count": 0,
        "salaries": [],
        "industries": [],
        "jd_samples": [],
        "company_types": [],
    })

    for r in range(1, sh.nrows):
        row = {headers[i]: sh.cell_value(r, i) for i in range(sh.ncols)}
        name = row.get("岗位名称", "").strip()
        if not name:
            continue
        s = stats[name]
        s["count"] += 1
        sal = row.get("薪资范围", "").strip()
        if sal:
            s["salaries"].append(sal)
        ind = row.get("所属行业", "").strip()
        if ind:
            s["industries"].append(ind)
        jd = row.get("岗位详情", "").strip()
        if jd and len(s["jd_samples"]) < 5:
            clean = re.sub(r"<[^>]+>", " ", jd).strip()[:300]
            s["jd_samples"].append(clean)
        ct = row.get("公司类型", "").strip()
        if ct:
            s["company_types"].append(ct)

    return dict(stats)


def dominant_salary(salaries: list) -> str:
    """取出现次数最多的薪资区间"""
    if not salaries:
        return ""
    from collections import Counter
    return Counter(salaries).most_common(1)[0][0]


def dominant_industry(industries: list) -> str:
    """取主行业（第一个逗号前）"""
    if not industries:
        return ""
    from collections import Counter
    primary = [i.split(",")[0].strip() for i in industries if i]
    return Counter(primary).most_common(1)[0][0] if primary else ""


# ──────────────────────────────────────────────────────────────────────────────
# 2. 清洗 job_profiles.json
# ──────────────────────────────────────────────────────────────────────────────

def clean_profiles(profiles: list, xls_stats: dict) -> list:
    """移除合成重复条目，用真实 XLS 数据更新统计字段"""
    real = [p for p in profiles if not re.search(r"\(\d+\)$", p["岗位名称"])]
    print(f"  保留真实条目: {len(real)} 个（移除 {len(profiles)-len(real)} 个合成重复）")

    for p in real:
        name = p["岗位名称"]
        stats = xls_stats.get(name)
        if not stats:
            continue
        # 更新真实 JD 总数
        p["total_jd_count"] = stats["count"]
        # 更新薪资（优先用真实数据）
        real_sal = dominant_salary(stats["salaries"])
        if real_sal:
            p["薪资范围"] = real_sal
        # 更新所属行业（优先用真实数据）
        real_ind = dominant_industry(stats["industries"])
        if real_ind:
            p["所属行业"] = real_ind
        # 更新市场热度（按 JD 数量归一化到 1-10）
        p["市场热度"] = min(10, max(1, round(stats["count"] / 100)))

    return real


# ──────────────────────────────────────────────────────────────────────────────
# 3. 重建 job_graph.json
# ──────────────────────────────────────────────────────────────────────────────

def build_graph(profiles: list) -> dict:
    """
    从 job_profiles 生成 job_graph.json 格式的图谱数据。
    节点 ID 格式：job_{岗位名称} / skill_{技能名}
    """
    nodes = {}   # id -> attrs dict
    edges = []   # list of {from, to, props}
    skill_names = set()

    for profile in profiles:
        job_name = profile["岗位名称"]
        job_id   = f"job_{job_name}"

        # ── 岗位节点 ──────────────────────────────────────────────────────────
        nodes[job_id] = {
            "node_type": "Job",
            "title": job_name,
            "overview": profile.get("岗位概述", ""),
            "industry": profile.get("所属行业", ""),
            "industry_category": profile.get("行业分类", ""),
            "salary": profile.get("薪资范围", ""),
            "skills": profile.get("专业技能", []),
            "required_skills": profile.get("必需技能", []),
            "preferred_skills": profile.get("优先技能", []),
            "bonus_skills": profile.get("加分技能", []),
            "certs": profile.get("证书要求", []),
            "tags": profile.get("岗位标签", []),
            "market_heat": profile.get("市场热度", 5),
            "total_jd_count": profile.get("total_jd_count", 0),
            # 学历/专业要求（供 match_service._score_basic() 使用）
            "education_level": profile.get("education_level", "本科"),
            "majors": profile.get("majors", []),
            # 地区分布 + 团队文化（从真实JD数据提取）
            "top_regions": profile.get("top_regions", []),
            "culture_types": profile.get("culture_types", []),
            "top_companies": profile.get("top_companies", []),
            # 七维能力字段（赛题要求）
            "creativity": profile.get("创新能力", ""),
            "learning": profile.get("学习能力", ""),
            "stress_resistance": profile.get("抗压能力", ""),
            "communication": profile.get("沟通能力", ""),
            "internship": profile.get("实习经历", ""),
        }

        # ── 技能节点 + REQUIRES 边 ────────────────────────────────────────────
        all_skills = (
            profile.get("必需技能", []) +
            profile.get("优先技能", []) +
            profile.get("加分技能", [])
        )
        for skill in all_skills:
            sid = f"skill_{skill}"
            if sid not in nodes:
                nodes[sid] = {"node_type": "Skill", "name": skill}
            is_must = skill in profile.get("必需技能", [])
            edges.append({
                "from": job_id,
                "to": sid,
                "props": {
                    "edge_type": "REQUIRES",
                    "weight": 1.0,
                    "is_must": is_must,
                },
            })
            skill_names.add(skill)

        # ── 垂直晋升路径 PROMOTES_TO ──────────────────────────────────────────
        prev_id = job_id
        for step in profile.get("垂直晋升路径", []):
            target_name = step.get("岗位", "")
            if not target_name or target_name == job_name:
                continue
            target_id = f"job_{target_name}"
            if target_id not in nodes:
                nodes[target_id] = {
                    "node_type": "Job",
                    "title": target_name,
                    "overview": step.get("描述", ""),
                    "industry": profile.get("所属行业", ""),
                    "industry_category": profile.get("行业分类", ""),
                    "salary": "",
                    "skills": [],
                    "required_skills": [],
                    "preferred_skills": [],
                    "bonus_skills": [],
                    "certs": [],
                    "tags": [],
                    "market_heat": 5,
                    "total_jd_count": 0,
                    "creativity": "",
                    "learning": "",
                    "stress_resistance": "",
                    "communication": "",
                    "internship": "",
                }
            edges.append({
                "from": prev_id,
                "to": target_id,
                "props": {
                    "edge_type": "PROMOTES_TO",
                    "level": step.get("层级", 0),
                    "years": step.get("年限", ""),
                    "description": step.get("描述", ""),
                },
            })
            prev_id = target_id

        # ── 换岗路径 CAN_TRANSFER_TO ─────────────────────────────────────────
        for hp in profile.get("横向换岗路径", []):
            target_name = hp.get("目标岗位", "")
            if not target_name:
                continue
            target_id = f"job_{target_name}"
            if target_id not in nodes:
                nodes[target_id] = {
                    "node_type": "Job",
                    "title": target_name,
                    "overview": "",
                    "industry": "",
                    "industry_category": "",
                    "salary": "",
                    "skills": [],
                    "required_skills": [],
                    "preferred_skills": [],
                    "bonus_skills": [],
                    "certs": [],
                    "tags": [],
                    "market_heat": 5,
                    "total_jd_count": 0,
                    "creativity": "",
                    "learning": "",
                    "stress_resistance": "",
                    "communication": "",
                    "internship": "",
                }
            match_level = hp.get("匹配度", "中")
            overlap = {"高": 0.8, "中": 0.5, "低": 0.3}.get(match_level, 0.5)
            edges.append({
                "from": job_id,
                "to": target_id,
                "props": {
                    "edge_type": "CAN_TRANSFER_TO",
                    "match_level": match_level,
                    "overlap_pct": overlap,
                    "advantage": hp.get("迁移优势", ""),
                    "need_learn": hp.get("需补足", ""),
                },
            })

    # ── 技能相似度 SIMILAR_TO 边（同岗位技能互联）──────────────────────────
    # 简单规则：同一岗位的 must_have 技能彼此 SIMILAR_TO
    skill_cooccur = defaultdict(set)
    for e in edges:
        if e["props"]["edge_type"] == "REQUIRES" and e["props"]["is_must"]:
            job = e["from"]
            skill = e["to"]
            skill_cooccur[job].add(skill)

    seen_pairs = set()
    for job, skills in skill_cooccur.items():
        skill_list = sorted(skills)
        for i, s1 in enumerate(skill_list):
            for s2 in skill_list[i+1:]:
                pair = (min(s1,s2), max(s1,s2))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    edges.append({
                        "from": s1,
                        "to": s2,
                        "props": {"edge_type": "SIMILAR_TO", "weight": 0.7},
                    })
                    edges.append({
                        "from": s2,
                        "to": s1,
                        "props": {"edge_type": "SIMILAR_TO", "weight": 0.7},
                    })

    node_list = [{"id": nid, "attrs": attrs} for nid, attrs in nodes.items()]
    return {
        "nodes": node_list,
        "edges": edges,
        "metadata": {
            "total_jobs": len([n for n in node_list if n["attrs"].get("node_type") == "Job"]),
            "total_skills": len([n for n in node_list if n["attrs"].get("node_type") == "Skill"]),
            "total_edges": len(edges),
            "source": "rebuilt_from_xls",
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=== Step 1: 解析 XLS 真实数据 ===")
    xls_stats = parse_xls(XLS_PATH)
    print(f"  XLS 岗位数: {len(xls_stats)}, 总 JD 条数: {sum(v['count'] for v in xls_stats.values())}")

    print("\n=== Step 2: 清洗 job_profiles.json ===")
    with open(PROFILES_PATH, encoding="utf-8") as f:
        profiles = json.load(f)
    clean = clean_profiles(profiles, xls_stats)

    # 写回
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"  已写入 {PROFILES_PATH}（{len(clean)} 个岗位）")

    print("\n=== Step 3: 重建 job_graph.json ===")
    graph = build_graph(clean)
    job_nodes = [n for n in graph["nodes"] if n["attrs"].get("node_type") == "Job"]
    skill_nodes = [n for n in graph["nodes"] if n["attrs"].get("node_type") == "Skill"]
    jobs_with_overview = [n for n in job_nodes if n["attrs"].get("overview")]

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"  岗位节点: {len(job_nodes)}（有 overview: {len(jobs_with_overview)}）")
    print(f"  技能节点: {len(skill_nodes)}")
    print(f"  总边数:   {len(graph['edges'])}")
    print(f"  已写入 {GRAPH_PATH}")

    print("\n=== 验证：可选岗位列表（前20） ===")
    sys.path.insert(0, str(ROOT))
    # 重新加载图谱验证
    from importlib import import_module
    import importlib
    import app.graph.job_graph_repo as mod
    importlib.reload(mod)
    repo = mod.JobGraphRepo()
    valid = repo.get_valid_jobs()
    print(f"  get_valid_jobs() 返回: {len(valid)} 个岗位")
    print("  前20:", valid[:20])

    print("\n✅ 完成")


if __name__ == "__main__":
    main()
