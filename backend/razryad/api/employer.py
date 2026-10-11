"""Кабинет работодателя: профиль компании, потребность и подборка, банк кандидатов, приглашения, вакансии, задания."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.agents import negotiate
from ..core.catalog import GRADES, SPEC_IDS
from ..core.docs import extract_text
from ..core.llm import provider
from ..core.scoring import rank
from ..db import get_db
from ..models import Candidate, Employer, FspAchievement, Invite, Need, Response, Task, TaskAnswer, TestSession, Vacancy
from .test import conduct_summary
from .candidate import invite_out
from .deps import current_employer

router = APIRouter(prefix="/employer", tags=["employer"])


# ── Профиль компании ─────────────────────────────────────────────────

class CompanyIn(BaseModel):
    name: str | None = None
    about: str | None = None
    field: str | None = None
    contact: str | None = None
    inn: str | None = None
    size: str | None = None
    city: str | None = None
    site: str | None = None
    hiring: str | None = None
    prefs: dict | None = None


@router.get("/company")
def get_company(e: Employer = Depends(current_employer)):
    return {"id": e.id, "name": e.name, "about": e.about, "field": e.field, "contact": e.contact, "inn": e.inn, "verified": e.verified,
            "size": e.size, "city": e.city, "site": e.site, "hiring": e.hiring or "active", "prefs": e.prefs}


@router.patch("/company")
def patch_company(body: CompanyIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_none=True)
    if "hiring" in data and data["hiring"] not in ("active", "paused"):
        raise HTTPException(422, "Статус найма: active | paused")
    if "prefs" in data:
        keys = {"specs": list, "grades": list, "formats": list, "cities": list, "confirmed_only": bool, "fsp_first": bool}
        data["prefs"] = {k: t(data["prefs"][k]) for k, t in keys.items() if k in data["prefs"]}
    for k, v in data.items():
        setattr(e, k, v)
    # Добровольная метка доверия: ИНН из 10 знаков и корпоративный домен почты. Не блокирует сценарий.
    e.verified = bool(e.inn and len(e.inn) == 10 and e.contact and "@" in e.contact and not e.contact.endswith(("@mail.ru", "@gmail.com", "@yandex.ru")))
    db.commit()
    return get_company(e)


# ── Кандидаты как словари для ранжирования ───────────────────────────

def _cand_dicts(db: Session, skip_user: int | None = None, emp_id: int | None = None, only_id: int | None = None) -> list[dict]:
    """Банк кандидатов для ранжирования. skip_user — вход самой компании: человек,
    который её представляет и сам ищет работу, своей компании не виден."""
    achs = {}
    for a in db.query(FspAchievement):
        achs.setdefault(a.candidate_id, []).append({"event": a.event, "year": a.year, "place": a.place, "participants": a.participants,
                                                    "level": a.level, "discipline": a.discipline, "rank": a.rank, "hidden": a.hidden})
    from ..core.refs import social_scores
    social = social_scores(db)
    conduct = {}
    for ts in db.query(TestSession).filter_by(finished=True):
        conduct[ts.candidate_id] = conduct_summary(ts)
    since = datetime.utcnow() - timedelta(days=90)
    fresh = {}
    for ta in db.query(TaskAnswer).filter(TaskAnswer.created_at >= since):
        f = fresh.setdefault(ta.candidate_id, {"n": 0, "scores": []})
        f["n"] += 1
        if ta.score is not None:
            f["scores"].append(ta.score)
    out = []
    q = db.query(Candidate).filter_by(visible=True)
    if skip_user is not None:
        q = q.filter(Candidate.user_id != skip_user)
    if only_id is not None:  # свой профиль для проверки агента: без фильтров видимости
        q = db.query(Candidate).filter_by(id=only_id)
    for c in q:
        if c.spec is None or (c.grade is None and c.claimed_grade is None):
            continue
        # «Не ищу» — в выдаче нет; скрывшийся от этой компании — тоже.
        hidden = (c.search or "active") == "closed" or (emp_id is not None and emp_id in ((c.wants or {}).get("hide") or []))
        if hidden and only_id is None:
            continue
        f = fresh.get(c.id, {"n": 0, "scores": []})
        out.append({"id": c.id, "spec": c.spec, "grade": c.grade, "claimed_grade": c.claimed_grade, "theta": c.theta, "se": c.se,
                    "express": c.grade is None and c.express_at is not None,
                    "stack": c.stack, "work_format": c.work_format, "salary": c.salary if c.privacy.get("salary", True) else None,
                    "years": c.years, "city": c.city if c.privacy.get("city") else None, "facts": c.facts, "privacy": c.privacy,
                    "fsp": achs.get(c.id, []) if c.privacy.get("fsp", True) else [],
                    "fresh_tasks": f["n"], "task_score": (max(f["scores"]) if f["scores"] else None), "name": c.name, "conduct": conduct.get(c.id),
                    "search": c.search or "active", "agent": c.agent, "social": social.get(c.id, 0.0)})
    return out


def card(x: dict, s: dict | None = None) -> dict:
    """Карточка кандидата до согласия: имя, места работы и подтверждённый профиль видны,
    контакты закрыты, пока кандидат не принял приглашение или не откликнулся сам (ТЗ, п. 2.2;
    ответ экспертов ФСП 07.10.2026)."""
    g = x["grade"] if x["grade"] is not None else x["claimed_grade"]
    return {"id": x["id"], "display": x.get("name") or f"Кандидат №{x['id']:03d}", "spec": x["spec"], "grade": g, "grade_name": GRADES[g]["name"], "conduct": x.get("conduct"),
            "confirmed": x["grade"] is not None, "express": bool(x.get("express")), "theta": x["theta"], "se": x["se"], "stack": x["stack"], "work_format": x["work_format"],
            "salary": x["salary"], "years": x["years"], "city": x["city"],
            "facts": [{"k": f["k"], "v": f["v"], "src": f["src"]} for f in x["facts"] if f.get("approved")],
            "fsp": [a for a in x["fsp"] if not a.get("hidden")], "fresh_tasks": x["fresh_tasks"], "task_score": x["task_score"],
            "search": x.get("search", "active"), "score": s}


# ── Потребность и подборка ───────────────────────────────────────────

class NeedIn(BaseModel):
    text: str
    spec: str | None = None
    grade: int | None = None
    stack: list[str] | None = None
    salary_from: int | None = None
    salary_to: int | None = None
    work_format: str | None = None


@router.post("/needs", summary="Описать потребность своими словами; ассистент раскладывает её в поля")
def create_need(body: NeedIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    p = provider.parse_need(body.text)
    for k in ("spec", "grade", "stack", "salary_from", "salary_to", "work_format"):
        if getattr(body, k) is not None:
            p[k] = getattr(body, k)
    if p["spec"] not in SPEC_IDS:
        raise HTTPException(422)
    n = Need(employer_id=e.id, text=body.text, **p)
    db.add(n)
    db.commit()
    return _need_out(n)


def _need_out(n: Need) -> dict:
    return {"id": n.id, "text": n.text, "spec": n.spec, "grade": n.grade, "stack": n.stack, "salary_from": n.salary_from,
            "salary_to": n.salary_to, "work_format": n.work_format}


@router.patch("/needs/{need_id}", summary="Поправить разобранную потребность")
def patch_need(need_id: int, body: NeedIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    n = db.get(Need, need_id)
    if not n or n.employer_id != e.id:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(n, k, v)
    db.commit()
    return _need_out(n)


@router.get("/needs/{need_id}/selection", summary="Подборка: категории с числом кандидатов и ранжированный список с обоснованием")
def selection(need_id: int, near: bool = False, fsp_only: bool = False, confirmed_only: bool = False, work_format: str | None = None,
              must_stack: bool = False, talks: bool = False, limit: int = 20, offset: int = 0, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    n = db.get(Need, need_id)
    if not n or n.employer_id != e.id:
        raise HTTPException(404)
    cands = _cand_dicts(db, e.user_id, e.id)
    need = _need_out(n)
    cats = [{"grade": g["id"], "name": g["name"], "count": sum(1 for c in cands if c["spec"] == n.spec and (c["grade"] if c["grade"] is not None else c["claimed_grade"]) == g["id"])} for g in GRADES]
    ranked = rank(cands, need, {"near": near, "fsp_only": fsp_only, "confirmed_only": confirmed_only, "work_format": work_format, "must_stack": must_stack})
    items = [card(x["c"], x["s"]) for x in ranked[offset: offset + limit]]
    if talks:
        # Переговоры с категорией: агент работодателя проходит один сценарий со всеми кандидатами выдачи.
        offer = _offer(db, e, n.id, None)
        for it, x in zip(items, ranked[offset: offset + limit]):
            it["talk"] = negotiate(x["c"], offer)
    return {"need": need, "categories": cats, "total": len(ranked), "items": items}


@router.get("/candidates", summary="Поиск по банку кандидатов с фильтрами")
def bank_search(spec: str | None = None, grade: int | None = None, stack: str | None = None, fsp_only: bool = False,
                confirmed_only: bool = False, work_format: str | None = None, limit: int = 20, offset: int = 0,
                e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    cands = _cand_dicts(db, e.user_id, e.id)
    st = [s for s in (stack or "").split(",") if s]
    out = []
    for c in cands:
        g = c["grade"] if c["grade"] is not None else c["claimed_grade"]
        if spec and c["spec"] != spec: continue
        if grade is not None and g != grade: continue
        if st and not any(s in c["stack"] for s in st): continue
        if fsp_only and not [a for a in c["fsp"] if not a.get("hidden")]: continue
        if confirmed_only and c["grade"] is None: continue
        if work_format and c["work_format"] != work_format: continue
        out.append(c)
    out.sort(key=lambda c: (c["grade"] is None, -(c["theta"] or -9)))
    return {"total": len(out), "items": [card(c) for c in out[offset: offset + limit]]}


@router.get("/candidates/{cand_id}/references", summary="Отзывы бывших коллег: агент компании опрашивает их в фоне, компанию не называет")
def candidate_refs(cand_id: int, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    from ..core.refs import collect
    c = db.get(Candidate, cand_id)
    if not c or c.user_id == e.user_id:
        raise HTTPException(404)
    return collect(db, c, e)


@router.get("/candidates/{cand_id}", summary="Карточка кандидата до согласия: имя и профиль видны, контакты закрыты")
def candidate_card(cand_id: int, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    x = next((c for c in _cand_dicts(db, e.user_id, e.id) if c["id"] == cand_id), None)
    if not x:
        raise HTTPException(404)
    out = card(x)
    acc = db.query(Invite).filter_by(employer_id=e.id, candidate_id=cand_id, status="принято").first()
    if acc:
        c = db.get(Candidate, cand_id)
        out["contacts"] = {"name": c.name, "email": c.user.email, "phone": c.phone}  # только после принятия приглашения
    return out


# ── Предразговор агентов ─────────────────────────────────────────────

class TalkIn(BaseModel):
    need_id: int | None = None
    vacancy_id: int | None = None


@router.post("/candidates/{cand_id}/talk", summary="Предразговор агентов сторон до приглашения")
def talk(cand_id: int, body: TalkIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    x = next((c for c in _cand_dicts(db, e.user_id, e.id) if c["id"] == cand_id), None)
    if not x:
        raise HTTPException(404)
    offer = _offer(db, e, body.need_id, body.vacancy_id)
    t = negotiate(x, offer)
    t["steps"] = provider.rephrase(t["steps"])
    return t


def _offer(db: Session, e: Employer, need_id: int | None, vacancy_id: int | None) -> dict:
    if vacancy_id:
        v = db.get(Vacancy, vacancy_id)
        if v and v.employer_id == e.id:
            return {"stack": v.stack, "grade": v.grade, "salary_from": v.salary_from, "salary_to": v.salary_to, "work_format": v.work_format, "tasks": v.tasks, "team": v.team, "field": e.field}
    n = db.get(Need, need_id) if need_id else db.query(Need).filter_by(employer_id=e.id).order_by(Need.id.desc()).first()
    if n and n.employer_id != e.id:
        n = None
    if not n:
        raise HTTPException(422, "Нужна потребность или вакансия")
    return {"stack": n.stack, "grade": n.grade, "salary_from": n.salary_from or 0, "salary_to": n.salary_to or 0, "work_format": n.work_format, "tasks": [], "team": e.about, "field": e.field}


# ── Приглашения ──────────────────────────────────────────────────────

class InviteIn(BaseModel):
    candidate_id: int
    title: str
    text: str = ""
    salary_from: int
    salary_to: int
    contact: str
    work_format: str = "гибрид"
    vacancy_id: int | None = None
    need_id: int | None = None


@router.post("/invites", summary="Пригласить кандидата: вилка зарплаты «от — до» в рублях обязательна")
def create_invite(body: InviteIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    if body.salary_from <= 0 or body.salary_to < body.salary_from:
        raise HTTPException(422, "Вилка зарплаты «от — до» в рублях обязательна")
    if not body.title.strip() or not body.contact.strip():
        raise HTTPException(422, "В приглашении нужны название предложения и способ связи")
    c0 = db.get(Candidate, body.candidate_id)
    if not c0 or c0.user_id == e.user_id:
        raise HTTPException(404)
    if db.query(Invite).filter_by(employer_id=e.id, candidate_id=body.candidate_id).filter(Invite.status.in_(["отправлено", "просмотрено"])).first():
        raise HTTPException(409, "Приглашение уже отправлено и ждёт ответа")
    x = next((c for c in _cand_dicts(db, e.user_id, e.id) if c["id"] == body.candidate_id), None)
    if not x:  # скрыт, не ищет или закрыл компанию: приглашение обходило бы приватность
        raise HTTPException(404)
    warn = None
    if x["salary"] and x["salary"] > body.salary_to:
        warn = f"Вилка зарплаты ниже ожиданий кандидата ({x['salary']:,} ₽)".replace(",", " ")
    # Стек и задачи — из потребности или вакансии, если они указаны; вилка и формат — всегда из самого приглашения:
    # протокол агентов кандидат читает рядом с приглашением, и условия в них должны совпадать.
    offer = None
    if body.need_id or body.vacancy_id:
        try:
            offer = _offer(db, e, body.need_id, body.vacancy_id)
        except HTTPException:
            offer = None
    if offer is None:
        offer = {"stack": [], "grade": x["grade"] if x["grade"] is not None else x["claimed_grade"], "tasks": [], "team": e.about, "field": e.field}
    offer.update({"salary_from": body.salary_from, "salary_to": body.salary_to, "work_format": body.work_format})
    talk = negotiate(x, offer)
    i = Invite(employer_id=e.id, candidate_id=body.candidate_id, vacancy_id=body.vacancy_id, title=body.title, text=body.text,
               salary_from=body.salary_from, salary_to=body.salary_to, contact=body.contact, work_format=body.work_format,
               log=[{"t": datetime.utcnow().isoformat(), "s": "отправлено"}], talk=talk)
    # Агент кандидата со стоп-фактором и разрешением отклонять сам — отклоняет сразу, с причиной.
    if talk and talk.get("stops") and ((c0.agent or {}).get("auto_decline")):
        i.status, i.reason = "отклонено", "стоп-фактор: " + ", ".join(talk["stops"]).lower()
        i.log = i.log + [{"t": datetime.utcnow().isoformat(), "s": "отклонено", "by": "агент кандидата"}]
    db.add(i)
    db.commit()
    out = invite_out(db, i, for_candidate=False)
    out["warning"] = warn
    return out


class FeedbackIn(BaseModel):
    grade_ok: bool          # грейд подтвердился на встрече
    note: str = ""


def interview_fact(db: Session, cand_id: int) -> dict | None:
    """Второе подтверждение: итоги встреч с работодателями. Источник «встреча» — то, чего онлайн-тест
    дать не может; с ним и калибруют тест."""
    fbs = [i.feedback for i in db.query(Invite).filter_by(candidate_id=cand_id, status="принято") if i.feedback]
    if not fbs:
        return None
    ok = sum(1 for f in fbs if f["grade_ok"])
    return {"k": "Грейд на встречах", "v": f"подтверждён {ok} из {len(fbs)}", "src": "interview", "approved": True, "n": len(fbs), "ok": ok}


@router.post("/invites/{inv_id}/feedback", summary="Итог встречи: подтвердился ли грейд. Становится фактом профиля с меткой «встреча»")
def invite_feedback(inv_id: int, body: FeedbackIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    i = db.get(Invite, inv_id)
    if not i or i.employer_id != e.id:
        raise HTTPException(404)
    if i.status != "принято":
        raise HTTPException(409, "Итог встречи — только по принятому приглашению")
    i.feedback = {"grade_ok": body.grade_ok, "note": body.note[:300], "at": datetime.utcnow().isoformat()}
    db.flush()
    c = db.get(Candidate, i.candidate_id)
    fact = interview_fact(db, c.id)
    c.facts = [f for f in c.facts if f.get("src") != "interview"] + ([{k: v for k, v in fact.items() if k in ("k", "v", "src", "approved")}] if fact else [])
    db.commit()
    return {"feedback": i.feedback, "fact": fact}


@router.get("/invites", summary="Мои приглашения и статусы")
def my_invites(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    return [invite_out(db, i, for_candidate=False) for i in db.query(Invite).filter_by(employer_id=e.id).order_by(Invite.id.desc())]


# ── Вакансии и отклики ───────────────────────────────────────────────

def _check_cat(body) -> None:
    """Категория «специализация × грейд» — только из справочника: иначе выдача и кабинет кандидата получат неизвестный грейд."""
    if body.spec not in SPEC_IDS:
        raise HTTPException(422, "Неизвестная специализация")
    if not 0 <= body.grade < len(GRADES):
        raise HTTPException(422, "Грейд 0…4")


class VacancyIn(BaseModel):
    title: str
    spec: str
    grade: int
    stack: list[str] = []
    salary_from: int
    salary_to: int
    work_format: str = "гибрид"
    team: str = ""
    tasks: list[str] = []
    published: bool = True


class VacancyTextIn(BaseModel):
    text: str


@router.post("/vacancies/parse", summary="Переезд: текст своей вакансии — в поля формы (чужие вакансии не импортируем)")
def parse_vacancy(body: VacancyTextIn, e: Employer = Depends(current_employer)):
    if len(body.text.strip()) < 20:
        raise HTTPException(422, "Вставьте текст вакансии целиком")
    return provider.parse_vacancy(body.text)


@router.post("/vacancies/parse-file", summary="Переезд: файл своей вакансии (PDF, DOCX, TXT) — в поля формы")
async def parse_vacancy_file(file: UploadFile, e: Employer = Depends(current_employer)):
    text = extract_text(file.filename, await file.read())
    if len(text.strip()) < 20:
        raise HTTPException(422, "Не получилось прочитать файл: пришлите PDF, DOCX или текст")
    return {**provider.parse_vacancy(text), "text": text[:6000]}


@router.post("/vacancies", summary="Опубликовать вакансию (без вилки зарплаты не сохраняется)")
def create_vacancy(body: VacancyIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    if body.salary_from <= 0 or body.salary_to < body.salary_from:
        raise HTTPException(422, "Вилка зарплаты «от — до» в рублях обязательна")
    _check_cat(body)
    v = Vacancy(employer_id=e.id, **body.model_dump())
    db.add(v)
    db.commit()
    return _vac(v, db)


def _vac(v: Vacancy, db: Session) -> dict:
    resp = db.query(Response).filter_by(vacancy_id=v.id).count()
    return {"id": v.id, "title": v.title, "spec": v.spec, "grade": v.grade, "stack": v.stack, "salary_from": v.salary_from, "salary_to": v.salary_to,
            "work_format": v.work_format, "team": v.team, "tasks": v.tasks, "published": v.published, "responses": resp}


@router.get("/vacancies")
def my_vacancies(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    return [_vac(v, db) for v in db.query(Vacancy).filter_by(employer_id=e.id).order_by(Vacancy.id.desc())]


@router.patch("/vacancies/{vac_id}")
def patch_vacancy(vac_id: int, body: VacancyIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    v = db.get(Vacancy, vac_id)
    if not v or v.employer_id != e.id:
        raise HTTPException(404)
    if body.salary_from <= 0 or body.salary_to < body.salary_from:
        raise HTTPException(422, "Вилка зарплаты «от — до» в рублях обязательна")
    _check_cat(body)
    for k, val in body.model_dump().items():
        setattr(v, k, val)
    db.commit()
    return _vac(v, db)


@router.get("/vacancies/{vac_id}/responses", summary="Отклики на вакансию: отклик сам раскрывает контакты кандидата")
def vacancy_responses(vac_id: int, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    v = db.get(Vacancy, vac_id)
    if not v or v.employer_id != e.id:
        raise HTTPException(404)
    cands = {c["id"]: c for c in _cand_dicts(db, e.user_id, e.id)}
    out = []
    for r in db.query(Response).filter_by(vacancy_id=vac_id).order_by(Response.id.desc()):
        c = cands.get(r.candidate_id)
        item = {"id": r.id, "status": r.status, "log": r.log, "created_at": r.created_at, "candidate": card(c) if c else None}
        if r.status == "принято" and c:
            cand = db.get(Candidate, r.candidate_id)
            item["contacts"] = {"name": cand.name, "email": cand.user.email, "phone": cand.phone}  # отклик сам раскрывает контакты
        out.append(item)
    return out


@router.post("/responses/{resp_id}", summary="Статус отклика: просмотрено | принято | отклонено")
def set_response(resp_id: int, status: str, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    r = db.get(Response, resp_id)
    v = db.get(Vacancy, r.vacancy_id) if r else None
    if not r or v.employer_id != e.id:
        raise HTTPException(404)
    if status not in ("просмотрено", "принято", "отклонено"):
        raise HTTPException(422)
    r.status = status
    r.log = r.log + [{"t": datetime.utcnow().isoformat(), "s": status}]
    db.commit()
    return {"id": r.id, "status": r.status}


# ── Регулярные задания ───────────────────────────────────────────────

class TaskIn(BaseModel):
    title: str
    text: str
    spec: str
    grade: int


@router.post("/tasks", summary="Короткое задание для категории: решить или предложить подход")
def create_task(body: TaskIn, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    _check_cat(body)
    t = Task(employer_id=e.id, **body.model_dump())
    db.add(t)
    db.commit()
    return _task(t, db)


def _task(t: Task, db: Session) -> dict:
    answers = db.query(TaskAnswer).filter_by(task_id=t.id).all()
    return {"id": t.id, "title": t.title, "text": t.text, "spec": t.spec, "grade": t.grade, "created_at": t.created_at,
            "answers": [{"id": a.id, "candidate": f"Кандидат №{a.candidate_id:03d}", "candidate_id": a.candidate_id, "text": a.text, "score": a.score} for a in answers]}


@router.get("/tasks")
def my_tasks(e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    return [_task(t, db) for t in db.query(Task).filter_by(employer_id=e.id).order_by(Task.id.desc())]


@router.post("/tasks/answers/{ans_id}/score", summary="Оценить ответ: 0 слабо, 0.5 годно, 1 сильно")
def score_answer(ans_id: int, score: float, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    a = db.get(TaskAnswer, ans_id)
    t = db.get(Task, a.task_id) if a else None
    if not a or t.employer_id != e.id:
        raise HTTPException(404)
    if score not in (0, 0.5, 1):
        raise HTTPException(422)
    a.score = score
    db.commit()
    return {"id": a.id, "score": a.score}


# ── Статистика работодателя: по реальным приглашениям ───────────────

def employer_stats(db: Session, e: Employer) -> dict:
    inv = db.query(Invite).filter_by(employer_id=e.id).all()
    n = len(inv)
    viewed = sum(1 for i in inv if i.status in ("просмотрено", "принято", "отклонено"))
    acc = sum(1 for i in inv if i.status == "принято")
    dec = [i for i in inv if i.status == "отклонено"]
    reasons = {}
    for i in dec:
        reasons[i.reason or "без причины"] = reasons.get(i.reason or "без причины", 0) + 1
    return {"invites": n, "viewed": viewed, "accepted": acc, "declined": len(dec),
            "accept_pct": round(acc / n * 100) if n else None, "reasons": sorted(reasons.items(), key=lambda x: -x[1]),
            "vacancies": db.query(Vacancy).filter_by(employer_id=e.id).count(),
            "responses": db.query(Response).join(Vacancy, Vacancy.id == Response.vacancy_id).filter(Vacancy.employer_id == e.id).count()}


@router.get("/stats", summary="Воронка найма по реальным приглашениям и откликам")
def my_stats(need_id: int | None = None, e: Employer = Depends(current_employer), db: Session = Depends(get_db)):
    out = employer_stats(db, e)
    n = db.get(Need, need_id) if need_id else db.query(Need).filter_by(employer_id=e.id).order_by(Need.id.desc()).first()
    if n and n.employer_id == e.id:
        cat = [c for c in _cand_dicts(db, e.user_id, e.id) if c["spec"] == n.spec and (c["grade"] if c["grade"] is not None else c["claimed_grade"]) == n.grade]
        sal = sorted(c["salary"] for c in cat if c["salary"])
        out["market"] = {"need": _need_out(n), "count": len(cat), "salaries": sal,
                         "within": sum(1 for v in sal if n.salary_to and v <= n.salary_to) if n.salary_to else None}
    return out
