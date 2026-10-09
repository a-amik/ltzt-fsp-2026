"""Зависимости: сессия базы, текущий пользователь по токену, роли."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Candidate, Employer, Token, User


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Нужен токен")
    t = db.get(Token, authorization[7:])
    if not t:
        raise HTTPException(401, "Токен не найден")
    return db.get(User, t.user_id)


def current_candidate(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Candidate:
    if user.role != "candidate":
        raise HTTPException(403, "Только для кандидата")
    return db.query(Candidate).filter_by(user_id=user.id).one()


def current_employer(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Employer:
    if user.role != "employer":
        raise HTTPException(403, "Только для работодателя")
    return db.query(Employer).filter_by(user_id=user.id).one()
