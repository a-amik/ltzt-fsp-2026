"""Кабинет кандидата: профиль, резюме, факты, видимость, приглашения, отклики."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.catalog import DECLINE_REASONS, GRADES, SPEC_IDS, WORK_FORMATS
from ..core.docs import extract_text
from ..core.llm import provider
from ..db import get_db
from ..models import Candidate, Employer, FspAchievement, Invite, Need, Response, TestSession, Vacancy
from ..core.scoring import rank as rank_cands
from .deps import current_candidate

router = APIRouter(prefix="/candidate", tags=["candidate"])


def fsp_list(db: Session, c: Candidate, include_hidden=False) -> list[dict]:
    q = db.query(FspAchievement).filter_by(candidate_id=c.id)
    return [{"id": a.id, "event": a.event, "discipline": a.discipline, "level": a.level, "year": a.year, "place": a.place,
             "participants": a.participants, "team": a.team, "role": a.role, "rank": a.rank, "hidden": a.hidden}
            for a in q if include_hidden or not a.hidden]


def profile_out(db: Session, c: Candidate) -> dict:
    return {"id": c.id, "name": c.name, "phone": c.phone, "city": c.city, "spec": c.spec, "stack": c.stack, "work_format": c.work_format,
            "salary": c.salary, "years": c.years, "claimed_grade": c.claimed_grade, "grade": c.grade, "theta": c.theta, "se": c.se,
            "grade_since": c.grade_since, "facts": c.facts, "privacy": c.privacy, "visible": c.visible, "fsp_id": c.fsp_id,
            "fsp": fsp_list(db, c, include_hidden=True),
            "category": {"spec": c.spec, "grade": c.grade if c.grade is not None else c.claimed_grade, "confirmed": c.grade is not None}
            if c.spec is not None and (c.grade is not None or c.claimed_grade is not None) else None}


class ProfileIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    city: str | None = None
    spec: str | None = None
    stack: list[str] | None = None
    work_format: str | None = None
    salary: int | None = None
    years: int | None = None
    claimed_grade: int | None = None
    privacy: dict | None = None
    visible: bool | None = None


@router.get("/profile", summary="Мой профиль")
def get_profile(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    return profile_out(db, c)


@router.patch("/profile", summary="Опрос и данные профиля (всё — «со слов»)")
def patch_profile(body: ProfileIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_none=True)
    if "spec" in data and data["spec"] not in SPEC_IDS:
        raise HTTPException(422, "Неизвестная специализация")
    if "work_format" in data and data["work_format"] not in WORK_FORMATS:
        raise HTTPException(422, "Формат: офис | гибрид | удалённо")
    if "claimed_grade" in data and not 0 <= data["claimed_grade"] <= 4:
        raise HTTPException(422, "Грейд 0…4")
    for k, v in data.items():
        setattr(c, k, v)
    _sync_facts(c)
    db.commit()
    return profile_out(db, c)


def _sync_facts(c: Candidate):
    """Факты «со слов» из полей профиля; одобренные факты других источников не трогаем."""
    keep = [f for f in c.facts if f.get("src") != "word" or f.get("k") not in ("Стек", "Формат", "Опыт", "Ожидания")]
    stack_src = "test" if c.grade is not None else "word"
    words = []
    if c.stack:
        words.append({"k": "Стек", "v": ", ".join(c.stack), "src": stack_src, "approved": True})
    if c.work_format:
        words.append({"k": "Формат", "v": c.work_format, "src": "word", "approved": True})
    if c.years:
        y = c.years
        words.append({"k": "Опыт", "v": f"{y} {'год' if y == 1 else 'года' if y < 5 else 'лет'} коммерческой разработки", "src": "word", "approved": True})
    c.facts = [f for f in keep if f.get("k") != "Стек"] + words


class FactIn(BaseModel):
    k: str
    v: str
    approved: bool = True


@router.post("/facts", summary="Добавить факт «со слов» (ответ на вопрос рекрутера)")
def add_fact(body: FactIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    c.facts = [f for f in c.facts if f.get("k") != body.k] + [{"k": body.k, "v": body.v, "src": "word", "approved": body.approved}]
    db.commit()
    return c.facts


@router.patch("/facts/{k}", summary="Одобрить или скрыть факт")
def toggle_fact(k: str, approved: bool, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    c.facts = [{**f, "approved": approved} if f.get("k") == k else f for f in c.facts]
    db.commit()
    return c.facts


@router.post("/resume", summary="Загрузить резюме (PDF или текст): поля распознаются и получают метку «со слов»")
async def upload_resume(file: UploadFile, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    text = extract_text(file.filename, await file.read())
    if not text.strip():
        raise HTTPException(422, "Не получилось прочитать файл: пришлите PDF, DOCX или текст")
    return _apply_resume(db, c, text)


class AboutIn(BaseModel):
    text: str


@router.post("/about", summary="Рассказать о себе своими словами или голосом: разбор тот же, что у резюме")
def about(body: AboutIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    if len(body.text.strip()) < 20:
        raise HTTPException(422, "Расскажите хотя бы пару предложений")
    return _apply_resume(db, c, body.text)


def _apply_resume(db: Session, c: Candidate, text: str) -> dict:
    """До опроса распознанное заменяет значения по умолчанию, после — заполняет только пустые поля.
    Всё встаёт фактами «со слов»."""
    parsed = provider.parse_resume(text)
    c.resume_text = text[:20000]
    fresh = c.claimed_grade is None
    for field in ("name", "spec", "stack", "years", "salary", "work_format", "phone"):
        if parsed.get(field) and (fresh or not getattr(c, field)):
            setattr(c, field, parsed[field])
    if parsed["workplaces"]:
        c.facts = [f for f in c.facts if f.get("k") != "Места работы"] + [
            {"k": "Места работы", "v": ", ".join(parsed["workplaces"]), "src": "word", "approved": True}]
    _sync_facts(c)
    db.commit()
    return {"parsed": parsed, "profile": profile_out(db, c)}


@router.get("/resume.txt", summary="Стандартизированный профиль текстом (черновик PDF-профиля)")
def resume_text(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    g = GRADES[c.grade]["name"] if c.grade is not None else "не подтверждён"
    lines = [f"Кандидат: {c.name or '—'}", f"Специализация: {c.spec or '—'} · грейд: {g}", f"Стек: {', '.join(c.stack) or '—'}",
             f"Формат: {c.work_format} · ожидания: {c.salary or '—'} ₽", "", "Факты профиля (источник):"]
    lines += [f"  {f['k']}: {f['v']} ({f['src']})" for f in c.facts if f.get("approved")]
    fsp = fsp_list(db, c)
    if fsp:
        lines += ["", "Достижения ФСП:"] + [f"  {a['year']} — {a['event']}: {a['place']} место из {a['participants']}" for a in fsp]
    return {"text": "\n".join(lines)}


@router.patch("/fsp/{ach_id}", summary="Скрыть или показать достижение ФСП (изменить нельзя)")
def toggle_ach(ach_id: int, hidden: bool, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    a = db.get(FspAchievement, ach_id)
    if not a or a.candidate_id != c.id:
        raise HTTPException(404)
    a.hidden = hidden
    db.commit()
    return fsp_list(db, c, include_hidden=True)


# ── Приглашения и отклики ────────────────────────────────────────────

def invite_out(db: Session, i: Invite, for_candidate=True) -> dict:
    e = db.get(Employer, i.employer_id)
    v = db.get(Vacancy, i.vacancy_id) if i.vacancy_id else None
    out = {"id": i.id, "candidate_id": i.candidate_id, "company": e.name, "title": i.title, "text": i.text, "salary_from": i.salary_from, "salary_to": i.salary_to,
           "contact": i.contact if (i.status == "принято" or not for_candidate) else None, "work_format": i.work_format, "status": i.status,
           "reason": i.reason, "log": i.log, "created_at": i.created_at, "talk": i.talk, "feedback": i.feedback if not for_candidate else None,
           "vacancy": {"id": v.id, "title": v.title, "stack": v.stack, "team": v.team, "tasks": v.tasks} if v else None,
           "employer": {"id": e.id, "name": e.name, "about": e.about, "field": e.field, "verified": e.verified}}
    if not for_candidate:
        cand = db.get(Candidate, i.candidate_id)
        out["candidate_name"] = cand.name if cand else ""  # имя видно работодателю всегда, контакты — после «да»
    if for_candidate and i.status == "принято":
        out["contact"] = i.contact  # способ связи работодателя виден после принятия
    return out


@router.get("/invites", summary="Мои приглашения")
def invites(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    return [invite_out(db, i) for i in db.query(Invite).filter_by(candidate_id=c.id).order_by(Invite.id.desc())]


class DecisionIn(BaseModel):
    status: str  # просмотрено | принято | отклонено
    reason: str | None = None


@router.post("/invites/{inv_id}", summary="Просмотреть, принять или отклонить приглашение")
def decide(inv_id: int, body: DecisionIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    i = db.get(Invite, inv_id)
    if not i or i.candidate_id != c.id:
        raise HTTPException(404)
    if body.status not in ("просмотрено", "принято", "отклонено"):
        raise HTTPException(422)
    if body.status == "отклонено" and body.reason and body.reason not in DECLINE_REASONS:
        raise HTTPException(422, "Причина из списка")
    if i.status in ("принято", "отклонено") and body.status != i.status:
        raise HTTPException(409, "Решение уже принято")
    if i.status != body.status:
        i.status, i.reason = body.status, body.reason
        i.log = i.log + [{"t": datetime.utcnow().isoformat(), "s": body.status}]
        db.commit()
    return invite_out(db, i)


@router.get("/vacancies", summary="Открытые вакансии (дополнительный сценарий отклика)")
def vacancies(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    out = []
    for v in db.query(Vacancy).filter_by(published=True).order_by(Vacancy.id.desc()):
        e = db.get(Employer, v.employer_id)
        out.append({"id": v.id, "company": e.name, "title": v.title, "spec": v.spec, "grade": v.grade, "stack": v.stack,
                    "salary_from": v.salary_from, "salary_to": v.salary_to, "work_format": v.work_format, "team": v.team, "tasks": v.tasks})
    return out


@router.post("/vacancies/{vac_id}/respond", summary="Откликнуться на вакансию")
def respond(vac_id: int, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    if not db.get(Vacancy, vac_id):
        raise HTTPException(404)
    if db.query(Response).filter_by(candidate_id=c.id, vacancy_id=vac_id).first():
        raise HTTPException(409, "Отклик уже есть")
    r = Response(candidate_id=c.id, vacancy_id=vac_id, log=[{"t": datetime.utcnow().isoformat(), "s": "отправлено"}])
    db.add(r)
    db.commit()
    return {"id": r.id, "status": r.status}


@router.get("/responses", summary="Мои отклики и их статусы")
def responses(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    return [{"id": r.id, "vacancy_id": r.vacancy_id, "status": r.status, "log": r.log, "created_at": r.created_at}
            for r in db.query(Response).filter_by(candidate_id=c.id).order_by(Response.id.desc())]


# ── Место в выдаче и статистика: честно, тем же ранжированием ───────

def _bank(db: Session) -> list[dict]:
    from .employer import _cand_dicts
    return _cand_dicts(db)


@router.get("/rank", summary="Почему я на этом месте: типичный запрос к моей категории и что будет, если…")
def my_rank(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    if c.spec is None or (c.grade is None and c.claimed_grade is None):
        return None
    cands = _bank(db)
    me = next((x for x in cands if x["id"] == c.id), None)
    if not me:
        return None
    need = {"spec": c.spec, "grade": c.grade if c.grade is not None else c.claimed_grade, "stack": c.stack[:3]}
    res = rank_cands(cands, need)
    pos = next((i for i, r in enumerate(res) if r["c"]["id"] == c.id), -1) + 1
    if not pos:
        return None
    mine = res[pos - 1]["s"]["parts"]
    above = res[: pos - 1]
    by = {"test": 0, "stack": 0, "fsp": 0, "fresh": 0}
    for r in above:
        k, d = max(((k, v - mine[k]) for k, v in r["s"]["parts"].items()), key=lambda x: x[1])
        if d > 0:
            by[k] += 1

    def what(patch):
        alt = [{**x, **patch} if x["id"] == c.id else x for x in cands]
        r2 = rank_cands(alt, need)
        return next((i for i, r in enumerate(r2) if r["c"]["id"] == c.id), -1) + 1

    moves = [{"text": "Решить задание работодателя и получить «сильно»", "pos": what({"fresh_tasks": (me.get("fresh_tasks") or 0) + 1, "task_score": 1})}]
    if not me["fsp"]:
        moves.append({"text": "Привязать ФСП ID с призовым местом (10 из 200)", "pos": what({"fsp": [{"place": 10, "participants": 200, "year": 2025, "event": "", "hidden": False}]})})
    if c.grade is not None:
        moves.append({"text": "Пересдать тест и поднять оценку на 0,3", "pos": what({"theta": min(2.6, c.theta + 0.3)})})
    else:
        moves.append({"text": "Подтвердить грейд тестом", "pos": what({"grade": need["grade"], "theta": 0.0, "se": 0.4})})
    # Сколько компаний ищут в категории: вакансии и запросы подбора той же специализации, грейд ±1.
    looking = len({x.employer_id for M in (Vacancy, Need)
                   for x in db.query(M).filter(M.spec == c.spec, M.grade.between(need["grade"] - 1, need["grade"] + 1))})
    return {"pos": pos, "total": len(res), "need": need, "parts": mine, "above_by": by, "moves": moves, "confirmed": c.grade is not None, "looking": looking}


@router.get("/stats", summary="Моя статистика: место в категории, приглашения и их вилки против ожиданий")
def my_stats(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    inv = db.query(Invite).filter_by(candidate_id=c.id).all()
    offers = [(i.salary_from + i.salary_to) // 2 for i in inv]
    tests = db.query(TestSession).filter_by(candidate_id=c.id, finished=True).count()
    return {"invites": len(inv), "accepted": sum(1 for i in inv if i.status == "принято"), "declined": sum(1 for i in inv if i.status == "отклонено"),
            "offers": offers, "not_below": sum(1 for o in offers if c.salary and o >= c.salary), "tests": tests,
            "responses": db.query(Response).filter_by(candidate_id=c.id).count()}


@router.get("/employers/{emp_id}", summary="Работодатель глазами кандидата: профиль и поведение на платформе")
def employer_card(emp_id: int, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    from .employer import employer_stats
    e = db.get(Employer, emp_id)
    if not e:
        raise HTTPException(404)
    return {"id": e.id, "name": e.name, "about": e.about, "field": e.field, "verified": e.verified, "stats": employer_stats(db, e)}
