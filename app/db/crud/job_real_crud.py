# -*- coding: utf-8 -*-
"""
真实招聘数据CRUD操作
提供基于9958条真实JD的市场统计查询
"""

import re
import math
from typing import List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobRealModel


def _normalize_job_name(name: str) -> str:
    """标准化岗位名称，用于模糊匹配。
    仅移除括号内的版本号标记（如"数据分析师(1)"→"数据分析师"），
    保留 / 分隔符，因为真实岗位名如"C/C++"、"质量管理/测试"含 /。
    """
    name = str(name).strip()
    name = re.sub(r"[（(【\[].*?[）)】\]]", "", name)
    # 仅截断连字符/破折号分隔的副标题（如"工程师-北京"），不截断斜线
    name = re.sub(r"[-–—·|].*$", "", name)
    return name.strip()


def _escape_like_pattern(pattern: str) -> str:
    """转义 SQL LIKE 模式中的特殊字符 % 和 _，防止通配符注入"""
    if not pattern:
        return pattern
    return pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_salary_k(salary_str: str) -> float:
    """
    解析薪资字符串，返回月均薪（千元）
    支持格式：'10-20K', '15K', '10k-20k', '10000-20000'
    """
    if not salary_str:
        return 0.0
    s = salary_str.upper().replace("，", ",").replace(" ", "")
    # 提取所有数字
    nums = re.findall(r"(\d+(?:\.\d+)?)", s)
    if not nums:
        return 0.0
    vals = [float(n) for n in nums[:2]]
    # 判断是否带K标识
    if "K" in s or "k" in s:
        avg = sum(vals) / len(vals)
        return round(avg, 1)
    else:
        # 纯数字，判断量级（>1000认为是元，转千元）
        avg = sum(vals) / len(vals)
        if avg > 1000:
            return round(avg / 1000, 1)
        return round(avg, 1)


