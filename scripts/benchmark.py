# -*- coding: utf-8 -*-
"""
持久化基准测试系统

功能：
1. 从 data/eval/ground_truth.jsonl 读取系统性测试用例（自动生成，覆盖51个真实岗位）
2. 运行全套准确率测试（技能F1 / 技能对is_match / 置信度校准）
3. 将结果追加到 data/eval/benchmarks.jsonl（每次运行一条记录）
4. 与上次运行对比，输出回归报告
5. 将置信度→经验准确率的映射写入 data/eval/confidence_cal.json
   （供 match_service_optimized 在运行时读取，实现数据驱动的置信度展示）

用法：
  python scripts/benchmark.py
  python scripts/benchmark.py --generate   # 先重新生成 ground_truth 再测试
  python scripts/benchmark.py --history    # 只打印历史趋势
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.services.match_service_optimized import OptimizedSkillMatcher

matcher = OptimizedSkillMatcher()

EVAL_DIR = ROOT / "data" / "eval"
BENCHMARKS_FILE = EVAL_DIR / "benchmarks.jsonl"
CONFIDENCE_CAL_FILE = EVAL_DIR / "confidence_cal.json"
GROUND_TRUTH_FILE = EVAL_DIR / "ground_truth.jsonl"
SKILL_PAIRS_FILE = EVAL_DIR / "skill_pairs.jsonl"


# ── 评估工具 ──────────────────────────────────────────────────────────────────

def _set(lst): return {s.lower() for s in (lst or [])}


def eval_match(result, exp_matched: list, exp_gap: list) -> dict:
    got_matched = _set(result.matched_skills)
    got_gap = _set(result.gap_skills)
    exp_m = _set(exp_matched)
    exp_g = _set(exp_gap)

    tp_m = len(got_matched & exp_m)
    fp_m = len(got_matched - exp_m)
    fn_m = len(exp_m - got_matched)

    p = tp_m / (tp_m + fp_m) if (tp_m + fp_m) > 0 else 1.0
    r = tp_m / (tp_m + fn_m) if (tp_m + fn_m) > 0 else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 1.0

    return {"p": p, "r": r, "f1": f1, "confidence": result.confidence}


# ── 测试套件 ──────────────────────────────────────────────────────────────────

def _get_industry(job_name: str, industry_map: dict) -> str:
    """通过 job_name 获取行业分类"""
    return industry_map.get(job_name, "其他")


def _load_industry_map() -> dict:
    profiles_path = ROOT / "data" / "job_profiles.json"
    result = {}
    try:
        with open(profiles_path, encoding="utf-8") as f:
            profiles = json.load(f)
        for p in profiles:
            result[p.get("岗位名称", "")] = p.get("行业分类", p.get("所属行业", "其他"))
    except Exception:
        pass
    return result


def run_ground_truth_suite() -> dict:
    """
    套件1：从 ground_truth.jsonl 运行系统性测试（来自51个真实岗位）
    返回按类型分组的指标
    """
    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(f"{GROUND_TRUTH_FILE} 不存在，请先运行 generate_ground_truth.py")

    cases = []
    with open(GROUND_TRUTH_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))

    industry_map = _load_industry_map()
    by_type: dict = defaultdict(list)
    by_industry: dict = defaultdict(list)
    conf_buckets: dict = defaultdict(list)
    industry_conf_buckets: dict = defaultdict(lambda: defaultdict(list))

    for case in cases:
        result = matcher.match_skills(case["student_skills"], case["job_skills"])
        m = eval_match(result, case["expected_matched"], case["expected_gap"])
        m["type"] = case["type"]
        m["job"] = case["job"]
        industry = _get_industry(case["job"], industry_map)
        m["industry"] = industry
        by_type[case["type"]].append(m)
        by_industry[industry].append(m)

        # 置信度桶（全局 + 行业）
        conf = result.confidence
        bucket = "high" if conf >= 0.8 else ("mid" if conf >= 0.6 else "low")
        conf_buckets[bucket].append(m["f1"])
        industry_conf_buckets[industry][bucket].append(m["f1"])

    summary_by_type = {}
    all_f1 = []
    for t, items in by_type.items():
        f1s = [x["f1"] for x in items]
        avg_f1 = sum(f1s) / len(f1s)
        summary_by_type[t] = {
            "n": len(items),
            "avg_f1": round(avg_f1, 4),
            "min_f1": round(min(f1s), 4),
            "pass_rate_80": round(sum(1 for f in f1s if f >= 0.8) / len(f1s), 4),
        }
        all_f1.extend(f1s)

    # 行业维度汇总
    summary_by_industry = {}
    for ind, items in by_industry.items():
        f1s = [x["f1"] for x in items]
        summary_by_industry[ind] = {
            "n": len(items),
            "avg_f1": round(sum(f1s) / len(f1s), 4),
            "pass_rate_80": round(sum(1 for f in f1s if f >= 0.8) / len(f1s), 4),
        }

    overall_f1 = sum(all_f1) / len(all_f1) if all_f1 else 0.0

    # 置信度校准数据（全局）
    calibration = {}
    for bucket, f1s in conf_buckets.items():
        calibration[bucket] = {
            "n": len(f1s),
            "empirical_accuracy": round(sum(f1s) / len(f1s), 4),
            "min_accuracy": round(min(f1s), 4),
            "source": "benchmark",
        }

    # 行业维度置信度校准
    industry_calibration = {}
    for ind, buckets in industry_conf_buckets.items():
        industry_calibration[ind] = {}
        for bucket, f1s in buckets.items():
            if f1s:
                industry_calibration[ind][bucket] = {
                    "n": len(f1s),
                    "empirical_accuracy": round(sum(f1s) / len(f1s), 4),
                }

    return {
        "total": len(cases),
        "overall_f1": round(overall_f1, 4),
        "by_type": summary_by_type,
        "by_industry": summary_by_industry,
        "calibration": calibration,
        "industry_calibration": industry_calibration,
    }


def run_skill_pairs_suite() -> dict:
    """
    套件2：从 skill_pairs.jsonl 测试技能对 is_match 精度
    验证同义词识别正确率 + 负例不误匹配
    """
    if not SKILL_PAIRS_FILE.exists():
        raise FileNotFoundError(f"{SKILL_PAIRS_FILE} 不存在")

    pairs = []
    with open(SKILL_PAIRS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))

    tp = fp = tn = fn = 0
    errors = []

    for pair in pairs:
        a, b = pair["skill_a"], pair["skill_b"]
        expected = pair["is_match"]
        score, _ = matcher._compute_match_score(a.lower(), b.lower())
        predicted = score >= 0.6

        if expected and predicted:
            tp += 1
        elif expected and not predicted:
            fn += 1
            errors.append({"pair": (a, b), "expected": True, "score": score, "reason": pair.get("reason")})
        elif not expected and predicted:
            fp += 1
            errors.append({"pair": (a, b), "expected": False, "score": score, "reason": pair.get("reason")})
        else:
            tn += 1

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 1.0  # 负例识别率（反幻觉）

    return {
        "total": total,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "specificity": round(specificity, 4),  # 反幻觉精度
        "errors": errors,
    }


# ── 回归对比 ──────────────────────────────────────────────────────────────────

def load_last_benchmark() -> Optional[dict]:
    if not BENCHMARKS_FILE.exists():
        return None
    lines = [l.strip() for l in BENCHMARKS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) < 2:
        return None
    return json.loads(lines[-2])  # 上一次（最新的是当前运行追加前的最后一条）


def regression_report(current: dict, previous: Optional[dict]):
    if not previous:
        print("  (首次运行，无对比基线)")
        return

    fields = [
        ("技能匹配 F1",    "gt_suite.overall_f1",    0.005),
        ("技能对精确率",    "pair_suite.precision",   0.01),
        ("技能对反幻觉",    "pair_suite.specificity", 0.01),
    ]

    def _get(d, path):
        for k in path.split("."):
            if d is None:
                return None
            d = d.get(k) if isinstance(d, dict) else None
        return d

    regressions = []
    improvements = []
    for label, path, threshold in fields:
        cur = _get(current, path)
        prev = _get(previous, path)
        if cur is None or prev is None:
            continue
        delta = cur - prev
        if delta < -threshold:
            regressions.append(f"  ❌ {label}: {prev:.1%} → {cur:.1%}  (↓{abs(delta):.1%})")
        elif delta > threshold:
            improvements.append(f"  ✅ {label}: {prev:.1%} → {cur:.1%}  (↑{delta:.1%})")

    if regressions:
        print("【回归警告】")
        for r in regressions:
            print(r)
    if improvements:
        print("【改进】")
        for r in improvements:
            print(r)
    if not regressions and not improvements:
        print("  ✅ 无显著变化")


# ── 持久化 ────────────────────────────────────────────────────────────────────

def persist_results(gt_suite: dict, pair_suite: dict):
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "gt_suite": gt_suite,
        "pair_suite": {k: v for k, v in pair_suite.items() if k != "errors"},  # 不存储详细错误
    }
    BENCHMARKS_FILE.parent.mkdir(exist_ok=True)
    with open(BENCHMARKS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def persist_calibration(calibration: dict, industry_calibration: dict = None):
    """
    将置信度→经验准确率写入 confidence_cal.json（全局 + 行业细分）。
    accuracy_service 在运行时读取此文件，提供数据驱动的准确率展示。
    """
    existing = {}
    if CONFIDENCE_CAL_FILE.exists():
        try:
            with open(CONFIDENCE_CAL_FILE, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    existing["_generated"] = datetime.utcnow().isoformat()
    existing["_description"] = "经验置信度校准：基于benchmark实测F1 + 用户DB反馈，key为置信度桶(high/mid/low)"
    existing["buckets"] = calibration
    if industry_calibration:
        existing["industry_buckets"] = industry_calibration

    with open(CONFIDENCE_CAL_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


# ── 历史趋势 ──────────────────────────────────────────────────────────────────

def print_history():
    if not BENCHMARKS_FILE.exists():
        print("无历史记录")
        return
    lines = [l.strip() for l in BENCHMARKS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        print("无历史记录")
        return

    print(f"\n{'日期':<22} {'用例数':>6} {'总体F1':>8} {'技能对F1':>10} {'反幻觉':>8}")
    print("-" * 60)
    for line in lines[-10:]:  # 最近10次
        r = json.loads(line)
        ts = r["timestamp"][:16]
        n = r["gt_suite"]["total"]
        gf = r["gt_suite"]["overall_f1"]
        pf = r["pair_suite"].get("f1", 0)
        sp = r["pair_suite"].get("specificity", 0)
        print(f"{ts:<22} {n:>6} {gf:>8.1%} {pf:>10.1%} {sp:>8.1%}")


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="先重新生成 ground_truth 再测试")
    parser.add_argument("--history", action="store_true", help="只打印历史趋势")
    parser.add_argument("--update-from-db", action="store_true", help="从数据库反馈更新校准（需要运行中的后端）")
    args = parser.parse_args()

    if args.history:
        print_history()
        return

    if args.update_from_db:
        print("从数据库反馈更新校准...")
        import asyncio
        from app.db import get_db_session
        from app.services.accuracy_service import accuracy_service
        async def _update():
            async with get_db_session() as db:
                result = await accuracy_service.update_calibration_from_db(db)
            print(f"更新结果: {result}")
        asyncio.run(_update())
        return

    if args.generate or not GROUND_TRUTH_FILE.exists():
        print("正在生成 Ground Truth...")
        import importlib.util
        spec = importlib.util.spec_from_file_location("gen", ROOT / "scripts" / "generate_ground_truth.py")
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        gen.main()
        print()

    print("=" * 70)
    print("  职业规划智能体 — 持久化基准测试")
    print(f"  运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    t0 = time.time()

    # ── 套件1：系统性 Ground Truth ────────────────────────────────────────────
    print("\n▶ 套件1：系统性技能匹配（来自51个真实岗位，自动生成）")
    gt = run_ground_truth_suite()

    print(f"\n  总用例: {gt['total']}  |  总体F1: {gt['overall_f1']:.1%}")
    print(f"\n  {'用例类型':<20} {'用例数':>6} {'均F1':>8} {'最低F1':>8} {'≥80%通过率':>12}")
    print("  " + "-" * 58)
    for t, s in gt["by_type"].items():
        print(f"  {t:<20} {s['n']:>6} {s['avg_f1']:>8.1%} {s['min_f1']:>8.1%} {s['pass_rate_80']:>12.1%}")

    print(f"\n  行业维度准确率：")
    print(f"  {'行业':<12} {'用例数':>6} {'均F1':>8} {'≥80%通过率':>12}")
    print("  " + "-" * 42)
    for ind, s in sorted(gt["by_industry"].items()):
        flag = "✅" if s["avg_f1"] >= 0.80 else "❌"
        print(f"  {flag} {ind:<10} {s['n']:>6} {s['avg_f1']:>8.1%} {s['pass_rate_80']:>12.1%}")

    print(f"\n  置信度校准（经验F1）：")
    for bucket, info in gt["calibration"].items():
        label = {"high": "高(≥0.8)", "mid": "中(0.6-0.8)", "low": "低(<0.6)"}[bucket]
        print(f"    {label:<12}: n={info['n']:>4}, 经验F1={info['empirical_accuracy']:.1%}, 最低={info['min_accuracy']:.1%}")

    # ── 套件2：技能对精度 ──────────────────────────────────────────────────────
    print("\n▶ 套件2：技能对 is_match 精度（同义词+负例）")
    pair = run_skill_pairs_suite()

    print(f"\n  总对数: {pair['total']}  |  TP={pair['tp']} FP={pair['fp']} TN={pair['tn']} FN={pair['fn']}")
    print(f"  精确率: {pair['precision']:.1%}  召回率: {pair['recall']:.1%}  F1: {pair['f1']:.1%}")
    print(f"  反幻觉精度（负例识别率）: {pair['specificity']:.1%}")

    if pair["errors"]:
        print(f"\n  错误案例 ({len(pair['errors'])} 个)：")
        for e in pair["errors"][:5]:
            exp_label = "应匹配" if e["expected"] else "不应匹配"
            print(f"    {e['pair'][0]} ↔ {e['pair'][1]}: {exp_label} 但 score={e['score']:.2f} [{e['reason']}]")

    # ── 回归对比 ──────────────────────────────────────────────────────────────
    prev = load_last_benchmark()
    current_record = persist_results(gt, pair)

    print("\n▶ 与上次运行对比：")
    regression_report(current_record, prev)

    # ── 持久化置信度校准（全局 + 行业细分）────────────────────────────────────
    persist_calibration(gt["calibration"], gt.get("industry_calibration", {}))

    elapsed = time.time() - t0
    print(f"\n  总耗时: {elapsed:.1f}s")
    print(f"  结果已追加: {BENCHMARKS_FILE}")
    print(f"  置信度校准已写入: {CONFIDENCE_CAL_FILE}")

    # 最终达标判断
    ok = (
        gt["overall_f1"] >= 0.80
        and pair["f1"] >= 0.80
        and pair["specificity"] >= 0.90
    )
    if ok:
        print("\n🎉 所有核心指标达标")
    else:
        print("\n⚠️  部分指标未达标，见上方详情")

    print("\n" + "=" * 70)
    print("  历史趋势（最近5次）：")
    print_history()


if __name__ == "__main__":
    main()
