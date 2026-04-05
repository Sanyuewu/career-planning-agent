# -*- coding: utf-8 -*-
"""
自主感知调度器 - APScheduler 定时任务
每日自动抓取岗位数据、刷新趋势快照、推送热度变化提醒
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler: Optional[object] = None


def _build_scheduler():
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        return AsyncIOScheduler(timezone="Asia/Shanghai")
    except ImportError:
        logger.warning("APScheduler 未安装，定时任务不可用。请 pip install apscheduler")
        return None


async def _task_fetch_live_jobs():
    """每日 00:30：抓取所有岗位最新 JD"""
    logger.info("[Scheduler] 开始每日岗位数据抓取")
    try:
        from app.services.job_fetcher import job_fetcher
        from app.graph.job_graph_repo import job_graph
        job_names = job_graph.get_valid_jobs()
        summary = await job_fetcher.fetch_and_store(job_names, limit_per_job=15)
        total = sum(summary.values())
        logger.info("[Scheduler] 岗位抓取完成，新增 %d 条记录", total)
    except Exception as e:
        logger.error("[Scheduler] 岗位抓取失败: %s", e)


async def _task_refresh_trend_snapshots():
    """每日 01:00：聚合 live_jobs 数据写入趋势快照"""
    logger.info("[Scheduler] 开始刷新岗位趋势快照")
    try:
        from app.db.database import get_db_session
        from app.db.crud.live_job_crud import LiveJobCRUD
        from app.db.models import JobTrendSnapshotModel
        from sqlalchemy import select, func

        async with get_db_session() as session:
            stats = await LiveJobCRUD.stats(session)

        async with get_db_session() as session:
            for stat in stats:
                snap = JobTrendSnapshotModel(
                    job_code=stat["job_name"],
                    snapshot_date=datetime.utcnow(),
                    jd_count=stat["jd_count"],
                    avg_salary=int(stat["avg_salary_k"] * 1000),
                    demand_index=min(stat["jd_count"] / 100.0, 10.0),
                    top_skills=[],
                )
                session.add(snap)
            await session.commit()
        logger.info("[Scheduler] 趋势快照刷新完成，共 %d 个岗位", len(stats))
    except Exception as e:
        logger.error("[Scheduler] 趋势快照刷新失败: %s", e)


async def _task_expire_old_jobs():
    """每日 02:00：清理超过 7 天的 live_jobs 记录"""
    logger.info("[Scheduler] 开始清理过期岗位数据")
    try:
        from app.services.job_fetcher import job_fetcher
        expired = await job_fetcher.expire_old_jobs(days=7)
        logger.info("[Scheduler] 过期岗位清理完成，共 %d 条", expired)
    except Exception as e:
        logger.error("[Scheduler] 过期清理失败: %s", e)


async def _task_push_hot_job_alerts():
    """每日 06:00：扫描活跃用户，推送岗位热度变化提醒"""
    logger.info("[Scheduler] 开始生成岗位热度提醒")
    try:
        from app.db.database import get_db_session
        from app.db.models import ChatSessionModel, StudentModel, JobTrendSnapshotModel
        from sqlalchemy import select, and_
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=24)

        async with get_db_session() as session:
            # 找出过去 24h 内有活动的会话
            stmt = (
                select(ChatSessionModel)
                .where(ChatSessionModel.updated_at >= cutoff)
                .limit(50)
            )
            active_sessions = (await session.execute(stmt)).scalars().all()

        for sess in active_sessions:
            try:
                student_id = sess.student_id
                if not student_id:
                    continue

                # 获取该用户的职业意向
                async with get_db_session() as session:
                    student = await session.get(StudentModel, student_id)
                    if not student or not student.career_intent:
                        continue
                    job_name = student.career_intent

                # 查询最新 vs 上期趋势快照
                async with get_db_session() as session:
                    stmt = (
                        select(JobTrendSnapshotModel)
                        .where(JobTrendSnapshotModel.job_code == job_name)
                        .order_by(JobTrendSnapshotModel.snapshot_date.desc())
                        .limit(2)
                    )
                    snaps = (await session.execute(stmt)).scalars().all()

                if len(snaps) < 2:
                    continue

                latest, prev = snaps[0], snaps[1]
                if prev.jd_count == 0:
                    continue

                change_pct = (latest.jd_count - prev.jd_count) / prev.jd_count * 100
                if abs(change_pct) < 10:
                    continue

                direction = "上涨" if change_pct > 0 else "下降"
                alert_msg = (
                    f"[系统提醒] 您关注的【{job_name}】岗位今日新增 {latest.jd_count} 条 JD，"
                    f"热度{direction} {abs(change_pct):.0f}%，建议更新匹配分析。"
                )

                # 写入系统消息到会话
                async with get_db_session() as session:
                    db_sess = await session.get(ChatSessionModel, sess.id)
                    if db_sess:
                        msgs = list(db_sess.messages or [])
                        msgs.append({
                            "role": "system",
                            "content": alert_msg,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        db_sess.messages = msgs
                        await session.commit()
                        logger.info("[Scheduler] 已推送热度提醒给 student=%s job=%s", student_id, job_name)
            except Exception as inner_e:
                logger.warning("[Scheduler] 推送提醒失败 session=%s: %s", sess.session_id, inner_e)

    except Exception as e:
        logger.error("[Scheduler] 热度提醒任务失败: %s", e)


def start_scheduler():
    """启动调度器（在 FastAPI lifespan 中调用）"""
    global _scheduler
    scheduler = _build_scheduler()
    if scheduler is None:
        return

    try:
        from apscheduler.triggers.cron import CronTrigger
        scheduler.add_job(_task_fetch_live_jobs, CronTrigger(hour=0, minute=30), id="fetch_live_jobs", replace_existing=True)
        scheduler.add_job(_task_refresh_trend_snapshots, CronTrigger(hour=1, minute=0), id="refresh_snapshots", replace_existing=True)
        scheduler.add_job(_task_expire_old_jobs, CronTrigger(hour=2, minute=0), id="expire_old_jobs", replace_existing=True)
        scheduler.add_job(_task_push_hot_job_alerts, CronTrigger(hour=6, minute=0), id="push_alerts", replace_existing=True)
        scheduler.start()
        _scheduler = scheduler
        logger.info("[Scheduler] 定时任务调度器已启动，共 %d 个任务", len(scheduler.get_jobs()))
    except Exception as e:
        logger.error("[Scheduler] 调度器启动失败: %s", e)


def stop_scheduler():
    """关闭调度器（在 FastAPI lifespan yield 后调用）"""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("[Scheduler] 调度器已关闭")
        except Exception as e:
            logger.warning("[Scheduler] 调度器关闭异常: %s", e)
        finally:
            _scheduler = None
