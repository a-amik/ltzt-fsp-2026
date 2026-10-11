"""Предразговор агентов сторон — эмуляция по сценарию, не самостоятельные агенты.

Агент работодателя спрашивает о том, что требует вакансия; агент кандидата отвечает
только одобренными фактами и спрашивает в ответ о том, что важно кандидату. Каждый
ответ закрывает критерий: совпало, с оговоркой, расхождение или нет данных. Итог —
протокол, одинаковый для обеих сторон; решение за людьми. Контакты агенты не раскрывают.
С подключённой моделью реплики переписываются живее, но факты берутся из того же протокола
и после генерации сверяются с профилем: чего в профиле нет — «уточнит сам».
"""
from __future__ import annotations

import re

from .catalog import GRADES

# Настройка агента кандидата (Candidate.agent):
# importance — {pay|format|stack|grade|motive: low|high|stop}: «неважно» не портит итог, «стоп-фактор» даёт расхождение;
# stops — стоп-факторы из STOPS; asks — вопросы, которые агент задаёт компании всегда;
# brief — как искать, своими словами; auto_decline — отклонять приглашение со стоп-фактором самому.
CRIT_KEYS = {"pay": "Деньги", "format": "Формат", "stack": "Стек", "grade": "Грейд", "motive": "Мотивация"}
STOPS = {
    "office": "Офис без удалёнки",
    "duty": "Ночные дежурства",
    "outstaff": "Аутстаф и аутсорс",
    "grey": "Неофициальная зарплата",
    "longtest": "Тестовое дольше 4 часов",
}
STOP_Q = {
    "office": "Можно ли работать удалённо хотя бы часть недели?",
    "duty": "Есть ли ночные дежурства?",
    "outstaff": "Работа в своём продукте или на клиентов?",
    "grey": "Зарплата полностью официальная?",
    "longtest": "Будет ли тестовое задание и сколько оно занимает?",
}


def _stop_check(key: str, offer: dict) -> tuple[str | None, bool | None]:
    """Ответ агента компании на стоп-фактор по данным вакансии: (ответ, сработал ли). None — данных нет."""
    blob = " ".join(offer.get("tasks") or []) + " " + (offer.get("team") or "") + " " + (offer.get("field") or "")
    if key == "office":
        wf = offer.get("work_format")
        return (f"Формат — {wf}.", wf == "офис") if wf else (None, None)
    if key == "duty":
        return ("Да, есть дежурства.", True) if re.search(r"дежур", blob, re.I) else (None, None)
    if key == "outstaff":
        if re.search(r"аутстаф|аутсорс|интегратор|заказчик", blob, re.I):
            return ("Работа на проектах клиентов.", True)
        return (f"Свой продукт: {offer['field'].lower()}.", False) if offer.get("field") else (None, None)
    return None, None


def _answer(q: str, offer: dict) -> str | None:
    """Ответ на вопрос кандидата только из данных вакансии; чего там нет — None, вопрос уходит людям."""
    ql = q.lower()
    if re.search(r"кто\b.*руковод|команд", ql) and offer.get("team"):
        return offer["team"]
    if re.search(r"удал|друг\w* город|из дома", ql) and offer.get("work_format"):
        return {"удалённо": "Да, полностью удалённо.", "гибрид": "Гибрид: часть недели в офисе.", "офис": "Нет, работа в офисе."}.get(offer["work_format"])
    if re.search(r"задач|первые|онборд|чем занима", ql) and offer.get("tasks"):
        return "Первые задачи: " + "; ".join(offer["tasks"]) + "."
    return None


def _num(x: float) -> str:
    """Дробное по-русски: запятая и настоящий минус."""
    return f"{x:.2f}".replace(".", ",").replace("-", "−")


def _fact(c: dict, k: str):
    return next((f for f in c.get("facts", []) if f.get("k") == k and f.get("approved")), None)


def _rng(a: int | None, b: int | None) -> str:
    if a and b:
        return f"{a // 1000}–{b // 1000} тыс. ₽"
    if a or b:
        return f"{'от' if a else 'до'} {(a or b) // 1000} тыс. ₽"
    return "не указана"