class JobRealCRUD:
    """真实招聘数据访问层"""

    async def get_stats_by_job_name(
        self,
        session: AsyncSession,
        job_name: str,
    ) -> Dict[str, Any]:
        """
        按岗位名称聚合统计真实招聘数据
        返回：{count, avg_salary_k, top_companies, salary_samples}
        """
        keyword = _normalize_job_name(job_name)
        if not keyword:
            return {"count": 0, "avg_salary_k": 0.0, "top_companies": [], "salary_samples": []}

        # 转义特殊字符，防止LIKE通配符注入
        safe_keyword = _escape_like_pattern(keyword)
        # 模糊匹配 job_name
        stmt = (
            select(JobRealModel.salary, JobRealModel.company_name)
            .where(JobRealModel.job_name.like(f"%{safe_keyword}%", escape="\\"))
            .where(JobRealModel.status == 1)
            .limit(500)
        )
        result = await session.execute(stmt)
        rows = result.all()

        if not rows:
            return {"count": 0, "avg_salary_k": 0.0, "top_companies": [], "salary_samples": []}

        count = len(rows)
        salaries = []
        company_counter: Dict[str, int] = {}

        for salary_str, company in rows:
            val = _parse_salary_k(salary_str or "")
            if val > 0:
                salaries.append(val)
            if company:
                company_counter[company] = company_counter.get(company, 0) + 1

        avg_salary_k = round(sum(salaries) / len(salaries), 1) if salaries else 0.0
        top_companies = sorted(company_counter, key=lambda c: company_counter[c], reverse=True)[:5]

        return {
            "count": count,
            "avg_salary_k": avg_salary_k,
            "top_companies": top_companies,
            "salary_samples": [s for s in salaries[:10]],
        }

    async def get_samples(
        self,
        session: AsyncSession,
        job_name: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        获取指定岗位的真实招聘样本（用于前端展示）
        """
        keyword = _normalize_job_name(job_name)
        if not keyword:
            return []

        safe_keyword = _escape_like_pattern(keyword)
        stmt = (
            select(
                JobRealModel.job_name,
                JobRealModel.salary,
                JobRealModel.company_name,
                JobRealModel.address,
                JobRealModel.size,
                JobRealModel.description,
            )
            .where(JobRealModel.job_name.like(f"%{safe_keyword}%", escape="\\"))
            .where(JobRealModel.status == 1)
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()

        return [
            {
                "job_name": r.job_name,
                "salary": r.salary or "薪资面议",
                "company_name": r.company_name or "未知公司",
                "address": r.address or "",
                "size": r.size or "",
                "description": (r.description or "")[:200],
            }
            for r in rows
        ]

    async def count_by_job_name(
        self,
        session: AsyncSession,
        job_name: str,
    ) -> int:
        """快速计数（用于 demand_index 计算）"""
        keyword = _normalize_job_name(job_name)
        if not keyword:
            return 0
        safe_keyword = _escape_like_pattern(keyword)
        stmt = (
            select(func.count())
            .select_from(JobRealModel)
            .where(JobRealModel.job_name.like(f"%{safe_keyword}%", escape="\\"))
            .where(JobRealModel.status == 1)
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def list_jobs(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取真实岗位列表（去重后的岗位名称）
        返回唯一的岗位名称列表
        """
        from app.db.database import get_db_session
        
        async with get_db_session() as session:
            stmt = (
                select(JobRealModel.job_name)
                .where(JobRealModel.status == 1)
                .where(JobRealModel.job_name != None)
                .where(JobRealModel.job_name != "")
                .distinct()
                .order_by(JobRealModel.job_name)
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            return [{"title": r, "id": r} for r in rows if r]

    async def search_jobs(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        搜索真实岗位
        """
        if not query:
            return []
        
        from app.db.database import get_db_session
        safe_query = _escape_like_pattern(query)
        
        async with get_db_session() as session:
            stmt = (
                select(JobRealModel.job_name)
                .where(JobRealModel.status == 1)
                .where(JobRealModel.job_name.ilike(f"%{safe_query}%"))
                .distinct()
                .order_by(JobRealModel.job_name)
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            return [{"title": r, "id": r} for r in rows if r]

    async def list_real_jobs(
        self,
        limit: int = 50,
        source: str = None,
    ) -> List[Dict[str, Any]]:
        """
        获取真实招聘JD列表（完整信息）
        """
        from app.db.database import get_db_session
        
        async with get_db_session() as session:
            stmt = (
                select(
                    JobRealModel.id,
                    JobRealModel.job_name,
                    JobRealModel.company_name,
                    JobRealModel.salary,
                    JobRealModel.address,
                    JobRealModel.description,
                )
                .where(JobRealModel.status == 1)
            )
            if source:
                stmt = stmt.where(JobRealModel.source == source)
            stmt = stmt.order_by(JobRealModel.created_at.desc()).limit(limit)
            
            result = await session.execute(stmt)
            rows = result.all()
            
            return [
                {
                    "id": r.id,
                    "job_name": r.job_name,
                    "company_name": r.company_name,
                    "salary": r.salary,
                    "address": r.address,
                    "description": (r.description or "")[:200],
                }
                for r in rows
            ]

    async def get_industry_stats(
        self,
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        从真实JD数据统计各行业分布（按 JD 数量降序）。
        返回: [{industry, jd_count, avg_salary_k, top_jobs}]
        """
        stmt = (
            select(JobRealModel.industry, JobRealModel.salary, JobRealModel.job_name)
            .where(JobRealModel.status == 1)
            .where(JobRealModel.industry != None)
            .where(JobRealModel.industry != "")
        )
        result = await session.execute(stmt)
        rows = result.all()

        from collections import defaultdict, Counter
        ind_data: Dict[str, Dict] = defaultdict(lambda: {"salaries": [], "jobs": []})
        for industry_raw, salary, job_name in rows:
            # 取行业字符串第一个逗号前的主行业
            ind = (industry_raw or "").split(",")[0].strip()
            if not ind:
                continue
            val = _parse_salary_k(salary or "")
            if val > 0:
                ind_data[ind]["salaries"].append(val)
            ind_data[ind]["jobs"].append(job_name or "")

        stats = []
        for ind, data in ind_data.items():
            salaries = data["salaries"]
            jobs = data["jobs"]
            avg_sal = round(sum(salaries) / len(salaries), 1) if salaries else 0.0
            top_jobs = [j for j, _ in Counter(jobs).most_common(3)]
            stats.append({
                "industry": ind,
                "jd_count": len(jobs),
                "avg_salary_k": avg_sal,
                "top_jobs": top_jobs,
            })

        stats.sort(key=lambda x: x["jd_count"], reverse=True)
        # 数据质量警告：样本量不足时前端显示提示
        for item in stats:
            item["data_quality_warning"] = item["jd_count"] < 100
        return stats[:20]

    async def get_job_market_details(
        self,
        session: AsyncSession,
        job_name: str,
    ) -> Dict[str, Any]:
        """
        获取指定岗位的真实市场详情：薪资分布、公司规模分布、地区分布、代表公司。
        """
        keyword = _normalize_job_name(job_name)
        if not keyword:
            return {}
        safe_keyword = _escape_like_pattern(keyword)
        stmt = (
            select(JobRealModel.salary, JobRealModel.size, JobRealModel.address, JobRealModel.company_name)
            .where(JobRealModel.job_name.like(f"%{safe_keyword}%", escape="\\"))
            .where(JobRealModel.status == 1)
            .limit(500)
        )
        result = await session.execute(stmt)
        rows = result.all()
        if not rows:
            return {}

        from collections import Counter, defaultdict
        salary_buckets: Dict[str, int] = defaultdict(int)
        size_counter: Counter = Counter()
        city_salaries: Dict[str, list] = defaultdict(list)
        company_counter: Counter = Counter()

        for salary, size, address, company in rows:
            val = _parse_salary_k(salary or "")
            # 薪资区间分桶（单位：K）
            if val > 0:
                if val < 8:
                    bucket = "8K以下"
                elif val < 12:
                    bucket = "8-12K"
                elif val < 18:
                    bucket = "12-18K"
                elif val < 25:
                    bucket = "18-25K"
                elif val < 40:
                    bucket = "25-40K"
                else:
                    bucket = "40K以上"
                salary_buckets[bucket] += 1
            # 公司规模
            if size:
                size_counter[size] += 1
            # 城市薪资
            if address:
                city = address.split("-")[0].split("·")[0].strip()[:5]
                if city and val > 0:
                    city_salaries[city].append(val)
            # 代表公司
            if company:
                company_counter[company] += 1

        bucket_order = ["8K以下", "8-12K", "12-18K", "18-25K", "25-40K", "40K以上"]
        salary_dist = [
            {"range": b, "count": salary_buckets.get(b, 0)} for b in bucket_order
        ]
        size_dist = [
            {"size": s, "count": c} for s, c in size_counter.most_common(6)
        ]
        city_dist = sorted(
            [
                {"city": city, "count": len(sals), "avg_salary_k": round(sum(sals) / len(sals), 1)}
                for city, sals in city_salaries.items()
            ],
            key=lambda x: x["count"], reverse=True,
        )[:8]
        top_companies = [c for c, _ in company_counter.most_common(5)]

        return {
            "salary_distribution": salary_dist,
            "company_size": size_dist,
            "location_distribution": city_dist,
            "top_companies": top_companies,
            "data_count": len(rows),
            "data_source": "真实JD数据库（9958条）",
        }

    @staticmethod
    def calc_demand_index(jd_count: int, user_match_count: int = 0) -> float:
        """
        计算市场需求指数（0-100）
        基于真实JD数量的对数标准化 + 用户匹配次数加成
        500条JD → ~90分；100条→~66分；0条→10分
        """
        if jd_count <= 0:
            base = 10.0
        else:
            base = min(math.log2(jd_count + 1) / math.log2(500) * 90 + 10, 100)
        bonus = min(user_match_count * 2.0, 10.0)
        return round(min(base + bonus, 100.0), 2)


job_real_crud = JobRealCRUD()
