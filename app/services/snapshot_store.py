# -*- coding: utf-8 -*-
"""
成长闭环时序层写入/读取服务（snapshot_store）。

把"画像→差距→行动→进步"四步里产生的历史态落库为不可变快照：
  - PortraitSnapshot：每次画像更新 append 一条，version 递增
  - MatchSnapshot：每次匹配 append 一条，关联当时的画像版本
  - ActionPlan：行动计划独立成实体，支持勾选完成/逾期追踪

设计取舍（与 RunRecorder 一致）：
  - 同步 SessionLocal 落库（SQLite 写入极快），可被 student_graph_service 等
    同步代码与经 to_thread 的异步路径直接调用，无需改函数签名。
  - **写入失败绝不影响主流程**：全部 try/except 包裹，记录降级为 best-effort。
  - 租户取 contextvar（security_context.get_tenant），与 KVStore 行级隔离一致。
  - portrait_json 经 PII 加密边界落库，与 KVStore 学生画像同等对待。
"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.core.security_context import get_tenant
from app.core.pii import encrypt_text, decrypt_text
from app.models.db_models import PortraitSnapshot, MatchSnapshot, ActionPlan
from app.services.state_store import _ensure_tables

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# 写入（append-only，best-effort，失败不抛）
# ════════════════════════════════════════════════════════════════

def record_portrait_snapshot(
    student_id: str,
    attributes: Dict[str, Any],
    trigger: str = "resume_update",
) -> Optional[int]:
    """为学生当前画像 append 一条快照，返回新版本号（失败返回 None）。

    version = 该学生（本租户）现有最大版本 + 1。单进程 SQLite 基线下足够；
    多实例并发写入的版本竞争属规模化债，与 _task_store 同批处理。
    """
    if not student_id:
        return None
    _ensure_tables()
    tenant = get_tenant()
    try:
        with SessionLocal() as db:
            cur_max = db.execute(
                select(func.max(PortraitSnapshot.version)).where(
                    PortraitSnapshot.student_id == student_id,
                    PortraitSnapshot.tenant == tenant,
                )
            ).scalar_one_or_none()
            version = int(cur_max or 0) + 1
            db.add(PortraitSnapshot(
                id=str(uuid.uuid4()),
                student_id=student_id,
                tenant=tenant,
                version=version,
                trigger=trigger,
                portrait_json=encrypt_text(json.dumps(attributes, ensure_ascii=False, default=str)),
                completeness_score=_as_float(attributes.get("completeness_score")),
                competitiveness_score=_as_float(attributes.get("competitiveness_score")),
                created_at=datetime.utcnow(),
            ))
            db.commit()
        return version
    except Exception as e:
        logger.warning("[snapshot] 画像快照写入失败 student=%s: %s", student_id, e)
        return None


def latest_portrait_version(student_id: str) -> Optional[int]:
    """当前租户内该学生的最新画像版本号（无快照返回 None）。"""
    if not student_id:
        return None
    _ensure_tables()
    try:
        with SessionLocal() as db:
            cur_max = db.execute(
                select(func.max(PortraitSnapshot.version)).where(
                    PortraitSnapshot.student_id == student_id,
                    PortraitSnapshot.tenant == get_tenant(),
                )
            ).scalar_one_or_none()
        return int(cur_max) if cur_max is not None else None
    except Exception as e:
        logger.warning("[snapshot] 读取最新画像版本失败 student=%s: %s", student_id, e)
        return None


def record_match_snapshot(
    student_id: str,
    job_name: str,
    match_result: Dict[str, Any],
    weight_used: Optional[Dict[str, float]] = None,
    portrait_version: Optional[int] = None,
) -> Optional[str]:
    """为一次人岗匹配 append 一条快照，返回 snapshot_id（失败返回 None）。

    portrait_version 缺省自动取该学生当前最新画像版本，建立"基于哪版画像算"的关联。
    match_result 接受 MatchResult.model_dump() 或等价 dict。
    """
    if not student_id or not job_name:
        return None
    _ensure_tables()
    if portrait_version is None:
        portrait_version = latest_portrait_version(student_id)
    details = match_result.get("details") if isinstance(match_result.get("details"), dict) else {}
    matched = match_result.get("matched_skills", details.get("matched_skills", []))
    missing = match_result.get("missing_skills", details.get("missing_skills", []))
    snap_id = str(uuid.uuid4())
    try:
        with SessionLocal() as db:
            db.add(MatchSnapshot(
                id=snap_id,
                student_id=student_id,
                tenant=get_tenant(),
                portrait_version=portrait_version,
                job_name=job_name,
                total_match=_as_float(match_result.get("total_match")) or 0.0,
                basic_match=_as_float(match_result.get("basic_match")) or 0.0,
                skill_match=_as_float(match_result.get("skill_match")) or 0.0,
                quality_match=_as_float(match_result.get("quality_match")) or 0.0,
                potential_match=_as_float(match_result.get("potential_match")) or 0.0,
                matched_skills=json.dumps(matched, ensure_ascii=False, default=str),
                missing_skills=json.dumps(missing, ensure_ascii=False, default=str),
                weight_used=json.dumps(weight_used, ensure_ascii=False) if weight_used else None,
                eligible=bool(match_result.get("eligible", True)),
                veto_reason=match_result.get("veto_reason", "") or None,
                created_at=datetime.utcnow(),
            ))
            db.commit()
        return snap_id
    except Exception as e:
        logger.warning("[snapshot] 匹配快照写入失败 student=%s job=%s: %s", student_id, job_name, e)
        return None


def record_action_plan(
    student_id: str,
    items: List[Dict[str, Any]],
    job_name: Optional[str] = None,
    portrait_version: Optional[int] = None,
) -> Optional[str]:
    """把行动计划落为独立实体，返回 plan_id（失败返回 None）。

    旧 active 计划标记 superseded（一名学生同一时间只有一份生效计划）。
    每个 item 补齐 id/status，便于后续按项勾选完成。
    """
    if not student_id or not items:
        return None
    _ensure_tables()
    if portrait_version is None:
        portrait_version = latest_portrait_version(student_id)
    norm_items = [_normalize_item(it) for it in items if isinstance(it, dict)]
    if not norm_items:
        return None
    plan_id = str(uuid.uuid4())
    tenant = get_tenant()
    try:
        with SessionLocal() as db:
            # 旧生效计划置为 superseded
            for old in db.execute(
                select(ActionPlan).where(
                    ActionPlan.student_id == student_id,
                    ActionPlan.tenant == tenant,
                    ActionPlan.status == "active",
                )
            ).scalars().all():
                old.status = "superseded"
            db.add(ActionPlan(
                id=plan_id,
                student_id=student_id,
                tenant=tenant,
                portrait_version=portrait_version,
                job_name=job_name,
                items_json=json.dumps(norm_items, ensure_ascii=False, default=str),
                status="active",
                created_at=datetime.utcnow(),
            ))
            db.commit()
        return plan_id
    except Exception as e:
        logger.warning("[snapshot] 行动计划写入失败 student=%s: %s", student_id, e)
        return None


# ════════════════════════════════════════════════════════════════
# 读取（供 ProgressService / 学生端端点消费）
# ════════════════════════════════════════════════════════════════

def list_portrait_snapshots(student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """该学生（本租户）的画像快照，按 version 升序。portrait_json 已解密为 dict。"""
    if not student_id:
        return []
    _ensure_tables()
    try:
        with SessionLocal() as db:
            rows = db.execute(
                select(PortraitSnapshot).where(
                    PortraitSnapshot.student_id == student_id,
                    PortraitSnapshot.tenant == get_tenant(),
                ).order_by(PortraitSnapshot.version.asc()).limit(limit)
            ).scalars().all()
        return [_portrait_row_to_dict(r) for r in rows]
    except Exception as e:
        logger.warning("[snapshot] 读取画像快照失败 student=%s: %s", student_id, e)
        return []


def list_match_snapshots(student_id: str, job_name: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
    """该学生（本租户）的匹配快照，按时间升序；可选按岗位过滤。"""
    if not student_id:
        return []
    _ensure_tables()
    try:
        with SessionLocal() as db:
            stmt = select(MatchSnapshot).where(
                MatchSnapshot.student_id == student_id,
                MatchSnapshot.tenant == get_tenant(),
            )
            if job_name:
                stmt = stmt.where(MatchSnapshot.job_name == job_name)
            rows = db.execute(
                stmt.order_by(MatchSnapshot.created_at.asc()).limit(limit)
            ).scalars().all()
        return [_match_row_to_dict(r) for r in rows]
    except Exception as e:
        logger.warning("[snapshot] 读取匹配快照失败 student=%s: %s", student_id, e)
        return []


def get_active_action_plan(student_id: str) -> Optional[Dict[str, Any]]:
    """该学生（本租户）当前生效的行动计划（无则 None）。"""
    if not student_id:
        return None
    _ensure_tables()
    try:
        with SessionLocal() as db:
            row = db.execute(
                select(ActionPlan).where(
                    ActionPlan.student_id == student_id,
                    ActionPlan.tenant == get_tenant(),
                    ActionPlan.status == "active",
                ).order_by(ActionPlan.created_at.desc())
            ).scalars().first()
        return _action_row_to_dict(row) if row else None
    except Exception as e:
        logger.warning("[snapshot] 读取行动计划失败 student=%s: %s", student_id, e)
        return None


def complete_action_item(student_id: str, item_id: str) -> bool:
    """把某行动项标记完成（写 completed_at）。返回是否命中并更新。

    归属由调用方（端点 authz）保证；此处仍按 student_id + tenant 双重过滤，防越权。
    若全部项完成则整份计划置 completed。
    """
    if not student_id or not item_id:
        return False
    _ensure_tables()
    tenant = get_tenant()
    try:
        with SessionLocal() as db:
            plan = db.execute(
                select(ActionPlan).where(
                    ActionPlan.student_id == student_id,
                    ActionPlan.tenant == tenant,
                    ActionPlan.status == "active",
                ).order_by(ActionPlan.created_at.desc())
            ).scalars().first()
            if not plan:
                return False
            items = json.loads(plan.items_json)
            hit = False
            for it in items:
                if it.get("id") == item_id:
                    it["status"] = "done"
                    it["completed_at"] = datetime.utcnow().isoformat()
                    hit = True
                    break
            if not hit:
                return False
            plan.items_json = json.dumps(items, ensure_ascii=False, default=str)
            if all(it.get("status") == "done" for it in items):
                plan.status = "completed"
                plan.completed_at = datetime.utcnow()
            db.commit()
        return True
    except Exception as e:
        logger.warning("[snapshot] 完成行动项失败 student=%s item=%s: %s", student_id, item_id, e)
        return False


# ════════════════════════════════════════════════════════════════
# 群体时序聚合（院校看板趋势用；按月分桶在 Python 做，跨 SQLite/PG 可移植）
# ════════════════════════════════════════════════════════════════

def _bucket_monthly_avg(pairs: List) -> List[Dict[str, Any]]:
    """[(created_at, value)] → 按月 [{month, avg, n}] 升序。"""
    from collections import defaultdict
    buckets: Dict[str, List[float]] = defaultdict(list)
    for dt, v in pairs:
        if dt is None or v is None:
            continue
        buckets[dt.strftime("%Y-%m")].append(float(v))
    out = []
    for k in sorted(buckets):
        vals = buckets[k]
        out.append({"month": k, "avg": round(sum(vals) / len(vals), 1), "n": len(vals)})
    return out


def cohort_competitiveness_series(student_ids: List[str], tenant: Optional[str] = None) -> List[Dict[str, Any]]:
    """群体竞争力随月趋势（来自 PortraitSnapshot）。"""
    ids = [s for s in (student_ids or []) if s]
    if not ids:
        return []
    tenant = tenant or get_tenant()
    _ensure_tables()
    try:
        with SessionLocal() as db:
            rows = db.execute(
                select(PortraitSnapshot.created_at, PortraitSnapshot.competitiveness_score).where(
                    PortraitSnapshot.student_id.in_(ids), PortraitSnapshot.tenant == tenant)
            ).all()
        return _bucket_monthly_avg([(r[0], r[1]) for r in rows])
    except Exception as e:
        logger.warning("[snapshot] 群体竞争力趋势失败: %s", e)
        return []


def cohort_match_series(student_ids: List[str], tenant: Optional[str] = None) -> List[Dict[str, Any]]:
    """群体匹配分随月趋势（来自 MatchSnapshot）。"""
    ids = [s for s in (student_ids or []) if s]
    if not ids:
        return []
    tenant = tenant or get_tenant()
    _ensure_tables()
    try:
        with SessionLocal() as db:
            rows = db.execute(
                select(MatchSnapshot.created_at, MatchSnapshot.total_match).where(
                    MatchSnapshot.student_id.in_(ids), MatchSnapshot.tenant == tenant)
            ).all()
        return _bucket_monthly_avg([(r[0], r[1]) for r in rows])
    except Exception as e:
        logger.warning("[snapshot] 群体匹配趋势失败: %s", e)
        return []


def cohort_action_completion(student_ids: List[str], tenant: Optional[str] = None) -> Dict[str, Any]:
    """群体行动完成率（active+completed 计划的 items 聚合）。"""
    ids = [s for s in (student_ids or []) if s]
    if not ids:
        return {"avg_pct": 0.0, "items_done": 0, "items_total": 0}
    tenant = tenant or get_tenant()
    _ensure_tables()
    total = done = 0
    try:
        with SessionLocal() as db:
            rows = db.execute(
                select(ActionPlan.items_json).where(
                    ActionPlan.student_id.in_(ids), ActionPlan.tenant == tenant,
                    ActionPlan.status.in_(["active", "completed"]))
            ).all()
        for (ij,) in rows:
            try:
                items = json.loads(ij)
            except (json.JSONDecodeError, TypeError):
                continue
            total += len(items)
            done += sum(1 for it in items if it.get("status") == "done")
    except Exception as e:
        logger.warning("[snapshot] 群体行动完成率失败: %s", e)
    return {"avg_pct": round(done / total * 100, 1) if total else 0.0,
            "items_done": done, "items_total": total}


# ════════════════════════════════════════════════════════════════
# 内部辅助
# ════════════════════════════════════════════════════════════════

def _as_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _due_from_timeline(timeline: str, base: datetime) -> str:
    """从 '第1-2个月'/'第3-6个月' 推截止日（取窗口末月 ×30 天）。无法解析→空。
    让逾期/复评提醒可触发——闭环能自旋而非永远静默等用户。"""
    nums = re.findall(r"\d+", timeline or "")
    if not nums:
        return ""
    months = int(nums[-1])
    return (base + timedelta(days=months * 30)).isoformat()


def _normalize_item(it: Dict[str, Any], base: Optional[datetime] = None) -> Dict[str, Any]:
    """补齐行动项的 id/status；due_date 缺省时由 timeline 推出（供逾期追踪）。"""
    base = base or datetime.utcnow()
    timeline = it.get("timeline", "")
    return {
        "id":          it.get("id") or str(uuid.uuid4()),
        "title":       it.get("title", ""),
        "description": it.get("description", ""),
        "timeline":    timeline,
        "status":      it.get("status", "pending"),
        "due_date":    it.get("due_date") or _due_from_timeline(timeline, base),
        "completed_at": it.get("completed_at", ""),
        "milestones":  it.get("milestones", []),
    }


def _portrait_row_to_dict(r: PortraitSnapshot) -> Dict[str, Any]:
    try:
        portrait = json.loads(decrypt_text(r.portrait_json))
    except (json.JSONDecodeError, TypeError):
        portrait = {}
    return {
        "id": r.id, "version": r.version, "trigger": r.trigger,
        "completeness_score": r.completeness_score,
        "competitiveness_score": r.competitiveness_score,
        "portrait": portrait,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


def _match_row_to_dict(r: MatchSnapshot) -> Dict[str, Any]:
    return {
        "id": r.id, "job_name": r.job_name,
        "portrait_version": r.portrait_version,
        "total_match": r.total_match, "basic_match": r.basic_match,
        "skill_match": r.skill_match, "quality_match": r.quality_match,
        "potential_match": r.potential_match,
        "matched_skills": _safe_json_list(r.matched_skills),
        "missing_skills": _safe_json_list(r.missing_skills),
        "eligible": r.eligible, "veto_reason": r.veto_reason or "",
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


def _action_row_to_dict(r: ActionPlan) -> Dict[str, Any]:
    try:
        items = json.loads(r.items_json)
    except (json.JSONDecodeError, TypeError):
        items = []
    return {
        "id": r.id, "student_id": r.student_id, "job_name": r.job_name,
        "portrait_version": r.portrait_version, "status": r.status,
        "items": items,
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "completed_at": r.completed_at.isoformat() if r.completed_at else "",
    }


def _safe_json_list(s: Optional[str]) -> List[Any]:
    if not s:
        return []
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
