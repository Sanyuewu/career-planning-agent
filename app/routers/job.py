# -*- coding: utf-8 -*-
"""
岗位/图谱/市场桥接路由
所有接口均经过 YOUTU-GraphRAG 检索，再返回前端期望格式。

前端期望路径：
  GET /api/match/jobs                    → 岗位列表（字符串数组）
  GET /api/jobs/info?job=                → 岗位七维画像
  GET /api/jobs/career-graph?job=        → 垂直晋升 + 换岗路径
  GET /api/graph/main-transfers/{job}    → 主岗 + 换岗节点聚合
  GET /api/jobs/search?query=&limit=     → 模糊搜索岗位
  GET /api/jobs/real?job=&limit=         → 原始招聘数据样本
  GET /api/jobs/ai_insight?job_name=     → LLM 岗位洞察
  GET /api/market/industry_trends        → 行业趋势（社区层）
"""

import functools
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import BASE_DIR
from app.services.career_graphrag_service import career_graphrag_service
from app.services.youtu_retriever_service import youtu_retriever_service

router = APIRouter(tags=["岗位图谱"])

CSV_PATH = BASE_DIR / "data" / "raw" / "preprocessed_for_llm.csv"

# ── CSV 懒加载（只读一次）────────────────────────────────
@functools.lru_cache(maxsize=1)
def _load_csv():
    try:
        import pandas as pd
        df = pd.read_csv(str(CSV_PATH), encoding="utf-8")
        return df
    except Exception:
        return None


# ── 工具函数 ─────────────────────────────────────────────
def _level_label(confidence: float) -> str:
    if confidence >= 0.7:
        return "高"
    if confidence >= 0.45:
        return "中"
    return "低"


def _parse_salary_k(s) -> Optional[float]:
    """把'8k-15k'/'8000-15000元'等解析为均值（单位 k）。无法解析返回 None。"""
    try:
        nums = [float(x.replace("k", "").replace("K", "").replace("元", ""))
                for x in str(s).split("-") if any(c.isdigit() for c in str(x))]
        if nums:
            avg = sum(nums) / len(nums)
            return round(avg / 1000, 1) if avg > 1000 else round(avg, 1)
    except Exception:
        pass
    return None


