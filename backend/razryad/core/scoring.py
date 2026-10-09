"""Категория, ранжирование и объяснение выдачи.

Категория — пара «специализация × грейд». Внутри категории:
балл = 0,60 · оценка теста + 0,20 · совпадение стека + 0,10 · достижения ФСП + 0,10 · свежесть.
Достижения ФСП: все соревнования равны, считаются результативные (место), а не участие —
так советовала федерация 6 октября 2026. Кандидат без истории ФСП получает 0, не штраф.
Кандидат с неподтверждённым грейдом стоит в своей категории ниже всех подтверждённых.
"""
from __future__ import annotations

import re
from datetime import datetime

from .catalog import GRADES, SPECS

WEIGHTS = {"test": 0.60, "stack": 0.20, "fsp": 0.10, "fresh": 0.10}

SPEC_WORDS = {
    "backend": ["бэкенд", "бекенд", "backend", "сервер", "api"],
    "frontend": ["фронтенд", "фронт", "frontend", "react", "интерфейс"],
    "mobile": ["мобил", "ios", "android", "kotlin", "swift"],
    "data": ["данных", "аналитик", "dwh", "хранилищ", "clickhouse"],
    "ml": ["ml", "машинн", "модел", "нейросет"],
    "devops": ["devops", "kubernetes", "инфраструкт", "sre"],
}
GRADE_WORDS = [["стажёр", "стажер", "intern"], ["младш", "junior", "джун"], ["средн", "middle", "мидл"],
               ["старш", "senior", "синьор", "сеньор"], ["ведущ", "lead", "лид"]]


def fsp_strength(achievements: list[dict], now_year: int | None = None) -> float:
    """0…1. Результативность: место относительно числа участников; число результативных соревнований
    добавляет по 0,1. Давность — мягкий коэффициент 0,8 для событий старше трёх лет (необязателен по ФСП)."""
    now_year = now_year or datetime.utcnow().year
    scored = []
    for e in achievements:
        if e.get("hidden") or not e.get("place"):
            continue
        n = max(e.get("participants") or 1, e["place"])
        v = 1 - (e["place"] - 1) / n
        if now_year - e.get("year", now_year) > 3:
            v *= 0.8
        scored.append(v)
    if not scored:
        return 0.0
    return min(1.0, max(scored) + 0.1 * (len(scored) - 1))


def test_position(grade: int, theta: float) -> float:
    """Положение θ внутри отрезка грейда, 0…1 (крайние грейды обрезаны по ±2,6)."""
    g = GRADES[grade]
    lo, hi = max(g["lo"], -2.6), min(g["hi"], 2.6)
    return max(0.0, min(1.0, (theta - lo) / (hi - lo)))


def score_candidate(c: dict, need: dict) -> dict:
    """c: {grade, claimed_grade, theta, se, stack, fsp: [...], fresh_tasks, task_score, salary}."""
    confirmed = c.get("grade") is not None
    test = test_position(c["grade"], c["theta"]) if confirmed else 0.0
    stack = (len([s for s in need["stack"] if s in c["stack"]]) / len(need["stack"])) if need["stack"] else 0.5
    fsp = fsp_strength(c.get("fsp", []))
    fresh = min(1.0, (c.get("fresh_tasks") or 0) / 3 + (c.get("task_score") or 0) * 0.5)
    parts = {"test": test, "stack": stack, "fsp": fsp, "fresh": fresh}
    total = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS)
    why = []
    if confirmed:
        g = GRADES[c["grade"]]["name"].lower()
        why.append({"src": "test", "text": f"Тест: {g} подтверждён, оценка {c['theta']:.2f} ± {c['se']:.2f}" + (" — в верхней трети категории" if test > 0.66 else "")})
    else:
        why.append({"src": "warn", "text": "Грейд заявлен, тестом не подтверждён"})
    hit = [s for s in need["stack"] if s in c["stack"]]
    if hit:
        why.append({"src": "test", "text": f"Стек: {', '.join(hit)} из {len(need['stack'])} запрошенных"})
    res = [e for e in c.get("fsp", []) if e.get("place") and not e.get("hidden")]
    if res:
        e = min(res, key=lambda x: x["place"] / max(x.get("participants") or 1, x["place"]))
        why.append({"src": "fsp", "text": f"{e['place']} место из {e.get('participants') or '?'}, {e['event']}, {e['year']}"})
    if c.get("task_score") is not None:
        why.append({"src": "test", "text": "Ваше задание: оценка «" + {1: "сильно", 0.5: "годно", 0: "слабо"}.get(c["task_score"], "годно") + "»"})
    if c.get("fresh_tasks"):
        why.append({"src": "test", "text": f"Решил {c['fresh_tasks']} коротких задания работодателей за 90 дней"})
    if need.get("salary_to") and c.get("salary") and c["salary"] > need["salary_to"]:
        why.append({"src": "warn", "text": f"Ожидания {c['salary']:,} ₽ выше вашей вилки".replace(",", " ")})
    return {"total": round(total, 4), "parts": {k: round(v, 3) for k, v in parts.items()}, "why": why, "confirmed": confirmed}


def rank(cands: list[dict], need: dict, filters: dict | None = None) -> list[dict]:
    """Жёсткий отбор по категории, затем ранжирование. Неподтверждённые — после подтверждённых."""
    f = filters or {}
    grades = [need["grade"] - 1, need["grade"], need["grade"] + 1] if f.get("near") else [need["grade"]]
    out = []
    for c in cands:
        g = c["grade"] if c.get("grade") is not None else c.get("claimed_grade")
        if c["spec"] != need["spec"] or g not in grades:
            continue
        if f.get("fsp_only") and not [e for e in c.get("fsp", []) if not e.get("hidden")]:
            continue
        if f.get("confirmed_only") and c.get("grade") is None:
            continue
        if f.get("work_format") and c.get("work_format") != f["work_format"]:
            continue
        if f.get("must_stack") and not all(s in c["stack"] for s in need["stack"]):
            continue
        out.append({"c": c, "s": score_candidate(c, need), "grade": g})
    out.sort(key=lambda x: (x["grade"] != need["grade"], not x["s"]["confirmed"], -x["s"]["total"]))
    return out


def parse_need(text: str) -> dict:
    """Разбор потребности своими словами. Заглушка на правилах; с моделью — структурированный вывод по той же схеме."""
    t = text.lower()
    spec_id = next((s for s, ws in SPEC_WORDS.items() if any(w in t for w in ws)), "backend")
    grade = next((i for i, ws in enumerate(GRADE_WORDS) if any(w in t for w in ws)), 2)
    pool = next(s for s in SPECS if s["id"] == spec_id)["stack"]
    stack = [s for s in pool if s.lower() in t] or pool[:2]
    nums = [int(x.replace(" ", "").replace(" ", "")) for x in re.findall(r"\d[\d  ]{4,}", text)]
    nums = [n for n in nums if 20_000 <= n <= 2_000_000]
    fmt = next((w for w in ["удалённо", "удаленно", "гибрид", "офис"] if w in t), None)
    return {"spec": spec_id, "grade": grade, "stack": stack,
            "salary_from": min(nums) if nums else None, "salary_to": max(nums) if len(nums) > 1 else (nums[0] if nums else None),
            "work_format": "удалённо" if fmt == "удаленно" else fmt}
