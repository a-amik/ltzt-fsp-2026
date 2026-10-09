"""Адаптивный тест на заявленный грейд: старт, следующее задание, ответ, итог, история."""
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..core import bank
from ..core.irt import estimate, pick_next, prior_for, should_stop, verdict
from ..core.llm import provider
from ..db import get_db
from ..models import Candidate, TemplateExposure, TestSession
from .deps import current_candidate

router = APIRouter(prefix="/test", tags=["test"])


class StartIn(BaseModel):
    claimed: int
    mode: str = "full"  # full | express (3—5 минут, для показа жюри)


def conduct_summary(s: TestSession) -> dict:
    """Поведение на тесте — в протокол, без штрафа: вставки из буфера, уходы со вкладки, время."""
    ev = s.events or []
    secs = int((s.finished_at - s.started_at).total_seconds()) if s.finished_at else None
    return {"paste": sum(1 for e in ev if e.get("e") == "paste"), "blur": sum(1 for e in ev if e.get("e") == "blur"),
            "seconds": secs, "items": len(s.answers), "mode": s.mode, "ai_items": sum(1 for a in s.answers if a.get("ai"))}


def _session_out(s: TestSession) -> dict:
    cur = bank.public(s.current) if s.current and not s.finished else None
    return {"id": s.id, "spec": s.spec, "claimed": s.claimed, "mode": s.mode, "n": len(s.answers), "finished": s.finished,
            "current": cur, "why": s.why, "trace": s.trace, "theta": s.theta, "se": s.se, "verdict": s.verdict,
            "answers": [{k: v for k, v in a.items() if k != "detail"} for a in s.answers] if s.finished else None}


def _next(db: Session, s: TestSession, theta: float):
    rng = random.Random()
    pool = bank.for_spec(s.spec)
    exposure = {e.template_id: e.shown for e in db.query(TemplateExposure)}
    # Контроль частоты показа: самые показанные шаблоны идут в конец очереди кандидатов.
    pool = sorted(pool, key=lambda t: exposure.get(t.id, 0))[: max(8, len(pool) * 2 // 3)]
    t, why = pick_next(theta, pool, set(s.used), rng)
    if not t:
        return False
    s.current = bank.instance(t, rng.randrange(1, 10**9))
    s.why = why
    s.used = s.used + [t.id]
    e = db.get(TemplateExposure, t.id) or TemplateExposure(template_id=t.id, shown=0)
    e.shown += 1
    db.add(e)
    return True


@router.post("/start", summary="Начать тест на заявленный грейд")
def start(body: StartIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    if not c.spec:
        raise HTTPException(422, "Сначала опрос: специализация")
    if body.mode not in ("full", "express"):
        raise HTTPException(422)
    open_s = db.query(TestSession).filter_by(candidate_id=c.id, finished=False).first()
    if open_s:
        return _session_out(open_s)
    # Смена грейда — не чаще раза в cooldown. Понижение после провала — сразу; тест выше при offer_up — сразу.
    last = db.query(TestSession).filter_by(candidate_id=c.id, finished=True).order_by(TestSession.id.desc()).first()
    if last and last.verdict:
        allowed_now = (last.verdict["kind"] == "below" and body.claimed <= last.verdict["offer_down"]) or \
                      (last.verdict["kind"] == "ok" and last.verdict.get("offer_up") and body.claimed == last.claimed + 1)
        if not allowed_now and last.finished_at and datetime.utcnow() - last.finished_at < timedelta(days=settings.grade_cooldown_days):
            left = settings.grade_cooldown_days - (datetime.utcnow() - last.finished_at).days
            raise HTTPException(429, f"Смена грейда — не чаще раза в {settings.grade_cooldown_days} дней; осталось {left}")
    c.claimed_grade = body.claimed
    s = TestSession(candidate_id=c.id, spec=c.spec, claimed=body.claimed, mode=body.mode, prior=prior_for(body.claimed),
                    trace=[{"theta": prior_for(body.claimed), "se": 1.0}])
    db.add(s)
    db.flush()
    _next(db, s, s.prior)
    db.commit()
    return _session_out(s)


@router.get("/current", summary="Текущая сессия теста")
def current(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    s = db.query(TestSession).filter_by(candidate_id=c.id, finished=False).first()
    return _session_out(s) if s else None


class AnswerIn(BaseModel):
    pick: str | None = None
    text: str | None = None
    events: list[dict] | None = None  # честность: paste, blur — в протокол, без штрафа


@router.post("/answer", summary="Ответить на текущее задание")
def answer(body: AnswerIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    s = db.query(TestSession).filter_by(candidate_id=c.id, finished=False).first()
    if not s or not s.current:
        raise HTTPException(409, "Нет открытого теста")
    cur = s.current
    t = bank.BY_ID[cur["tpl"]]
    detail = None
    if cur.get("open"):
        if not body.text or len(body.text.strip()) < 20:
            raise HTTPException(422, "Опишите подход хотя бы в двух предложениях")
        g = provider.grade_open(body.text, cur["rubric"], cur["keys"])
        score, detail = g["score"], g
    else:
        if body.pick is None:
            raise HTTPException(422, "Выберите вариант")
        score = 1.0 if body.pick == cur["ok"] else 0.0
    if body.events:
        s.events = s.events + body.events
    s.answers = s.answers + [{"tpl": t.id, "title": t.title, "skill": t.skill, "a": t.a, "b": t.b, "score": score, "detail": detail, "ai": bool(cur.get("ai"))}]
    theta, se = estimate(s.answers, s.prior)
    s.trace = s.trace + [{"theta": round(theta, 3), "se": round(se, 3), "ok": score >= 0.5}]
    last = {"title": t.title, "score": score, "theta_before": s.trace[-2]["theta"], "theta_after": round(theta, 3)}
    if should_stop(len(s.answers), se, s.mode) or not _next(db, s, theta):
        s.finished, s.finished_at, s.theta, s.se = True, datetime.utcnow(), theta, se
        s.verdict = verdict(s.claimed, theta, se)
        s.current = None
        if s.verdict["kind"] == "ok":
            c.grade, c.theta, c.se, c.grade_since = s.claimed, theta, se, datetime.utcnow()
            c.facts = [{**f, "src": "test"} if f.get("k") == "Стек" else f for f in c.facts]
    db.commit()
    out = _session_out(s)
    out["last"] = last
    return out


@router.get("/history", summary="История тестов")
def history(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    return [{"id": s.id, "date": s.finished_at, "claimed": s.claimed, "mode": s.mode, "theta": s.theta, "se": s.se, "verdict": s.verdict,
             "n": len(s.answers), "skills": _skills(s), "trace": s.trace, "conduct": conduct_summary(s)} for s in db.query(TestSession).filter_by(candidate_id=c.id, finished=True).order_by(TestSession.id.desc())]


def _skills(s: TestSession) -> list[dict]:
    """Профиль по навыкам: оценка по заданиям каждого навыка отдельно."""
    by = {}
    for a in s.answers:
        by.setdefault(a["skill"], []).append(a)
    out = []
    for k, xs in by.items():
        th, se = estimate(xs, s.prior)
        out.append({"name": k, "theta": round(th, 2), "se": round(se, 2), "items": len(xs)})
    return out