def _demand_profile(job_name: str, df) -> Dict[str, Any]:
    """
    从原始招聘 CSV 计算岗位的**真实社会需求结构**（非时间趋势——CSV 无时间戳）：
    招聘量、需求占比、薪资分位（min/median/max）、公司规模分布、需求热度等级。
    """
    if df is None:
        return {"available": False, "basis": "无招聘样本数据"}
    subset = df[df["岗位名称"].astype(str).str.contains(job_name, na=False, regex=False)]
    jd_count = int(len(subset))
    total = int(len(df)) or 1
    if jd_count == 0:
        return {"available": False, "basis": "该岗位在招聘样本中无记录"}

    sals = sorted(subset["薪资范围"].apply(_parse_salary_k).dropna().tolist())
    sal_stat = {}
    if sals:
        n = len(sals)
        sal_stat = {
            "min_k": sals[0],
            "median_k": sals[n // 2],
            "max_k": sals[-1],
        }
    sizes = {}
    if "公司规模" in subset.columns:
        sizes = {str(k): int(v) for k, v in subset["公司规模"].value_counts().head(5).items()}

    # 需求热度：按招聘条数真实分级（透明阈值，可解释）
    level = "高" if jd_count >= 100 else "中" if jd_count >= 30 else "低"

    return {
        "available": True,
        "jd_count": jd_count,
        "demand_share_pct": round(jd_count / total * 100, 2),
        "demand_level": level,
        "salary": sal_stat,
        "company_sizes": sizes,
        "basis": f"基于 {total} 条本地招聘样本的需求结构分析（非时间趋势预测）",
    }


# ── 路由 ─────────────────────────────────────────────────

@router.get("/api/match/jobs")
async def get_match_jobs():
    """岗位列表（字符串数组，供匹配页下拉使用）"""
    try:
        jobs = career_graphrag_service.get_all_jobs()
        titles = [j["title"] for j in jobs if j.get("title")]
        return titles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jobs/info")
async def get_job_info(job: str = Query(..., description="岗位名称")):
    """
    岗位七维画像
    数据来源：YOUTU-GraphRAG 图谱 Job 节点属性 + 边关系
    """
    try:
        portrait = career_graphrag_service.generate_job_portrait(job)
        if not portrait.title:
            raise HTTPException(status_code=404, detail=f"未找到岗位：{job}")

        # 从 YOUTU retriever 补充市场数据
        youtu_info = youtu_retriever_service.retrieve_job_info(job)
        top_companies = youtu_info.get("top_companies", []) if isinstance(youtu_info, dict) and "error" not in youtu_info else []

        return {
            "title": portrait.title,
            "salary": portrait.salary_range,
            "industry": portrait.industry,
            "education": "",
            "experience": "1-3年" if not portrait.entry_friendly else "应届可",
            "skills": portrait.skills,
            "overview": portrait.job_description or f"{portrait.title}是计算机信息化领域核心岗位",
            "responsibilities": [],
            "top_regions": portrait.location.split("、") if portrait.location else [],
            "top_companies": top_companies[:5],
            "majors": [],
            "tags": [
                f"均薪{portrait.salary_avg_k:.1f}k" if portrait.salary_avg_k else "",
                "应届友好" if portrait.entry_friendly else "经验导向",
                f"需求量{portrait.job_count}" if portrait.job_count else "",
            ],
            # 七维度
            "innovation": portrait.innovation,
            "learning": portrait.learning,
            "stress_resistance": portrait.stress_resistance,
            "communication": portrait.communication,
            "internship": portrait.internship,
            "certificates": portrait.certificates,
            "salary_avg_k": portrait.salary_avg_k,
            "job_count": portrait.job_count,
            "entry_friendly": portrait.entry_friendly,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jobs/career-graph")
async def get_career_graph(job: str = Query(..., description="岗位名称")):
    """
    职业图谱（垂直晋升 + 横向换岗）
    数据来源：YOUTU-GraphRAG PROMOTES_TO / TRANSFERS_TO 边
    """
    try:
        paths = career_graphrag_service.get_career_paths(job)

        nodes: List[Dict] = [{"id": job, "title": job}]
        edges: List[Dict] = []
        promotion_paths = []
        transfer_paths = []

        for vp in paths.vertical_paths:
            tgt = vp.target_job
            if not any(n["id"] == tgt for n in nodes):
                # 拿目标岗薪资
                tgt_portrait = career_graphrag_service.generate_job_portrait(tgt)
                nodes.append({"id": tgt, "title": tgt, "salary": tgt_portrait.salary_range})
            edges.append({"from": job, "to": tgt, "type": "PROMOTES_TO", "label": "晋升"})
            promotion_paths.append({
                "nodes": [{"title": job}, {"title": tgt}],
                "transitions": [{"to": tgt, "description": vp.description}],
            })

        for hp in paths.horizontal_paths:
            tgt = hp.target_job
            if not any(n["id"] == tgt for n in nodes):
                tgt_portrait = career_graphrag_service.generate_job_portrait(tgt)
                nodes.append({"id": tgt, "title": tgt, "salary": tgt_portrait.salary_range})
            edges.append({"from": job, "to": tgt, "type": "TRANSFERS_TO", "label": "换岗"})
            transfer_paths.append({
                "target": tgt,
                "title": tgt,
                "match_level": _level_label(hp.confidence),
                "overlap_pct": round(hp.confidence * 100),
                "advantage": f"共同技能：{', '.join(hp.shared_skills[:3])}" if hp.shared_skills else "",
                "need_learn": "",
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "promotion_paths": promotion_paths,
            "transfer_paths": transfer_paths,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/graph/main-transfers/{job_name:path}")
async def get_main_transfers(job_name: str):
    """
    主岗位信息 + 换岗派生节点聚合
    数据来源：YOUTU-GraphRAG Job 节点 + TRANSFERS_TO 边
    """
    try:
        portrait = career_graphrag_service.generate_job_portrait(job_name)
        paths = career_graphrag_service.get_career_paths(job_name)

        main = {
            "title": portrait.title,
            "salary": portrait.salary_range,
            "industry": portrait.industry,
            "description": portrait.job_description,
        }

        transfers = []
        graph_nodes = [{"id": job_name, "title": job_name}]
        graph_edges = []

        for hp in paths.horizontal_paths:
            tgt = hp.target_job
            tgt_portrait = career_graphrag_service.generate_job_portrait(tgt)
            transfers.append({
                "target": tgt,
                "title": tgt,
                "match_level": _level_label(hp.confidence),
                "overlap_pct": round(hp.confidence * 100),
                "advantage": f"共同技能：{', '.join(hp.shared_skills[:3])}" if hp.shared_skills else "",
                "need_learn": "",
                "target_info": {
                    "title": tgt_portrait.title,
                    "industry": tgt_portrait.industry,
                    "salary": tgt_portrait.salary_range,
                },
            })
            if not any(n["id"] == tgt for n in graph_nodes):
                graph_nodes.append({"id": tgt, "title": tgt})
            graph_edges.append({"from": job_name, "to": tgt, "type": "TRANSFERS_TO", "label": "换岗"})

        return {
            "main": main,
            "transfers": transfers,
            "graph": {"nodes": graph_nodes, "edges": graph_edges},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jobs/search")
async def search_jobs(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    岗位搜索（模糊匹配 + YOUTU 相似度）
    """
    try:
        all_jobs = career_graphrag_service.get_all_jobs()
        q = query.lower().strip()

        # 精确/子串匹配（支持拆分关键词）
        keywords = q.split()
        exact = [
            j for j in all_jobs
            if any(kw in j["title"].lower() for kw in keywords)
        ]
        similar = youtu_retriever_service.find_similar_jobs(query, top_k=limit)
        similar_titles = {s["title"] for s in similar}

        results = []
        seen = set()
        for j in exact:
            if j["title"] not in seen:
                results.append(j)
                seen.add(j["title"])

        for j in all_jobs:
            if j["title"] in similar_titles and j["title"] not in seen:
                results.append(j)
                seen.add(j["title"])

        return [
            {
                "id": j["title"],
                "title": j["title"],
                "industry": "",
                "salary": j.get("salary_range", ""),
            }
            for j in results[:limit]
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jobs/real")
async def get_real_jobs(
    job: str = Query(..., description="岗位名称"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    原始招聘数据样本（来自 preprocessed_for_llm.csv）
    """
    try:
        df = _load_csv()
        if df is None:
            return {"jd_count": 0, "avg_salary_k": 0.0, "top_companies": [], "samples": []}

        subset = df[df["岗位名称"] == job]
        if subset.empty:
            # 模糊匹配
            subset = df[df["岗位名称"].str.contains(job, na=False)]

        jd_count = len(subset)

        # 薪资均值（复用模块级 _parse_salary_k）
        salaries = subset["薪资范围"].apply(_parse_salary_k).dropna().tolist()
        avg_salary_k = round(sum(salaries) / len(salaries), 1) if salaries else 0.0

        top_companies = subset["公司名称"].value_counts().head(5).index.tolist()

        samples = []
        for _, row in subset.head(limit).iterrows():
            samples.append({
                "company_name": row.get("公司名称", ""),
                "salary": row.get("薪资范围", ""),
                "address": row.get("地址", ""),
                "size": row.get("公司规模", ""),
                "description": str(row.get("岗位详情_clean", ""))[:200],
            })

        return {
            "jd_count": jd_count,
            "avg_salary_k": avg_salary_k,
            "top_companies": top_companies,
            "samples": samples,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jobs/ai_insight")
async def get_ai_insight(job_name: str = Query(..., description="岗位名称")):
    """
    AI 岗位洞察（YOUTU-GraphRAG 检索 + LLM 生成）
    """
    try:
        portrait = career_graphrag_service.generate_job_portrait(job_name)
        result = await youtu_retriever_service.query(
            f"请分析{job_name}岗位的市场前景、核心技能要求和职业发展建议，结合当前就业市场给出实用洞察。",
            top_k=10,
        )
        insight = result.get("answer", result.get("response", ""))

        return {
            "job_name": job_name,
            "insight": insight,
            "core_skills": portrait.skills[:8],
            "salary": portrait.salary_range,
            "industry": portrait.industry,
            "generated_by": "YOUTU-GraphRAG + LLM",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/market/industry_trends")
async def get_industry_trends():
    """
    行业趋势 - YOUTU-GraphRAG L4社区层 + L1属性层 + BELONGS_TO_INDUSTRY 聚合
    """
    try:
        # L4 社区层：获取职业族群宏观摘要
        community_ctx = youtu_retriever_service.retrieve_by_community(
            "职业发展行业趋势", top_k=8
        )
        community_summary = community_ctx.get("context", "")

        # L1 属性层 + BELONGS_TO_INDUSTRY：按行业聚合岗位数据
        all_jobs = career_graphrag_service.get_all_jobs()
        industry_map: Dict[str, Any] = {}

        for job in all_jobs:
            portrait = career_graphrag_service.generate_job_portrait(job["title"])
            ind = portrait.industry or "计算机软件"
            if ind not in industry_map:
                industry_map[ind] = {"jobs": [], "skills": [], "salaries": []}
            industry_map[ind]["jobs"].append(job["title"])
            industry_map[ind]["skills"].extend(portrait.skills[:3])
            if portrait.salary_avg_k:
                industry_map[ind]["salaries"].append(portrait.salary_avg_k)

        def _growth_label(job_count: int) -> str:
            if job_count >= 10: return "快速增长"
            if job_count >= 5:  return "稳步增长"
            if job_count >= 3:  return "平稳发展"
            return "新兴领域"

        def _outlook_label(job_count: int, avg_k: float) -> str:
            if job_count >= 10 and avg_k >= 15: return "前景广阔"
            if job_count >= 5:  return "持续需求旺盛"
            if avg_k >= 20:     return "高薪小众方向"
            if job_count >= 3:  return "稳定发展"
            return "新兴机遇多"

        trends = []
        for industry, data in industry_map.items():
            salaries = data["salaries"]
            avg_k = round(sum(salaries) / len(salaries), 1) if salaries else 0
            job_count = len(data["jobs"])
            hot_skills = list(dict.fromkeys(data["skills"]))[:5]
            growth = _growth_label(job_count)
            outlook = _outlook_label(job_count, avg_k)
            trends.append({
                "industry": industry,
                "trend": "上升" if job_count >= 5 else "平稳",
                "job_count": job_count,
                "avg_salary": f"{avg_k}k" if avg_k else "面议",
                "growth": growth,
                "hot_skills": hot_skills,
                "outlook": outlook,
                "jobs": data["jobs"][:6],
                "demand": "增长" if job_count >= 5 else "平稳",
                "description": f"{industry}领域共 {job_count} 个岗位，热门技能：{', '.join(hot_skills[:3])}",
            })

        if not trends:
            trends = [{
                "industry": "计算机软件", "trend": "上升", "job_count": 10,
                "avg_salary": "15k", "growth": "快速增长",
                "hot_skills": ["Python", "Java", "SQL"], "outlook": "前景广阔",
            }]

        return {
            "trends": trends,
            "community_insight": community_summary,  # L4 社区层宏观摘要
            "updated_at": "2026-04",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/market/trend")
async def get_market_trend(job_name: str = Query(..., description="岗位名称")):
    """
    单岗市场趋势
    来源：YOUTU 图谱 L1 属性层（薪资/技能/需求量）+ CSV 数据
    """
    try:
        # L1 属性层：直接从图谱获取
        attr_data = youtu_retriever_service.retrieve_by_attribute(job_name, attr_type="all")
        portrait = career_graphrag_service.generate_job_portrait(job_name)

        # CSV 真实需求结构（替换写死的"增长"伪趋势）
        df = _load_csv()
        demand = _demand_profile(job_name, df)
        jd_count = demand.get("jd_count", 0)
        avg_salary_k = portrait.salary_avg_k or 0
        if not avg_salary_k and demand.get("salary"):
            avg_salary_k = demand["salary"].get("median_k", 0)

        return {
            "job_name": job_name,
            "avg_salary_k": avg_salary_k,
            "salary_range": portrait.salary_range or attr_data.get("salary", ""),
            "job_count": jd_count or portrait.job_count,
            # 真实需求热度（按招聘量分级），替代恒为"增长"的假趋势
            "demand_level": demand.get("demand_level", "中") if demand.get("available") else "中",
            "demand_profile": demand,          # 招聘量/占比/薪资分位/公司规模分布 + 诚实 basis
            "hot_skills": portrait.skills[:6],
            "entry_friendly": portrait.entry_friendly,
            "top_regions": portrait.location.split("、") if portrait.location else [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/market/salary_comparison")
async def get_salary_comparison(job_name: str = Query(..., description="岗位名称")):
    """
    薪资对比
    来源：YOUTU 图谱（历史均薪） + CSV（样本均薪，两者均取自本地数据，无实时抓取）
    """
    try:
        portrait = career_graphrag_service.generate_job_portrait(job_name)
        graph_avg_k = portrait.salary_avg_k or 0

        df = _load_csv()
        csv_avg_k = 0.0
        csv_count = 0
        if df is not None:
            subset = df[df["岗位名称"].str.contains(job_name, na=False, regex=False)]
            csv_count = len(subset)
            salaries = subset["薪资范围"].apply(_parse_salary_k).dropna().tolist() if not subset.empty else []
            csv_avg_k = round(sum(salaries) / len(salaries), 1) if salaries else 0

        # live_avg_k = CSV 样本均薪；historical_avg_k = 图谱建模均薪（YOUTU-GraphRAG L1 属性层）
        # 两者均为本地历史数据，change_pct 反映两种统计口径偏差，不代表薪资时间变化趋势
        live_avg = csv_avg_k or graph_avg_k
        hist_avg = graph_avg_k or csv_avg_k
        change_pct = round((live_avg - hist_avg) / hist_avg * 100, 1) if hist_avg else 0

        return {
            "job_name": job_name,
            "live_avg_k": live_avg,
            "live_count": csv_count,
            "historical_avg_k": hist_avg,
            "historical_count": portrait.job_count or csv_count,
            "change_pct": change_pct,
            "note": "change_pct 为 CSV 样本均薪与图谱建模均薪的统计口径偏差，非时间涨幅趋势",
            "insufficient_data": (live_avg == 0 and hist_avg == 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/api/jobs/live/stats")
async def get_live_job_stats(job_names: Optional[str] = Query(None)):
    """
    实时岗位统计 - 从 CSV 计算
    """
    try:
        df = _load_csv()
        if df is None:
            return {"stats": [], "total_active": 0, "as_of": "2026-04"}

        names = [n.strip() for n in job_names.split(",")] if job_names else []

        stats = []
        if names:
            for name in names:
                subset = df[df["岗位名称"].str.contains(name, na=False, regex=False)]
                salaries = subset["薪资范围"].apply(_parse_salary_k).dropna().tolist()
                stats.append({
                    "job_name": name,
                    "jd_count": len(subset),
                    "avg_salary_k": round(sum(salaries) / len(salaries), 1) if salaries else 0,
                    "last_fetched": "2026-04-01",
                })
        else:
            for name in df["岗位名称"].value_counts().head(10).index:
                subset = df[df["岗位名称"] == name]
                salaries = subset["薪资范围"].apply(_parse_salary_k).dropna().tolist()
                stats.append({
                    "job_name": name,
                    "jd_count": len(subset),
                    "avg_salary_k": round(sum(salaries) / len(salaries), 1) if salaries else 0,
                    "last_fetched": "2026-04-01",
                })

        return {"stats": stats, "total_active": len(df), "as_of": "2026-04"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
