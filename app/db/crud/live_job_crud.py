# -*- coding: utf-8 -*-
"""
实时岗位数据 CRUD
操作 live_jobs 表：插入/查询/去重/过期清理
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Any
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LiveJobModel


def _parse_salary_k(salary_str: str) -> tuple[float, float]:
    """解析薪资字符串 → (min_k, max_k)，单位：千元/月"""
    if not salary_str:
        return 0.0, 0.0
    s = salary_str.upper().replace(" ", "").replace("，", ",")
    nums = re.findall(r"(\d+(?:\.\d+)?)", s)
    if not nums:
        return 0.0, 0.0
    vals = [float(n) for n in nums[:2]]
    is_k = "K" in s
    # 判断是年薪还是月薪（年薪通常 > 100K 或含"年"字）
    is_annual = "年" in salary_str or (is_k and max(vals) > 100)
    if is_annual:
        vals = [v / 12 for v in vals]
    elif not is_k:
        # 数值是元/月，转千元
        vals = [v / 1000 for v in vals]
    mn = vals[0]
    mx = vals[1] if len(vals) > 1 else vals[0]
    return round(mn, 1), round(mx, 1)


class LiveJobCRUD:
    """实时岗位数据访问层"""

    @staticmethod
    async def upsert_batch(
        session: AsyncSession,
        jobs: list[dict[str, Any]],
        source: str,
    ) -> int:
        """批量插入，24小时内相同(job_name, company, source)跳过去重。返回实际插入数。"""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        inserted = 0
        for job in jobs:
            job_name = (job.get("job_name") or "").strip()
            company = (job.get("company") or "").strip()
            if not job_name:
                continue

            # 去重检查
            exists = await session.scalar(
                select(func.count(LiveJobModel.id)).where(
                    and_(
                        LiveJobModel.job_name == job_name,
                        LiveJobModel.company == company,
                        LiveJobModel.source == source,
                        LiveJobModel.fetched_at >= cutoff,
                    )
                )
            )
            if exists:
                continue

            salary_raw = job.get("salary_raw") or job.get("salary", "")
            min_k, max_k = _parse_salary_k(salary_raw)

            row = LiveJobModel(
                job_name=job_name,
                raw_title=job.get("raw_title") or job_name,
                company=company,
                city=job.get("city", ""),
                salary_raw=salary_raw,
                salary_min_k=min_k,
                salary_max_k=max_k,
                skills=job.get("skills") or [],
                description=job.get("description", ""),
                requirements=job.get("requirements", ""),
                source=source,
                source_url=job.get("source_url", ""),
                fetched_at=datetime.utcnow(),
                is_active=1,
            )
            session.add(row)
            inserted += 1

        await session.commit()
        return inserted

    @staticmethod
    async def expire_old(session: AsyncSession, days: int = 7) -> int:
        """将超过 days 天的记录标记为过期（is_active=0）。返回过期数量。"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            update(LiveJobModel)
            .where(and_(LiveJobModel.fetched_at < cutoff, LiveJobModel.is_active == 1))
            .values(is_active=0)
        )
        await session.commit()
        return result.rowcount

    @staticmethod
    async def query(
        session: AsyncSession,
        job_name: Optional[str] = None,
        city: Optional[str] = None,
        salary_min_k: Optional[float] = None,
        active_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """分页查询实时岗位列表"""
        stmt = select(LiveJobModel)
        conditions = []
        if active_only:
            conditions.append(LiveJobModel.is_active == 1)
        if job_name:
            conditions.append(LiveJobModel.job_name.contains(job_name))
        if city:
            conditions.append(LiveJobModel.city.contains(city))
        if salary_min_k is not None:
            conditions.append(LiveJobModel.salary_min_k >= salary_min_k)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(LiveJobModel.fetched_at.desc()).limit(limit).offset(offset)
        rows = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "job_name": r.job_name,
                "raw_title": r.raw_title,
                "company": r.company,
                "city": r.city,
                "salary_raw": r.salary_raw,
                "salary_min_k": r.salary_min_k,
                "salary_max_k": r.salary_max_k,
                "skills": r.skills or [],
                "description": r.description[:200] if r.description else "",
                "source": r.source,
                "source_url": r.source_url,
                "fetched_at": r.fetched_at.isoformat() if r.fetched_at else "",
                "is_active": r.is_active,
            }
            for r in rows
        ]

    @staticmethod
    async def stats(
        session: AsyncSession,
        job_names: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """各岗位最新 JD 数量 + 均薪统计（仅统计 active 记录）"""
        stmt = (
            select(
                LiveJobModel.job_name,
                func.count(LiveJobModel.id).label("jd_count"),
                func.avg(
                    (LiveJobModel.salary_min_k + LiveJobModel.salary_max_k) / 2
                ).label("avg_salary_k"),
                func.max(LiveJobModel.fetched_at).label("last_fetched"),
            )
            .where(LiveJobModel.is_active == 1)
            .group_by(LiveJobModel.job_name)
            .order_by(func.count(LiveJobModel.id).desc())
        )
        if job_names:
            stmt = stmt.where(LiveJobModel.job_name.in_(job_names))
        rows = (await session.execute(stmt)).all()
        return [
            {
                "job_name": r.job_name,
                "jd_count": r.jd_count,
                "avg_salary_k": round(r.avg_salary_k or 0, 1),
                "last_fetched": r.last_fetched.isoformat() if r.last_fetched else "",
            }
            for r in rows
        ]

    @staticmethod
    async def count_active(session: AsyncSession) -> int:
        return await session.scalar(
            select(func.count(LiveJobModel.id)).where(LiveJobModel.is_active == 1)
        ) or 0
