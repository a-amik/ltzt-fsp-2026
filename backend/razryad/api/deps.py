"""Зависимости: сессия базы, текущий пользователь по токену, профили.

Один вход — до двух профилей: кандидата и компании. Человек может представлять
компанию и в то же время искать работу сам, поэтому доступ к кабинету решает
наличие профиля, а не роль, выбранная при регистрации."""
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
    c = db.query(Candidate).filter_by(user_id=user.id).first()
    if not c:
        raise HTTPException(404, "Профиль кандидата не создан")
    return c


def current_employer(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Employer:
    e = db.query(Employer).filter_by(user_id=user.id).first()
    if not e:
        raise HTTPException(404, "Профиль компании не создан")
    return e
