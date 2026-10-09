"""Схема данных. Она же — черновик того, что мы предлагаем ФСП для интеграции (таблица fsp_achievements)."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16))  # candidate | employer
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 152-ФЗ: согласие на обработку и публикацию
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class EmailCode(Base):
    __tablename__ = "email_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), index=True)
    code: Mapped[str] = mapped_column(String(8))
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Token(Base):
    __tablename__ = "tokens"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    spec: Mapped[str | None] = mapped_column(String(32), nullable=True)      # специализация
    stack: Mapped[list] = mapped_column(JSON, default=list)
    work_format: Mapped[str] = mapped_column(String(16), default="гибрид")
    salary: Mapped[int | None] = mapped_column(Integer, nullable=True)     # ожидания, ₽ в месяц
    years: Mapped[int] = mapped_column(Integer, default=0)
    claimed_grade: Mapped[int | None] = mapped_column(Integer, nullable=True)  # заявленный самим кандидатом
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)      # подтверждённый тестом
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    se: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    facts: Mapped[list] = mapped_column(JSON, default=list)   # [{k, v, src: fsp|test|word, approved}]
    privacy: Mapped[dict] = mapped_column(JSON, default=lambda: {"fsp": True, "salary": True, "city": False})
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    fsp_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resume_text: Mapped[str] = mapped_column(Text, default="")
    user = relationship("User")


class FspAchievement(Base):
    """Достижение из реестра ФСП. Кандидат эти строки не вводит и не правит, может только скрыть."""
    __tablename__ = "fsp_achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    fsp_id: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(300))
    discipline: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(32))      # региональное | всероссийское | международное
    year: Mapped[int] = mapped_column(Integer)
    place: Mapped[int | None] = mapped_column(Integer, nullable=True)
    participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rank: Mapped[str | None] = mapped_column(String(32), nullable=True)  # спортивный разряд на момент события
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class TestSession(Base):
    __tablename__ = "test_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    spec: Mapped[str] = mapped_column(String(32))
    claimed: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(8), default="full")  # full | express
    prior: Mapped[float] = mapped_column(Float, default=0.0)
    answers: Mapped[list] = mapped_column(JSON, default=list)   # [{tpl, a, b, score, title, skill}]
    trace: Mapped[list] = mapped_column(JSON, default=list)
    used: Mapped[list] = mapped_column(JSON, default=list)
    current: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # экземпляр задания с ответом (ответ клиенту не отдаётся)
    why: Mapped[list] = mapped_column(JSON, default=list)
    events: Mapped[list] = mapped_column(JSON, default=list)   # честность: вставки, уход со вкладки
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    se: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TemplateExposure(Base):
    """Сколько раз шаблон показан: контроль частоты показа."""
    __tablename__ = "template_exposure"
    template_id: Mapped[str] = mapped_column(String(8), primary_key=True)
    shown: Mapped[int] = mapped_column(Integer, default=0)


class Employer(Base):
    __tablename__ = "employers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    field: Mapped[str] = mapped_column(String(200), default="")
    contact: Mapped[str] = mapped_column(String(200), default="")
    inn: Mapped[str] = mapped_column(String(12), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)  # добровольная метка доверия, не блокирует


class Need(Base):
    """Потребность работодателя: из неё строится подборка."""
    __tablename__ = "needs"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    spec: Mapped[str] = mapped_column(String(32))
    grade: Mapped[int] = mapped_column(Integer)
    stack: Mapped[list] = mapped_column(JSON, default=list)
    salary_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Vacancy(Base):
    __tablename__ = "vacancies"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    spec: Mapped[str] = mapped_column(String(32))
    grade: Mapped[int] = mapped_column(Integer)
    stack: Mapped[list] = mapped_column(JSON, default=list)
    salary_from: Mapped[int] = mapped_column(Integer)   # обязательно: без вилки вакансия не сохраняется
    salary_to: Mapped[int] = mapped_column(Integer)
    work_format: Mapped[str] = mapped_column(String(16), default="гибрид")
    team: Mapped[str] = mapped_column(Text, default="")
    tasks: Mapped[list] = mapped_column(JSON, default=list)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Invite(Base):
    """Приглашение работодателя кандидату. Статусы: отправлено → просмотрено → принято | отклонено."""
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text, default="")
    salary_from: Mapped[int] = mapped_column(Integer)
    salary_to: Mapped[int] = mapped_column(Integer)
    contact: Mapped[str] = mapped_column(String(300), default="")
    work_format: Mapped[str] = mapped_column(String(16), default="гибрид")
    status: Mapped[str] = mapped_column(String(16), default="отправлено")
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    log: Mapped[list] = mapped_column(JSON, default=list)
    talk: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # протокол предразговора агентов
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # итог встречи: {grade_ok: bool, note, at}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Response(Base):
    """Отклик кандидата на вакансию (дополнительный сценарий)."""
    __tablename__ = "responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="отправлено")
    log: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Task(Base):
    """Регулярное короткое задание от работодателя."""
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employers.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    spec: Mapped[str] = mapped_column(String(32))
    grade: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class TaskAnswer(Base):
    __tablename__ = "task_answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0, 0.5, 1 — ставит работодатель
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
