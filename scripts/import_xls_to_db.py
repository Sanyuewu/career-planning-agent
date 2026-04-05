#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 XLS 真实 JD 数据批量导入 job_real 表
用法：python scripts/import_xls_to_db.py
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
XLS_PATH = ROOT / "20260226105856_457.xls"

BATCH_SIZE = 500


async def main():
    import xlrd
    from sqlalchemy import text
    from app.db.database import get_db_session
    from app.db.models import JobRealModel

    # ── 解析 XLS ──────────────────────────────────────────────────────────────
    print("解析 XLS …")
    wb = xlrd.open_workbook(str(XLS_PATH), encoding_override="gbk")
    sh = wb.sheet_by_index(0)
    headers = [sh.cell_value(0, i) for i in range(sh.ncols)]
    rows = []
    for r in range(1, sh.nrows):
        row = {headers[i]: sh.cell_value(r, i) for i in range(sh.ncols)}
        rows.append(row)
    print(f"  共 {len(rows)} 条 JD")

    # ── 导入数据库 ────────────────────────────────────────────────────────────
    async with get_db_session() as db:
        # 热迁移：添加 industry 列（已存在则忽略）
        try:
            await db.execute(text("ALTER TABLE job_real ADD COLUMN industry TEXT DEFAULT ''"))
            await db.commit()
        except Exception:
            pass
        # 增量导入：先检查是否需要清空（默认增量，传 --reset 清空）
        import sys as _sys
        do_reset = "--reset" in _sys.argv
        if do_reset:
            await db.execute(text("DELETE FROM job_real"))
            await db.commit()
            print("  已清空旧数据（--reset 模式）")
        else:
            print("  增量导入模式（已存在的记录按 company_name+job_name 去重跳过）")

        # 构建已有 (company_name, job_name) 集合用于去重
        existing_set: set = set()
        if not do_reset:
            result_rows = await db.execute(
                text("SELECT company_name, job_name FROM job_real")
            )
            for r in result_rows:
                existing_set.add((r[0] or "", r[1] or ""))

        total = 0
        skipped = 0
        batch = []
        for row in rows:
            j_name = str(row.get("岗位名称", "")).strip()
            c_name = str(row.get("公司名称", "")).strip()
            if not do_reset and (c_name, j_name) in existing_set:
                skipped += 1
                continue
            obj = JobRealModel(
                job_name    = j_name,
                salary      = str(row.get("薪资范围", "")).strip(),
                company_name= c_name,
                address     = str(row.get("地址", "")).strip(),
                size        = str(row.get("公司规模", "")).strip(),
                industry    = str(row.get("所属行业", "")).strip(),
                description = str(row.get("岗位详情", "")).strip(),
                status      = 1,
            )
            batch.append(obj)
            if len(batch) >= BATCH_SIZE:
                db.add_all(batch)
                await db.commit()
                total += len(batch)
                print(f"  已导入 {total} 条…")
                batch = []

        if batch:
            db.add_all(batch)
            await db.commit()
            total += len(batch)

        if skipped:
            print(f"  跳过重复记录 {skipped} 条")

    print(f"\n✅  导入完成，共 {total} 条")

    # ── 验证 ──────────────────────────────────────────────────────────────────
    async with get_db_session() as db:
        from app.db.crud.job_real_crud import job_real_crud
        for name in ["前端开发", "Java", "软件测试", "实施工程师"]:
            stats = await job_real_crud.get_stats_by_job_name(db, name)
            print(f"  [{name}] count={stats['count']} avg_salary={stats['avg_salary_k']}K "
                  f"top={stats['top_companies'][:2]}")


if __name__ == "__main__":
    asyncio.run(main())
