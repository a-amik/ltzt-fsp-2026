"""Категория, ранжирование и объяснение выдачи.

Категория — пара «специализация × грейд». Внутри категории:
балл = 0,60 · оценка теста + 0,15 · совпадение стека + 0,10 · достижения ФСП + 0,10 · свежесть
+ 0,05 · связи (отзывы бывших коллег и рекомендации; решение участника 11.10.2026).
Достижения ФСП: все соревнования равны, считаются результативные (место), а не участие —
так советовала федерация 6 октября 2026. Кандидат без истории ФСП получает 0, не штраф.
Кандидат с неподтверждённым грейдом стоит в своей категории ниже всех подтверждённых.
Вилка работодателя обязательна, поэтому она и порядок: кандидат, чьи ожидания выше верха
вилки больше чем на 10 % (порог «расхождения» у агентов), стоит после тех, кто в неё укладывается.
Достижение ФСП в направлении, близком к специализации, засчитывается полностью, в остальных — 0,8.
"""
from __future__ import annotations

import re
from datetime import datetime

from .catalog import GRADES, SPECS

WEIGHTS = {"test": 0.60, "stack": 0.15, "fsp": 0.10, "fresh": 0.10, "social": 0.05}
BUDGET_SLACK = 0.10  # ожидания до 10 % выше вилки — «с оговоркой», выше — после укладывающихся
# Направления соревнований ФСП, близкие к специализации; остальные засчитываются с коэффициентом 0,8.
FSP_NEAR = {
    "backend": ["продуктовое", "алгоритмическое", "информационная безопасность"],
    "frontend": ["продуктовое"],
    "mobile": ["продуктовое", "бас"],
    "data": ["продуктовое", "алгоритмическое"],
    "ml": ["алгоритмическое", "продуктовое", "бас"],
    "devops": ["информационная безопасность", "продуктовое"],
}
FSP_FAR = 0.8

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


def fsp_near(e: dict, spec: str | None) -> bool:
    """Близко ли направление соревнования к специализации. Без дисциплины или специализации — близко."""
    d = (e.get("discipline") or "").lower()
    return not d or not spec or any(w in d for w in FSP_NEAR.get(spec, []))


def fsp_strength(achievements: list[dict], now_year: int | None = None, spec: str | None = None) -> float:
    """0…1. Результативность: место относительно числа участников; число результативных соревнований
    добавляет по 0,1. Давность — мягкий коэффициент 0,8 для событий старше трёх лет (необязателен по ФСП).
    Направление далёкое от специализации — коэффициент 0,8: все соревнования равны, но ближе — весомее."""
    now_year = now_year or datetime.utcnow().year
    scored = []
    for e in achievements:
        if e.get("hidden") or not e.get("place"):
            continue
        n = max(e.get("participants") or 1, e["place"])
        v = 1 - (e["place"] - 1) / n
        if now_year - e.get("year", now_year) > 3:
            v *= 0.8
        if not fsp_near(e, spec):
            v *= FSP_FAR
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
    express = not confirmed and bool(c.get("express")) and c.get("theta") is not None
    test = test_position(c["grade"], c["theta"]) if confirmed else test_position(c["claimed_grade"], c["theta"]) if express else 0.0
    stack = (len([s for s in need["stack"] if s in c["stack"]]) / len(need["stack"])) if need["stack"] else 0.5
    fsp = fsp_strength(c.get("fsp", []), spec=c.get("spec"))
    fresh = min(1.0, (c.get("fresh_tasks") or 0) / 3 + (c.get("task_score") or 0) * 0.5)
    social = c.get("social") or 0.0
    parts = {"test": test, "stack": stack, "fsp": fsp, "fresh": fresh, "social": social}
    total = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS)
    why = []
    if confirmed:
        g = GRADES[c["grade"]]["name"].lower()
        why.append({"src": "test", "text": f"Тест: {g} подтверждён, оценка {c['theta']:.2f} ± {c['se']:.2f}" + (" — в верхней трети категории" if test > 0.66 else "")})
    elif express:
        g = GRADES[c["claimed_grade"]]["name"].lower()
        why.append({"src": "test", "text": f"Экспресс-тест: {g}, оценка {c['theta']:.2f} ± {c['se']:.2f} — полным тестом не подтверждён"})
    else:
        why.append({"src": "warn", "text": "Грейд заявлен, тестом не подтверждён"})
    hit = [s for s in need["stack"] if s in c["stack"]]
    if hit:
        why.append({"src": "word", "text": f"Стек: {', '.join(hit)} из {len(need['stack'])} запрошенных"})
    res = [e for e in c.get("fsp", []) if e.get("place") and not e.get("hidden")]
    if res:
        e = min(res, key=lambda x: x["place"] / max(x.get("participants") or 1, x["place"]))
        why.append({"src": "fsp", "text": f"{e['place']} место из {e.get('participants') or '?'}, {e['event']}, {e['year']}"})
    if c.get("task_score") is not None:
        why.append({"src": "test", "text": "Ваше задание: оценка «" + {1: "сильно", 0.5: "годно", 0: "слабо"}.get(c["task_score"], "годно") + "»"})
    if c.get("fresh_tasks"):
        n = c["fresh_tasks"]
        word = "короткое задание" if n % 10 == 1 and n % 100 != 11 else "коротких задания" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "коротких заданий"
        why.append({"src": "test", "text": f"Решил {n} {word} работодателей за 90 дней"})
    if social > 0:
        why.append({"src": "word", "text": "Связи: бывшие коллеги взяли бы снова, есть рекомендации"})
    if need.get("salary_to") and c.get("salary") and c["salary"] > need["salary_to"]:
        why.append({"src": "warn", "text": f"Ожидания {c['salary']:,} ₽ выше вашей вилки зарплаты".replace(",", " ")})
    return {"total": round(total, 4), "parts": {k: round(v, 3) for k, v in parts.items()}, "why": why, "confirmed": confirmed, "express": express,
            "over_budget": over_budget(c, need)}


