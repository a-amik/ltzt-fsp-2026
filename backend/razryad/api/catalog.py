"""Справочник и сведения о механике — для фронта и документации."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import TemplateExposure

from ..core import bank
from ..core.catalog import DECLINE_REASONS, GRADES, SKILLS, SPECS, WORK_FORMATS
from ..core.scoring import rank, score_candidate
from ..core.irt import RULES
from ..core.llm import PROVIDER_INFO
from ..core.scoring import WEIGHTS

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", summary="Специализации, грейды, навыки, форматы")
def catalog():
    return {"specs": SPECS, "grades": GRADES,
            "skills": SKILLS, "work_formats": WORK_FORMATS, "decline_reasons": DECLINE_REASONS}


@router.get("/mechanics", summary="Параметры механик: веса, правила теста, банк")
def mechanics():
    return {"weights": WEIGHTS, "cat": {k: v.__dict__ for k, v in RULES.items()},
            "bank": {"templates": len(bank.TEMPLATES), "by_spec": {s["id"]: len(bank.for_spec(s["id"])) for s in SPECS}},
            "llm": PROVIDER_INFO}


@router.get("/templates", summary="Банк шаблонов без эталонов: id, навык, формат, параметры IRT")
def templates(db: Session = Depends(get_db)):
    shown = {e.template_id: e.shown for e in db.query(TemplateExposure)}
    return [{"id": t.id, "title": t.title, "skill": t.skill, "specs": t.specs, "format": t.fmt, "a": t.a, "b": t.b, "tags": t.tags, "shown": shown.get(t.id, 0)} for t in bank.TEMPLATES]


@router.get("/fsp-pair", summary="Для страницы «Как это работает»: два обезличенных кандидата с равным тестом, у одного есть ФСП")
def fsp_pair(spec_id: str = "backend", grade: int = 2, db: Session = Depends(get_db)):
    """Страница открыта без входа, поэтому наружу уходят только номер, оценка, балл и призовые места — ни имени, ни профиля."""
    from .employer import _cand_dicts
    pool = [c for c in _cand_dicts(db) if c["spec"] == spec_id and c["grade"] == grade]
    withf = [c for c in pool if c["fsp"]]
    without = [c for c in pool if not c["fsp"]]
    if not withf or not without:
        return None
    a, b = min(((x, y) for x in withf for y in without), key=lambda p: abs(p[0]["theta"] - p[1]["theta"]))
    need = {"spec": spec_id, "grade": grade, "stack": [s for s in SPECS if s["id"] == spec_id][0]["stack"][:2]}
    res = rank(pool, need)
    pos = {r["c"]["id"]: i + 1 for i, r in enumerate(res)}
    def anon(x):
        sc = score_candidate(x, need)
        return {"id": x["id"], "display": f"Кандидат №\u00a0{x['id']}", "theta": x["theta"], "pos": pos[x["id"]],
                "score": {"total": sc["total"], "parts": sc["parts"]},
                "fsp": [{k: e.get(k) for k in ("place", "participants", "event", "year")} for e in x["fsp"] if not e.get("hidden")]}
    return {"pair": [anon(x) for x in (a, b)], "total": len(res), "top10_without_fsp": sum(1 for r in res[:10] if not r["c"]["fsp"]), "need": need}
