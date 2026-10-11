"""Отзывы бывших коллег, рекомендации, сводка о компании и доля «Связи» в балле.

Решения участника 11.10.2026: связи весят 5 % балла; кандидат видит, сколько
отзывов о нём собрано и сколько агентов опрошено, но не сами отзывы; открытые
отзывы о компании берём оценкой и числом, без текстов; порога показа нет.
Коллег находит агент по совпадению мест работы в двух профилях — кандидат
их не выбирает. Компания в запросе не называется: только сфера и размер.
"""
from __future__ import annotations

import hashlib
import re

from sqlalchemy.orm import Session

from ..models import Candidate, ColleagueRef, Employer, Invite

STRONG = ["Держит сроки, не теряет задачи", "Разбирается в чужом коде быстрее всех в команде", "Спокойно ведёт релизы под нагрузкой",
          "Хорошо объясняет решения младшим", "Сам находит, где медленно, и чинит", "Пишет код, который легко читать"]
GROW = ["Берёт на себя больше, чем успевает", "Мало пишет документацию", "Не любит спорить на ревью, соглашается слишком быстро",
        "Долго решает без данных", "Мог бы чаще делиться тем, что знает"]


def _h(*parts) -> int:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def workplaces(c: Candidate) -> list[str]:
    """Компании из факта «Места работы»: «ТрансКод — 4 г. (сейчас…); Финпоток — 3 г.» → [ТрансКод, Финпоток]."""
    f = next((x for x in (c.facts or []) if x.get("k") == "Места работы"), None)
    if not f:
        return []
    out = []
    for part in f["v"].split(";"):
        name = re.split(r"\s+—\s+", part.strip())[0].strip()
        if name and "стажировк" not in name:
            out.append(name)
    return out


def colleagues(db: Session, c: Candidate, limit: int = 4) -> list[tuple[Candidate, str]]:
    """Коллеги по общему месту работы. Порядок устойчивый, чтобы сводка не прыгала от запроса к запросу."""
    mine = set(workplaces(c))
    if not mine:
        return []
    found = []
    for o in db.query(Candidate).filter(Candidate.id != c.id, Candidate.spec.isnot(None)):
        common = mine & set(workplaces(o))
        if common:
            found.append((o, sorted(common)[0]))
    found.sort(key=lambda x: _h(c.id, x[0].id))
    return found[:limit]


def answer_for(c: Candidate, author: Candidate) -> dict:
    k = _h(c.id, author.id)
    strong = STRONG[k % len(STRONG)]
    if c.stack:
        strong = f"{strong}. Сильный в {c.stack[k % len(c.stack)]}"
    return {"strong": strong, "grow": GROW[(k // 7) % len(GROW)], "again": (k % 10) < 8}


def collect(db: Session, c: Candidate, e: Employer) -> dict:
    """Агент компании опрашивает коллег кандидата. Готовые отзывы берёт сразу, остальным шлёт
    запрос без названия компании. Исход запроса в прототипе задан детерминированно:
    часть отвечает сразу, часть отказывается, часть ещё не ответила (запрос лежит у коллеги)."""
    if not (c.privacy or {}).get("refs_collect", True):
        return {"closed": True, "asked": 0, "answered": 0, "declined": 0, "pending": 0, "quotes": []}
    for o, where in colleagues(db, c):
        r = db.query(ColleagueRef).filter_by(candidate_id=c.id, author_id=o.id, kind="review").first()
        if r:
            continue
        roll = _h(c.id, o.id, e.id) % 10
        auto = (o.privacy or {}).get("refs_agent", True)
        status = "answered" if roll < 5 and auto else "declined" if roll < 7 else "asked"
        db.add(ColleagueRef(candidate_id=c.id, author_id=o.id, employer_id=e.id, kind="review", status=status, relation=where,
                            answers=answer_for(c, o) if status == "answered" else None))
    db.commit()
    return report(db, c)


def report(db: Session, c: Candidate) -> dict:
    rs = db.query(ColleagueRef).filter_by(candidate_id=c.id, kind="review").all()
    done = [r for r in rs if r.status in ("ready", "answered")]
    return {"closed": not (c.privacy or {}).get("refs_collect", True), "asked": len(rs), "answered": len(done),
            "declined": sum(r.status == "declined" for r in rs), "pending": sum(r.status == "asked" for r in rs),
            "quotes": [{"relation": r.relation, **(r.answers or {})} for r in done]}


def social_scores(db: Session) -> dict[int, float]:
    """Доля «Связи», 0…1: отзывы коллег «взял бы снова» и одобренные рекомендации."""
    by: dict[int, dict] = {}
    for r in db.query(ColleagueRef).filter(ColleagueRef.status.in_(["ready", "answered"])):
        d = by.setdefault(r.candidate_id, {"rev": 0, "again": 0, "rec": 0})
        if r.kind == "rec":
            d["rec"] += 1 if r.approved else 0
        else:
            d["rev"] += 1
            d["again"] += 1 if (r.answers or {}).get("again") else 0
    out = {}
    for cid, d in by.items():
        rev = (d["again"] / d["rev"]) * min(1.0, d["rev"] / 2) if d["rev"] else 0.0
        out[cid] = round(min(1.0, 0.6 * rev + 0.4 * min(1.0, d["rec"] / 2)), 3)
    return out


def company_summary(db: Session, e: Employer) -> dict:
    """Сводка о компании для кандидата: сотрудники (агенты тех, у кого она в местах работы),
    кандидаты (поведение компании на платформе) и открытые оценки без текстов."""
    rep = e.reputation or {}
    staff_n = sum(1 for c in db.query(Candidate).filter(Candidate.spec.isnot(None)) if e.name and e.name in workplaces(c))
    st = rep.get("staff") or {}
    invs = db.query(Invite).filter_by(employer_id=e.id).all()
    acc = sum(i.status == "принято" for i in invs)
    seen = [i for i in invs if any(x.get("s") == "просмотрено" for x in (i.log or []))]
    return {
        # Опрошены агенты всех, у кого компания в местах работы; ответила примерно треть.
        "staff": {"asked": staff_n, "n": max(st.get("n", 0), round(staff_n * 0.3)) if staff_n else st.get("n", 0), "avg": st.get("avg"), "notes": st.get("notes", [])},
        "cands": {"n": len({i.candidate_id for i in invs}), "accepted": acc, "invites": len(invs), "note": rep.get("cands_note")},
        "open": rep.get("open", []),
        "agents": staff_n + len({i.candidate_id for i in invs}),
    }
