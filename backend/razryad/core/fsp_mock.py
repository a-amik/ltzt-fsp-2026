"""Мок ФСП ID и реестра достижений.

Настоящих API и структуры данных организаторы не дают намеренно: наша схема —
черновик интеграции. Мок изображает OIDC-провайдер (authorize → code → token →
userinfo) и реестр достижений по номеру участника. Адрес провайдера — настройка
RZ_FSP_OIDC_ISSUER: когда ФСП поднимет тестовый стенд, мок выключается.
"""
from __future__ import annotations

import random

EVENTS = [
    ("Всероссийские соревнования по спортивному программированию (продуктовое)", "всероссийское", "продуктовое программирование"),
    ("Чемпионат России по спортивному программированию (алгоритмическое)", "всероссийское", "алгоритмическое программирование"),
    ("Кубок России по программированию беспилотных систем", "всероссийское", "программирование БАС"),
    ("Региональный этап, Приволжский ФО", "региональное", "продуктовое программирование"),
    ("Международный турнир ФСП «Код»", "международное", "алгоритмическое программирование"),
    ("Соревнования по информационной безопасности (CTF)", "всероссийское", "информационная безопасность"),
    ("Кубок Федерации по спортивному программированию", "всероссийское", "продуктовое программирование"),
]
RANKS = ["III разряд", "II разряд", "I разряд", "КМС", "МС"]

# Демонстрационные учётные записи ФСП ID.
ACCOUNTS = {
    "fsp-100001": {"sub": "fsp-100001", "name": "Амбарцум Амаякян", "email": "amik@fsp.example", "region": "Москва", "history": True},
    "fsp-100002": {"sub": "fsp-100002", "name": "Ольга Новикова", "email": "olga@fsp.example", "region": "Казань", "history": False},
    "fsp-100003": {"sub": "fsp-100003", "name": "Иван Петров", "email": "ivan@fsp.example", "region": "Санкт-Петербург", "history": True},
}


def achievements(sub: str) -> list[dict]:
    """Достижения участника из «реестра». Детерминированы номером участника."""
    acc = ACCOUNTS.get(sub)
    if not acc or not acc["history"]:
        return []
    r = random.Random(int(sub.split("-")[1]))
    n = 2 + int(r.random() * 3)
    out = []
    for _ in range(n):
        ev, level, disc = EVENTS[int(r.random() * len(EVENTS))]
        participants = 40 + int(r.random() * 300)
        place = 1 + int(r.random() * min(30, participants))
        out.append({"fsp_id": sub, "event": ev, "level": level, "discipline": disc, "year": 2022 + int(r.random() * 4),
                    "place": place, "participants": participants, "team": f"Команда №{1 + int(r.random() * 90)}",
                    "role": RANKS and ["капитан", "бэкенд", "фронтенд", "аналитик"][int(r.random() * 4)], "rank": RANKS[int(r.random() * len(RANKS))]})
    return out


def userinfo(sub: str) -> dict | None:
    acc = ACCOUNTS.get(sub)
    return {k: v for k, v in acc.items() if k != "history"} if acc else None