def over_budget(c: dict, need: dict) -> bool:
    """Ожидания выше верха вилки больше чем на 10 %. Скрытые ожидания или вилка без верха — не выше."""
    to, sal = need.get("salary_to"), c.get("salary")
    return bool(to and sal and sal > to * (1 + BUDGET_SLACK))


def rank(cands: list[dict], need: dict, filters: dict | None = None) -> list[dict]:
    """Жёсткий отбор по категории, затем ранжирование. Неподтверждённые — после подтверждённых,
    ожидания сильно выше вилки — после укладывающихся."""
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
    # Подтверждённые полным тестом, затем экспресс, затем только заявленные.
    out.sort(key=lambda x: (x["grade"] != need["grade"], 0 if x["s"]["confirmed"] else 1 if x["s"]["express"] else 2, x["s"]["over_budget"], -x["s"]["total"]))
    return out


# Что после числа означает не рубли: нагрузка, люди, сроки, объёмы.
NOT_MONEY = re.compile(r"\.?\s*(?:rps|rpm|qps|tps|req|запрос|пользовател|клиент|человек|сотрудник|разработчик|инженер|мс\b|ms\b|гб|gb|тб|tb|"
                       r"%|строк|лет|года|год\b|мес|раз\b|транзакц|заказ|сообщен|событ|подписчик|устройств|сервис|узл|нод)", re.I)
REMOTE = re.compile(r"удал[её]нн|удал[её]нк|remote|дистанц|из дома")
MENTOR = re.compile(r"(?:ментор|наставл|руковод|обуча|помога|курир|ревью)[а-яё]*(?:\s+[а-яё]+){0,2}\s*$")


def work_format(t: str) -> str | None:
    """Формат работы из текста: гибрид, если назван; иначе удалённо, если можно удалённо («удалёнка или офис» — тоже); иначе офис."""
    t = t.lower()
    if "гибрид" in t or "hybrid" in t:
        return "гибрид"
    if REMOTE.search(t):
        return "удалённо"
    if re.search(r"(?<![a-zа-яё])офис", t):
        return "офис"
    return None


def find_grade(t: str) -> int | None:
    """Грейд — самое раннее упоминание, кроме тех, кого человек будет учить: «менторить двух middle-разработчиков» — не грейд вакансии."""
    t = t.lower()
    best = None
    for i, ws in enumerate(GRADE_WORDS):
        for w in ws:
            for m in re.finditer(rf"(?<![a-zа-яё]){re.escape(w)}", t):
                if MENTOR.search(t[max(0, m.start() - 40):m.start()]):
                    continue
                if best is None or m.start() < best[0]:
                    best = (m.start(), i)
    return best[1] if best else None


_MULT = {"к": 1000, "k": 1000, "тыс": 1000, "т.р": 1000, "млн": 1_000_000, "m": 1_000_000}


def parse_money(t: str) -> list[int]:
    """Суммы в рублях: «300 000», «300000», «200к», «от 200 тыс.», «200–250 тыс», «1,2 млн».
    Множитель после второго числа диапазона относится к обоим: «200–250 тыс», «от 200 до 260 тыс»."""
    t = t.replace(" ", " ").replace(" ", " ")
    found = []
    for m in re.finditer(r"(\d{1,3}(?: \d{3})+|\d+(?:[.,]\d+)?)\s*(тыс|млн|т\.р|к|k|m)?(?![\wа-яё])", t):
        if NOT_MONEY.match(t, m.end()):  # «20 тыс. RPS», «из 7 человек», «от 4 лет» — не деньги
            continue
        num = float(m.group(1).replace(" ", "").replace(",", "."))
        found.append([num, _MULT.get(m.group(2) or "", 0), m.start(), m.end()])
    for i in range(len(found) - 2, -1, -1):
        a, b = found[i], found[i + 1]
        if not a[1] and b[1] and re.fullmatch(r"\s*(?:-|–|—|до)\s*", t[a[3]:b[2]]):
            a[1] = b[1]
    nums = [int(n * (k or 1)) for n, k, _, _ in found]
    return [n for n in nums if 20_000 <= n <= 2_000_000]


def parse_need(text: str) -> dict:
    """Разбор потребности своими словами. Заглушка на правилах; с моделью — структурированный вывод по той же схеме."""
    t = text.lower()
    spec_id = next((s for s, ws in SPEC_WORDS.items() if any(w in t for w in ws)), "backend")
    g = find_grade(t)
    grade = 2 if g is None else g
    pool = next(s for s in SPECS if s["id"] == spec_id)["stack"]
    stack = [s for s in pool if s.lower() in t] or pool[:2]
    nums = parse_money(t)
    lo, hi = (min(nums), max(nums)) if len(nums) > 1 else (nums[0], nums[0]) if nums else (None, None)
    if len(nums) == 1:  # «от 200к» — только низ вилки, «до 300 тыс» — только верх
        if re.search(r"(?<![\wа-яё])от\s+\d", t) and not re.search(r"(?<![\wа-яё])до\s+\d", t):
            hi = None
        elif re.search(r"(?<![\wа-яё])до\s+\d", t):
            lo = None
    return {"spec": spec_id, "grade": grade, "stack": stack,
            "salary_from": lo, "salary_to": hi,
            "work_format": work_format(t)}
