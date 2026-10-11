"""Регистрация по почте с подтверждением кодом. На стенде код показывается в ответе (RZ_MAIL_MODE=screen)."""
import secrets
from datetime import datetime, timedelta

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


CODE_TTL_MIN = 15  # код подтверждения почты живёт четверть часа


class ConfirmIn(BaseModel):
    email: EmailStr
    code: str
    consent: bool  # 152-ФЗ: согласие на обработку и публикацию данных профиля — поле обязательное, без него 422


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
    if datetime.utcnow() - rec.created_at > timedelta(minutes=CODE_TTL_MIN):
        raise HTTPException(400, "Код устарел, запросите новый")
    rec.used = True
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, role=rec.role, email_confirmed=True, consent_at=datetime.utcnow())
        db.add(user)
        db.flush()
    # Вход с другой стороны той же почтой заводит второй профиль: аккаунт один.
    ensure_profile(db, user, rec.role)
    token = Token(token=secrets.token_hex(32), user_id=user.id)
    db.add(token)
    db.commit()
    return {"token": token.token, "role": rec.role, "email": user.email, "profiles": profiles(db, user)}


def ensure_profile(db: Session, user: User, kind: str) -> None:
    model = Candidate if kind == "candidate" else Employer
    if not db.query(model).filter_by(user_id=user.id).first():
        db.add(model(user_id=user.id))
        db.flush()


def profiles(db: Session, user: User) -> dict:
    c = db.query(Candidate).filter_by(user_id=user.id).first()
    e = db.query(Employer).filter_by(user_id=user.id).first()
    return {"candidate": {"id": c.id, "name": c.name, "spec": c.spec, "grade": c.grade if c.grade is not None else c.claimed_grade} if c else None,
            "employer": {"id": e.id, "name": e.name} if e else None}


@router.get("/me", summary="Кто я и какие у меня профили")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"id": user.id, "email": user.email, "role": user.role, "consent_at": user.consent_at, "profiles": profiles(db, user)}


@router.post("/profiles/{kind}", summary="Завести второй профиль на том же входе: candidate | employer")
def add_profile(kind: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if kind not in ("candidate", "employer"):
        raise HTTPException(422, "kind: candidate | employer")
    ensure_profile(db, user, kind)
    db.commit()
    return {"profiles": profiles(db, user)}


@router.post("/logout")
def logout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.query(Token).filter_by(user_id=user.id).delete()
    db.commit()
    return {"ok": True}


@router.get("/personas", summary="Готовые входы: кандидаты разных типов и компании")
def list_personas(db: Session = Depends(get_db)):
    from ..seed import personas
    return personas(db)


@router.post("/personas/fresh", summary="Новый кандидат с нуля: свой вход, онбординг с первого шага")
def fresh_candidate(db: Session = Depends(get_db)):
    email = f"new-{secrets.token_hex(4)}@razryad.example"
    user = User(email=email, role="candidate", email_confirmed=True, consent_at=datetime.utcnow())
    db.add(user)
    db.flush()
    ensure_profile(db, user, "candidate")
    token = Token(token=secrets.token_hex(32), user_id=user.id)
    db.add(token)
    db.commit()
    return {"token": token.token, "email": email, "profiles": profiles(db, user)}
