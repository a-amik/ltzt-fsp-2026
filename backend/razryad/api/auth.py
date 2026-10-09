"""Регистрация по почте с подтверждением кодом. На стенде код показывается в ответе (RZ_MAIL_MODE=screen)."""
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Candidate, EmailCode, Employer, Token, User
from .deps import current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class StartIn(BaseModel):
    email: EmailStr
    role: str  # candidate | employer


class ConfirmIn(BaseModel):
    email: EmailStr
    code: str
    consent: bool = True  # 152-ФЗ: согласие на обработку и публикацию данных профиля


@router.post("/start", summary="Запросить код подтверждения почты")
def start(body: StartIn, db: Session = Depends(get_db)):
    if body.role not in ("candidate", "employer"):
        raise HTTPException(422, "role: candidate | employer")
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(EmailCode(email=body.email.lower(), code=code, role=body.role))
    db.commit()
    out = {"sent": True, "mode": settings.mail_mode}
    if settings.mail_mode == "screen":
        out["code"] = code  # демонстрационный режим: письмо не уходит, код виден на экране
    return out


@router.post("/confirm", summary="Подтвердить почту кодом и получить токен")
def confirm(body: ConfirmIn, db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(422, "Без согласия на обработку данных регистрация невозможна")
    email = body.email.lower()
    rec = db.query(EmailCode).filter_by(email=email, code=body.code, used=False).order_by(EmailCode.id.desc()).first()
    if not rec:
        raise HTTPException(400, "Код не подходит")
    rec.used = True
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, role=rec.role, email_confirmed=True, consent_at=datetime.utcnow())
        db.add(user)
        db.flush()
        db.add(Candidate(user_id=user.id) if rec.role == "candidate" else Employer(user_id=user.id))
    token = Token(token=secrets.token_hex(32), user_id=user.id)
    db.add(token)
    db.commit()
    return {"token": token.token, "role": user.role, "email": user.email}


@router.get("/me", summary="Кто я")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role, "consent_at": user.consent_at}


@router.post("/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.query(Token).filter_by(user_id=user.id).delete()
    db.commit()
    return {"ok": True}
