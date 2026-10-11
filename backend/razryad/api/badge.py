"""Значок грейда для README на GitHub и подписи: «Разряд | Бэкенд · Средний».

Адрес подписан ключом сервиса: по номеру кандидата чужой значок не подобрать,
а значок без подписи не отдаётся. Скрытый профиль значка не имеет.
"""
import hashlib
import hmac
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..core.catalog import GRADES, SPECS
from ..db import get_db
from ..models import Candidate
from .deps import current_candidate

router = APIRouter(tags=["Значок"])


def sign(cand_id: int) -> str:
    return hmac.new(settings.secret.encode(), f"badge:{cand_id}".encode(), hashlib.sha256).hexdigest()[:16]


def _width(text: str) -> int:
    # Ширина под шрифт 11 px без измерения: кириллица шире латиницы.
    return int(sum(7.4 if "а" <= ch.lower() <= "я" or ch in "ёЁ" else 6.6 if ch != " " else 3.6 for ch in text)) + 20


def render(left: str, right: str, color: str) -> str:
    lw, rw = _width(left), _width(right)
    w = lw + rw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="22" role="img" aria-label="{escape(left)}: {escape(right)}">
<title>{escape(left)}: {escape(right)}</title>
<rect width="{lw}" height="22" fill="#1C1D22"/><rect x="{lw}" width="{rw}" height="22" fill="{color}"/>
<g fill="#FFFFFF" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">
<text x="{lw / 2:.0f}" y="15">{escape(left)}</text><text x="{lw + rw / 2:.0f}" y="15">{escape(right)}</text></g></svg>"""


@router.get("/badge/{cand_id}-{sig}.svg", summary="Значок грейда кандидата (SVG)", response_class=Response)
def badge(cand_id: int, sig: str, db: Session = Depends(get_db)):
    if not hmac.compare_digest(sig, sign(cand_id)):
        raise HTTPException(404)
    c = db.get(Candidate, cand_id)
    if not c or not c.visible or not c.spec:
        raise HTTPException(404)
    name = next(s["name"] for s in SPECS if s["id"] == c.spec)
    if c.grade is not None:
        svg = render("Разряд", f"{name} · {GRADES[c.grade]['name']}", "#402FFF")
    else:
        svg = render("Разряд", f"{name} · грейд не подтверждён", "#6B6C75")
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "max-age=3600"})


@router.get("/candidate/badge", summary="Мой значок грейда: адрес картинки и строка для README")
def my_badge(c: Candidate = Depends(current_candidate)):
    path = f"/api/badge/{c.id}-{sign(c.id)}.svg"
    return {"path": path, "confirmed": c.grade is not None}
