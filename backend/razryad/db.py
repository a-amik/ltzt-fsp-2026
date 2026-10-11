"""Подключение к базе. SQLite для разработки и тестов, PostgreSQL на стенде."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    url = url or settings.database_url
    kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, **kw)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns(eng=None) -> None:
    """Лёгкая миграция: create_all не трогает существующие таблицы, поэтому новые
    столбцы модели добавляем ALTER TABLE с умолчанием. Удалений и переименований нет."""
    from sqlalchemy import inspect, text
    eng = eng or engine
    insp = inspect(eng)
    with eng.begin() as cx:
        for t in Base.metadata.sorted_tables:
            if not insp.has_table(t.name):
                continue
            have = {c["name"] for c in insp.get_columns(t.name)}
            for col in t.columns:
                if col.name in have:
                    continue
                kind = col.type.compile(eng.dialect)
                d = col.default.arg if col.default is not None and not callable(col.default.arg) else None
                lit = "" if d is None else f" DEFAULT {int(d) if isinstance(d, bool) else repr(d) if isinstance(d, str) else d}"
                cx.execute(text(f'ALTER TABLE {t.name} ADD COLUMN {col.name} {kind}{lit}'))
