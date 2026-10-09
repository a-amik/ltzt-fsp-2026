"""Приложение FastAPI: собирает маршруты, создаёт таблицы, отдаёт OpenAPI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, candidate, catalog, employer, fsp, tasks, test
from .config import settings
from .db import Base, engine

DESCRIPTION = """Сервис подбора ИТ-специалистов с обратной механикой для Федерации спортивного программирования.

Кандидат проходит опрос, сам выбирает грейд и сдаёт адаптивный тест на него; попадает в категорию
«специализация × грейд». Работодатель описывает потребность, получает подборку с обоснованием и сам
отправляет приглашение с вилкой зарплаты. Контакты открываются после согласия кандидата.
У каждого факта профиля — метка происхождения: ФСП, тест или со слов кандидата.
"""

app = FastAPI(title="Разряд — API", version="0.1.0", description=DESCRIPTION)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")], allow_methods=["*"], allow_headers=["*"])
for r in (auth, catalog, candidate, test, fsp, employer, tasks):
    app.include_router(r.router, prefix="/api")


@app.on_event("startup")
def init_db():
    Base.metadata.create_all(engine)


@app.get("/api/health", tags=["service"])
def health():
    return {"ok": True, "llm": settings.llm_provider, "mail": settings.mail_mode}
