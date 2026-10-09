"""Адаптивный тест на модели IRT 2PL.

Оценка навыка θ — апостериорное среднее на сетке (EAP) с нормальным априорным,
центрированным на заявленном грейде. Следующее задание берётся из трёх самых
информативных в текущей точке случайно: так один шаблон не достаётся всем.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .catalog import GRADE_MID, grade_of

GRID = [round(-4 + i * 0.05, 2) for i in range(161)]


def p_correct(theta: float, a: float, b: float) -> float:
    return 1.0 / (1.0 + math.exp(-a * (theta - b)))


def information(theta: float, a: float, b: float) -> float:
    p = p_correct(theta, a, b)
    return a * a * p * (1 - p)


def estimate(answers: list[dict], prior: float = 0.0) -> tuple[float, float]:
    """answers: [{a, b, score ∈ [0, 1]}]. Возвращает (θ, стандартная ошибка)."""
    weights = []
    for t in GRID:
        lik = math.exp(-((t - prior) ** 2) / 2)
        for x in answers:
            p = p_correct(t, x["a"], x["b"])
            lik *= x["score"] * p + (1 - x["score"]) * (1 - p)
        weights.append(lik)
    s = sum(weights) or 1e-12
    mean = sum(t * w for t, w in zip(GRID, weights)) / s
    var = sum((t - mean) ** 2 * w for t, w in zip(GRID, weights)) / s
    return mean, math.sqrt(max(var, 1e-9))


@dataclass(frozen=True)
class CatRules:
    min_items: int
    max_items: int
    target_se: float


RULES = {"full": CatRules(min_items=6, max_items=12, target_se=0.38), "express": CatRules(min_items=3, max_items=4, target_se=0.0)}


def should_stop(n: int, se: float, mode: str) -> bool:
    r = RULES[mode]
    return n >= r.max_items or (n >= r.min_items and se <= r.target_se)


def pick_next(theta: float, templates: list, used: set[str], rng: random.Random | None = None, k: int = 3):
    """Из неиспользованных шаблонов — k самых информативных, один из них случайно.
    Возвращает (шаблон, объяснение выбора)."""
    rng = rng or random.Random()
    left = [t for t in templates if t.id not in used]
    if not left:
        return None, []
    ranked = sorted(((information(theta, t.a, t.b), t) for t in left), key=lambda x: -x[0])[:k]
    _, choice = rng.choice(ranked)
    why = [{"id": t.id, "title": t.title, "info": round(i, 2)} for i, t in ranked]
    return choice, why


def verdict(claimed: int, theta: float, se: float) -> dict:
    """Итог против заявленного грейда. Принудительно грейд не понижается.
    Не прошёл — сразу предлагаем тест на ступень ниже. Уверенно выше границы —
    предлагаем отдельный тест на ступень выше; автоматически грейд не растёт."""
    measured = grade_of(theta)
    lo, hi = grade_of(theta - se), grade_of(theta + se)
    if measured >= claimed:
        return {"kind": "ok", "grade": claimed, "measured": measured, "offer_up": claimed < 4 and lo > claimed}
    return {"kind": "below", "grade": None, "measured": measured, "offer_down": max(0, claimed - 1), "close": hi >= claimed}


def prior_for(claimed: int) -> float:
    return GRADE_MID[claimed]
