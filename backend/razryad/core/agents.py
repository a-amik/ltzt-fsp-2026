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
        say("cand", f"Подтверждён тестом: «{GRADES[c['grade']]['name'].lower()}», оценка {c['theta']:.2f} ± {c['se']:.2f}.", cite=[{"src": "test", "text": "Тест платформы"}])
        g_ok = c["grade"] >= offer["grade"]
        crit["grade"] = {"name": "Грейд", "state": "ok" if g_ok else "part" if c["grade"] == offer["grade"] - 1 else "no", "note": GRADES[c["grade"]]["name"]}
    else:
        say("cand", f"Заявлен «{GRADES[c['claimed_grade']]['name'].lower()}», тестом пока не подтверждён.", nodata=True)
        crit["grade"] = {"name": "Грейд", "state": "nodata", "note": "не подтверждён"}

    say("emp", f"Вилка — {_rng(offer['salary_from'], offer['salary_to'])}. Укладываемся?")
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
    say("cand", "Вилка окончательная?")
    say("emp", "Вилка зафиксирована в приглашении; итог — внутри неё по результатам встречи.")

    vals = list(crit.values())
    no = [x for x in vals if x["state"] == "no"]
    other = [x for x in vals if x["state"] != "ok"]
    if no:
        verdict = {"kind": "no", "text": "Расхождение: " + ", ".join(x["name"].lower() for x in no)}
    elif other:
        verdict = {"kind": "part", "text": "Совпадает с оговорками: " + ", ".join(x["name"].lower() for x in other)}
    else:
        verdict = {"kind": "ok", "text": "Совпадает по всем критериям"}
    return {"steps": steps, "crit": vals, "verdict": verdict, "open": [x["name"] for x in vals if x["state"] in ("nodata", "part")]}