def negotiate(c: dict, offer: dict) -> dict:
    """c — профиль кандидата (словарь), offer — {stack, grade, salary_from, salary_to, work_format, tasks, team}."""
    steps, crit = [], {}
    say = lambda who, text, **extra: steps.append({"who": who, "text": text, **extra})
    ag = c.get("agent") or {}
    imp = ag.get("importance") or {}
    if ag.get("brief"):
        say("cand", f"Сначала о главном для кандидата: {ag['brief'].strip().rstrip('.')}.", cite=[{"src": "word", "text": "Настройка агента"}])

    say("emp", f"Вакансия на {', '.join(offer['stack'])}. С чем из этого кандидат работал?")
    st = _fact(c, "Стек")
    if st:
        hit = [s for s in offer["stack"] if s in c["stack"]]
        miss = [s for s in offer["stack"] if s not in hit]
        say("cand", (f"{', '.join(hit)} — да." + (f" {', '.join(miss)} — нет." if miss else "")) if hit else "Из перечисленного — ничего.",
            cite=[{"src": st["src"], "text": "Стек"}])
        need = -(-len(offer["stack"]) * 2 // 3)
        crit["stack"] = {"name": "Стек", "state": "ok" if len(hit) >= need else "part" if hit else "no", "note": f"{len(hit)} из {len(offer['stack'])}"}
    else:
        say("cand", "Стек кандидат не открыл.", nodata=True)
        crit["stack"] = {"name": "Стек", "state": "nodata", "note": "не открыт"}

    say("emp", f"Нужен уровень не ниже «{GRADES[offer['grade']]['name'].lower()}».")
    if c.get("grade") is not None:
        say("cand", f"Подтверждён тестом: «{GRADES[c['grade']]['name'].lower()}», оценка {_num(c['theta'])} ± {_num(c['se'])}.", cite=[{"src": "test", "text": "Тест платформы"}])
        g_ok = c["grade"] >= offer["grade"]
        crit["grade"] = {"name": "Грейд", "state": "ok" if g_ok else "part" if c["grade"] == offer["grade"] - 1 else "no", "note": GRADES[c["grade"]]["name"]}
    else:
        say("cand", f"Заявлен «{GRADES[c['claimed_grade']]['name'].lower()}», тестом пока не подтверждён.", nodata=True)
        crit["grade"] = {"name": "Грейд", "state": "nodata", "note": "не подтверждён"}

    say("emp", f"Вилка зарплаты — {_rng(offer['salary_from'], offer['salary_to'])}. Укладываемся?")
    s = c.get("salary")
    if s and c.get("privacy", {}).get("salary", True) and not offer.get("salary_to"):
        # «от 200 тыс.»: верха нет — расхождения по деньгам быть не может, обсуждается сумма
        say("cand", f"Ожидания — {s // 1000} тыс. ₽; верх вилки не задан.", cite=[{"src": "word", "text": "Ожидания"}])
        low = offer.get("salary_from") and s < offer["salary_from"]
        crit["pay"] = {"name": "Деньги", "state": "ok" if low else "part", "note": "ниже низа вилки" if low else "верх не задан"}
    elif s and c.get("privacy", {}).get("salary", True):
        over = s / offer["salary_to"] - 1
        say("cand", "Да, ожидания внутри вилки." if over <= 0 else f"Ожидания выше вилки на {round(over * 100)} %.", cite=[{"src": "word", "text": "Ожидания"}])
        crit["pay"] = {"name": "Деньги", "state": "ok" if over <= 0 else "part" if over <= 0.1 else "no", "note": "внутри вилки" if over <= 0 else f"+{round(over * 100)} %"}
    else:
        say("cand", "Ожидания кандидат не открыл.", nodata=True)
        crit["pay"] = {"name": "Деньги", "state": "nodata", "note": "не открыты"}

    say("emp", f"Формат — {offer.get('work_format') or 'по договорённости'}.")
    ff = _fact(c, "Формат")
    if ff and offer.get("work_format"):
        v, w = ff["v"], offer["work_format"]
        state = "ok" if v == w or w == "удалённо" else "no" if v == "удалённо" and w == "офис" else "part"
        say("cand", {"ok": f"Подходит: кандидат указал «{v}».", "part": f"Кандидат указал «{v}» — обсуждаемо.", "no": f"Кандидат указал «{v}» — расхождение."}[state], cite=[{"src": ff["src"], "text": "Формат"}])
        crit["format"] = {"name": "Формат", "state": state, "note": v}
    else:
        say("cand", "Формат не открыт.", nodata=True)
        crit["format"] = {"name": "Формат", "state": "nodata", "note": "—"}

    if offer["grade"] >= 3:
        say("emp", "Был ли опыт техлидства или наставничества?")
        rf = _fact(c, "Роль в команде")
        if rf:
            say("cand", rf["v"][0].upper() + rf["v"][1:] + ".", cite=[{"src": rf["src"], "text": "Роль"}])
            crit["role"] = {"name": "Роль", "state": "ok" if re.search(r"лид|настав|владел", rf["v"]) else "part", "note": rf["v"]}
        else:
            say("cand", "В одобренных фактах нет — уточнит сам.", nodata=True)
            crit["role"] = {"name": "Роль", "state": "nodata", "note": "—"}

    say("cand", "Какие задачи в первые три месяца?")
    tasks = offer.get("tasks") or []
    say("emp", "; ".join(tasks) + "." if tasks else "В описании нет — рекрутер расскажет на встрече.", **({} if tasks else {"nodata": True}))
    why = _fact(c, "Почему ищет")
    if why:
        say("cand", f"Кандидату важно: {why['v']}. Это про вас?")
        blob = " ".join(tasks) + " " + (offer.get("team") or "")
        fit = bool(re.search(r"нагруз|запрос|секунд|млн", blob)) if "нагруз" in why["v"] else offer["grade"] >= 2 if re.search(r"техлид|рост", why["v"]) else True
        say("emp", f"Да: {offer.get('team') or 'команда расскажет на встрече'}" if fit else f"Прямо не обещаем. {offer.get('team') or ''}")
        crit["motive"] = {"name": "Мотивация", "state": "ok" if fit else "part", "note": why["v"]}
    # Стоп-факторы и обязательные вопросы кандидата: агент задаёт их в каждом разговоре.
    asks, stops_hit = [], []
    for key in ag.get("stops") or []:
        if key not in STOPS:
            continue
        a, hit = _stop_check(key, offer)
        say("cand", STOP_Q[key], ask=True)
        if a is None:
            say("emp", "В вакансии ответа нет — уточнит рекрутер.", nodata=True)
        else:
            say("emp", a)
        if hit:
            stops_hit.append(STOPS[key])
        asks.append({"q": STOP_Q[key], "a": a, "stop": True, "hit": bool(hit)})
    for q in ag.get("asks") or []:
        a = _answer(q, offer)
        say("cand", q, ask=True)
        if a:
            say("emp", a)
        else:
            say("emp", "В вакансии ответа нет — уточнит рекрутер.", nodata=True)
        asks.append({"q": q, "a": a})
    say("cand", "Вилка зарплаты окончательная?")
    say("emp", "Вилка зарплаты зафиксирована в приглашении; итог — внутри неё по результатам встречи.")

    # Важность критериев по настройке кандидата: «неважно» не портит итог, «стоп-фактор» его решает.
    for k, x in crit.items():
        lvl = imp.get(k)
        x["imp"] = lvl or "high"
        if lvl == "stop" and x["state"] == "no":
            stops_hit.append(x["name"])
    vals = list(crit.values())
    no = [x for x in vals if x["state"] == "no" and x["imp"] != "low"]
    other = [x for x in vals if x["state"] != "ok" and x["imp"] != "low"]
    if stops_hit:
        verdict = {"kind": "no", "text": "Стоп-фактор кандидата: " + ", ".join(dict.fromkeys(s.lower() for s in stops_hit))}
    elif no:
        verdict = {"kind": "no", "text": "Расхождение: " + ", ".join(x["name"].lower() for x in no)}
    elif other:
        verdict = {"kind": "part", "text": "Совпадает с оговорками: " + ", ".join(x["name"].lower() for x in other)}
    else:
        verdict = {"kind": "ok", "text": "Совпадает по всем критериям"}
    return {"steps": steps, "crit": vals, "verdict": verdict, "asks": asks, "stops": list(dict.fromkeys(stops_hit)),
            "open": [x["name"] for x in vals if x["state"] in ("nodata", "part") and x["imp"] != "low"] + [a["q"] for a in asks if a["a"] is None]}
