# -*- coding: utf-8 -*-
"""
评测指标 —— 纯函数，无重依赖（不 import youtu/FAISS/LLM）。

供内部评测流程与轻量检查共用，避免指标公式漂移。
集合级 P/R/F1 + 画像抽取的同义容错召回。
诚实原则：指标只算真实预测 vs gold，不写死数字。
"""

from typing import Iterable, List, Set, Tuple


def _norm(s: str) -> str:
    return str(s).strip().lower().replace(".js", "").replace(" ", "")


def to_set(skills: Iterable[str]) -> Set[str]:
    return {_norm(s) for s in skills if s and str(s).strip()}


def set_prf(expected: Iterable[str], predicted: Iterable[str]) -> Tuple[float, float, float]:
    """精确集合 P/R/F1（用于匹配评测：预测命中的技能 vs 应命中的技能）。"""
    e, p = to_set(expected), to_set(predicted)
    if not e and not p:
        return 1.0, 1.0, 1.0
    tp = len(e & p)
    precision = tp / len(p) if p else (1.0 if not e else 0.0)
    recall = tp / len(e) if e else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def _hits_tolerant(expected_item: str, predicted: Set[str]) -> bool:
    """同义/子串容错：'vue' 命中 'vue.js'，'js' 命中 'javascript' 等。"""
    e = _norm(expected_item)
    if e in predicted:
        return True
    return any(e in p or p in e for p in predicted if p)


def recall_tolerant(expected: Iterable[str], predicted: Iterable[str]) -> float:
    """容错召回（用于画像抽取：简历明确写了的技能，是否被抽出来——允许命名归一）。"""
    e = [x for x in expected if x and str(x).strip()]
    if not e:
        return 1.0
    p = to_set(predicted)
    hit = sum(1 for x in e if _hits_tolerant(x, p))
    return hit / len(e)


def precision_tolerant(expected: Iterable[str], predicted: Iterable[str]) -> float:
    """容错精确率：抽出来的技能里，有多少是简历里真有的——**抓 LLM 幻觉**（凭空多抽）。"""
    p = [x for x in predicted if x and str(x).strip()]
    if not p:
        return 1.0
    e = to_set(expected)
    hit = sum(1 for x in p if _hits_tolerant(x, e))
    return hit / len(p)


def prf_tolerant(expected: Iterable[str], predicted: Iterable[str]) -> Tuple[float, float, float]:
    """容错 P/R/F1（画像抽取用：召回看漏没漏，精确看有没有幻觉）。"""
    pr = precision_tolerant(expected, predicted)
    rc = recall_tolerant(expected, predicted)
    f1 = (2 * pr * rc / (pr + rc)) if (pr + rc) else 0.0
    return pr, rc, f1


def mean(xs: List[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0
