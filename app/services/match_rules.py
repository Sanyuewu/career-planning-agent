# -*- coding: utf-8 -*-
"""
人岗匹配业务规则 —— 单一事实源（四维权重 + 一票否决）。

设计：**纯函数、无重依赖**（不 import youtu/FAISS/career 服务），
让 REST 路径与 Agent 路径共用同一套规则（消除此前 veto 只在 tools 层、
REST 不一致的问题），且 CI 可直接对其单测而无需加载向量模型。

红线：`DEFAULT_WEIGHTS` 与算法是技术指标（赛题 line56），改动需显式批准。
"""

from typing import Dict, Optional, Tuple

# ── 红线：默认四维权重（基础/技能/素养/潜力综合打分）──────────────
DEFAULT_WEIGHTS: Dict[str, float] = {
    "basic": 0.25, "skill": 0.35, "quality": 0.25, "potential": 0.15,
}

# ── 权重预设（由 tools.ToolExecutor.WEIGHT_MAP 归位至此，匹配域唯一来源）──
WEIGHT_PRESETS: Dict[str, Dict[str, float]] = {
    "default":    DEFAULT_WEIGHTS,
    "general":    {"basic": 0.20, "skill": 0.40, "quality": 0.25, "potential": 0.15},
    "tech":       {"basic": 0.15, "skill": 0.55, "quality": 0.20, "potential": 0.10},
    "management": {"basic": 0.20, "skill": 0.20, "quality": 0.40, "potential": 0.20},
    "research":   {"basic": 0.20, "skill": 0.35, "quality": 0.15, "potential": 0.30},
    "operation":  {"basic": 0.20, "skill": 0.30, "quality": 0.35, "potential": 0.15},
}

# ── 基础要求一票否决：基础匹配低于阈值 → 总分封顶、标记 ineligible ──
BASIC_VETO_THRESHOLD = 50.0
VETO_CAP = 59.9   # 否决时把总分压到推荐阈值（60）以下


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    """取四键、缺失补默认；和不为 1 时按比例归一（自定义权重容错）。"""
    out = {k: float(weights.get(k, DEFAULT_WEIGHTS[k])) for k in DEFAULT_WEIGHTS}
    s = sum(out.values())
    if s > 0 and abs(s - 1.0) > 1e-6:
        out = {k: v / s for k, v in out.items()}
    return out


def resolve_weights(weights: Optional[Dict[str, float]] = None,
                    preset: Optional[str] = None) -> Dict[str, float]:
    """解析有效权重：自定义 weights 优先 → 预设名 → 默认。"""
    if isinstance(weights, dict) and weights:
        return _normalize(weights)
    if preset and preset in WEIGHT_PRESETS:
        return WEIGHT_PRESETS[preset]
    return DEFAULT_WEIGHTS


def combine_total(basic: float, skill: float, quality: float, potential: float,
                  weights: Optional[Dict[str, float]] = None) -> float:
    """四维加权综合分。weights 缺省用红线默认权重。"""
    w = weights or DEFAULT_WEIGHTS
    return (basic * w["basic"] + skill * w["skill"]
            + quality * w["quality"] + potential * w["potential"])


def apply_veto(basic: float, total: float) -> Tuple[float, bool, str]:
    """
    基础要求一票否决：basic < 阈值时，总分封顶到 VETO_CAP 并标记 ineligible。
    返回 (最终总分, 是否合格, 否决原因)。
    """
    if basic >= BASIC_VETO_THRESHOLD:
        return total, True, ""
    reason = (f"基础硬性要求不达标（基础匹配 {round(basic, 1)} < {BASIC_VETO_THRESHOLD}），"
              f"即使其他维度较高也不建议直接投递。")
    return min(total, VETO_CAP), False, reason
