"""Регулярные задания со стороны кандидата: лента по своей категории и ответ."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Candidate, Employer, Task, TaskAnswer
from .deps import current_candidate

router = APIRouter(prefix="/candidate/tasks", tags=["tasks"])


@router.get("", summary="Задания работодателей для моей категории (±1 грейд)")
def feed(c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    g = c.grade if c.grade is not None else c.claimed_grade
    if c.spec is None or g is None:
        return []
    mine = {a.task_id: a for a in db.query(TaskAnswer).filter_by(candidate_id=c.id)}
    out = []
    for t in db.query(Task).filter_by(spec=c.spec).order_by(Task.id.desc()):
        if abs(t.grade - g) > 1:
            continue
        e = db.get(Employer, t.employer_id)
        if e.user_id == c.user_id or e.hiring == "paused":
            continue
        a = mine.get(t.id)
        out.append({"id": t.id, "company": e.name, "title": t.title, "text": t.text, "grade": t.grade, "created_at": t.created_at,
                    "answer": {"text": a.text, "score": a.score} if a else None})
    return out


class AnswerIn(BaseModel):
    text: str


@router.post("/{task_id}/answer")
def answer(task_id: int, body: AnswerIn, c: Candidate = Depends(current_candidate), db: Session = Depends(get_db)):
    if not db.get(Task, task_id):
        raise HTTPException(404)
    if db.query(TaskAnswer).filter_by(task_id=task_id, candidate_id=c.id).first():
        raise HTTPException(409, "Ответ уже отправлен")
    if len(body.text.strip()) < 20:
        raise HTTPException(422, "Коротко, но по делу: хотя бы два предложения")
    a = TaskAnswer(task_id=task_id, candidate_id=c.id, text=body.text)
    db.add(a)
    db.commit()
    return {"id": a.id}
