"""ФСП ID: мок OIDC-провайдера и реестра достижений; привязка к профилю кандидата."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..core import fsp_mock
from ..db import get_db
from ..models import Candidate, FspAchievement
from .candidate import fsp_list
from .deps import current_candidate

router = APIRouter(tags=["fsp-id"])
_codes: dict[str, str] = {}   # code → sub (мок, в памяти)
_tokens: dict[str, str] = {}  # access_token → sub


@router.get("/fsp-id/.well-known/openid-configuration", summary="Мок OIDC: discovery")
def discovery():
    base = "/fsp-id"
    return {"issuer": base, "authorization_endpoint": f"{base}/authorize", "token_endpoint": f"{base}/token",
            "userinfo_endpoint": f"{base}/userinfo", "response_types_supported": ["code"], "mock": settings.fsp_oidc_issuer == "internal"}


@router.get("/fsp-id/accounts", summary="Мок: демонстрационные учётные записи ФСП ID")
def accounts():
    return [{"sub": a["sub"], "name": a["name"], "history": a["history"]} for a in fsp_mock.ACCOUNTS.values()]


@router.get("/fsp-id/authorize", summary="Мок OIDC: вход, выдаёт code на redirect_uri")
def authorize(sub: str, redirect_uri: str, state: str = ""):
    if sub not in fsp_mock.ACCOUNTS:
        raise HTTPException(404, "Нет такой учётной записи")
    code = secrets.token_urlsafe(16)
    _codes[code] = sub
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{sep}code={code}&state={state}", status_code=302)


class TokenIn(BaseModel):
    code: str


@router.post("/fsp-id/token", summary="Мок OIDC: обмен code на токен")
def token(body: TokenIn):
    sub = _codes.pop(body.code, None)
    if not sub:
        raise HTTPException(400, "invalid_grant")
    t = secrets.token_urlsafe(24)
    _tokens[t] = sub
    return {"access_token": t, "token_type": "Bearer", "sub": sub}


@router.get("/fsp-id/userinfo", summary="Мок OIDC: сведения об участнике")
def userinfo(access_token: str):
    sub = _tokens.get(access_token)
    if not sub:
        raise HTTPException(401)
    return fsp_mock.userinfo(sub)


@router.get("/fsp-registry/{sub}/achievements", summary="Мок реестра: достижения участника (наша схема данных)")
def registry(sub: str):
    if sub not in fsp_mock.ACCOUNTS:
        raise HTTPException(404)
    return fsp_mock.achievements(sub)


class LinkIn(BaseModel):
    code: str


@router.post("/candidate/fsp/link", summary="Привязать ФСП ID по code и подтянуть достижения")
def link(body: LinkIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    sub = _codes.pop(body.code, None)
    if not sub:
        raise HTTPException(400, "Код входа ФСП ID не подходит")
    info = fsp_mock.userinfo(sub)
    c.fsp_id = sub
    if not c.name:
        c.name = info["name"]
    db.query(FspAchievement).filter_by(candidate_id=c.id).delete()
    for a in fsp_mock.achievements(sub):
        db.add(FspAchievement(candidate_id=c.id, **a))
    db.commit()
    return {"fsp_id": sub, "name": info["name"], "achievements": fsp_list(db, c, include_hidden=True)}


@router.delete("/candidate/fsp/link", summary="Отвязать ФСП ID: достижения уходят из профиля")
def unlink(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    c.fsp_id = None
    db.query(FspAchievement).filter_by(candidate_id=c.id).delete()
    db.commit()
    return {"fsp_id": None}
