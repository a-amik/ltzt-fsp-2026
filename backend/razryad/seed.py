"""Синтетические данные: банк кандидатов, работодатель с вакансиями и заданием.

Запуск: `uv run python -m razryad.seed [--n 600]`. Кандидаты получают θ из смеси
нормальных распределений по грейдам и «сдают» тест по модели IRT — так банк
согласован с механикой, а не придуман отдельно. Используется и для валидации.
"""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta

from .core import bank, fsp_mock
from .core.catalog import GRADE_MID, SPECS, WORK_FORMATS, grade_of
from .core.irt import estimate, p_correct, pick_next, prior_for, should_stop
from .db import Base, SessionLocal, engine
from .models import Candidate, Employer, FspAchievement, Task, TaskAnswer, Token, User, Vacancy

LAST = ["Смирнов", "Иванова", "Кузнецов", "Попова", "Соколов", "Лебедева", "Козлов", "Новикова", "Морозов", "Волкова", "Зайцев", "Павлова"]
FIRST = ["Мария", "Анна", "Елена", "Алексей", "Иван", "Дмитрий", "Никита", "Артём", "Софья", "Дарья", "Кирилл", "Максим"]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург", "Томск", "Иннополис", "Нижний Новгород"]
ROLES = ["разработчик", "техлид небольшой команды", "наставник стажёров", "владелец сервиса"]
COMPANIES = ["ТрансКод", "Облачный склад", "Северный банк", "Лента данных", "ГеоСервис", "студия «Пиксель»", "Ритм-Платёж",
             "МедТех Плюс", "Логика Торга", "Кода-Интегратор", "Финпоток", "Умный город", "веб-студия", "стартап на 12 человек"]
F_FIRST = ["Мария", "Анна", "Елена", "Софья", "Дарья", "Ксения", "Полина", "Алина"]
M_FIRST = ["Алексей", "Иван", "Дмитрий", "Никита", "Артём", "Кирилл", "Максим", "Егор"]
M_LAST = ["Смирнов", "Иванов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Волков", "Зайцев", "Павлов"]


def person(r: random.Random) -> str:
    last = r.choice(M_LAST)
    return f"{r.choice(F_FIRST)} {last}a".replace("вa", "ва").replace("нa", "на") if r.random() < 0.4 else f"{r.choice(M_FIRST)} {last}"


def workplaces(r: random.Random, years: int) -> str:
    if years == 0:
        return "стажировки и учебные проекты"
    n = 1 if years < 3 else 2 if years < 6 else 3
    jobs = r.sample(COMPANIES, n)
    left, out = years, []
    for k, j in enumerate(jobs):
        y = left if k == n - 1 else max(1, left // (n - k) + r.choice([-1, 0, 1]))
        y = max(1, min(y, left - (n - k - 1)))
        left -= y
        out.append(f"{j} — {y} г.")
    return "; ".join(out)


WHY = ["хочу в продукт с нагрузкой", "рост до техлида", "переезд в другой город", "нужна команда сильнее"]


def simulate_test(spec: str, true_theta: float, claimed: int, r: random.Random, mode="full"):
    """Кандидат с истинным θ сдаёт адаптивный тест: ответ верен с вероятностью p(θ)."""
    pool = bank.for_spec(spec)
    answers, used = [], set()
    theta, se = prior_for(claimed), 1.0
    while True:
        t, _ = pick_next(theta, pool, used, r)
        if not t:
            break
        used.add(t.id)
        ok = r.random() < p_correct(true_theta, t.a, t.b)
        answers.append({"a": t.a, "b": t.b, "score": 1.0 if ok else 0.0, "tpl": t.id})
        theta, se = estimate(answers, prior_for(claimed))
        if should_stop(len(answers), se, mode):
            break
    return theta, se, answers


DEMO_CANDIDATE_TOKEN = "demo-candidate-token"


def ensure_demo_candidate(db) -> None:
    """Вход демо-кандидата для доски макетов: токен на засеянном кандидате.

    Берём бэкендера уровня «Средний» с подтверждённым грейдом и историей ФСП,
    чтобы страницы кандидата открывались с данными. Без пересева: токен вешается
    на того, кто уже есть, и повторный старт ничего не меняет."""
    if db.get(Token, DEMO_CANDIDATE_TOKEN):
        return
    c = (db.query(Candidate).filter(Candidate.spec == "backend", Candidate.grade == 2, Candidate.fsp_id.isnot(None))
         .order_by(Candidate.id).first())
    if not c:
        return
    db.add(Token(token=DEMO_CANDIDATE_TOKEN, user_id=c.user_id))
    db.commit()


def run(n: int = 600, seed: int = 2026, reset: bool = False):
    if reset:
        # Сброс — пересоздание схемы целиком: частичная очистка оставляла сессии тестов
        # и приглашения, и SQLite отдавал их номера новым кандидатам.
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    r = random.Random(seed)
    for i in range(n):
        sp = SPECS[i % len(SPECS)]
        true_grade = r.choices(range(5), weights=[1, 3, 4, 2.5, 1])[0]
        true_theta = max(-2.8, min(2.8, GRADE_MID[true_grade] + r.gauss(0, 0.45)))
        claimed = true_grade if r.random() < 0.75 else min(4, true_grade + 1)  # четверть завышает
        theta, se, answers = simulate_test(sp["id"], true_theta, claimed, r)
        confirmed = grade_of(theta) >= claimed
        email = f"cand{i:04d}@demo.razryad"
        u = User(email=email, role="candidate", email_confirmed=True, consent_at=datetime.utcnow())
        db.add(u)
        db.flush()
        stack = r.sample(sp["stack"], 2 + int(r.random() * 3))
        fmt = r.choice(WORK_FORMATS)
        years = [0, 1, 3, 5, 8][true_grade] + int(r.random() * 3)
        base = [70, 120, 220, 340, 450][true_grade] * 1000
        c = Candidate(user_id=u.id, name=person(r), city=r.choice(CITIES), spec=sp["id"], stack=stack,
                      work_format=fmt, salary=round(base * (0.85 + r.random() * 0.35) / 10000) * 10000, years=years,
                      claimed_grade=claimed, grade=claimed if confirmed else None, theta=theta if confirmed else None, se=se if confirmed else None,
                      grade_since=datetime.utcnow() - timedelta(days=int(r.random() * 160)) if confirmed else None,
                      facts=[{"k": "Стек", "v": ", ".join(stack), "src": "test" if confirmed else "word", "approved": True},
                             {"k": "Опыт", "v": f"{years} лет коммерческой разработки", "src": "word", "approved": True},
                             {"k": "Места работы", "v": workplaces(r, years), "src": "word", "approved": True},
                             {"k": "Формат", "v": fmt, "src": "word", "approved": True},
                             {"k": "Роль в команде", "v": r.choice(ROLES), "src": "word", "approved": r.random() > 0.3},
                             {"k": "Английский", "v": r.choice(["B1", "B2", "C1"]), "src": "word", "approved": r.random() > 0.4},
                             {"k": "Почему ищет", "v": r.choice(WHY), "src": "word", "approved": r.random() > 0.5}],
                      fsp_id=f"fsp-{200000 + i}" if r.random() < 0.42 else None)
        db.add(c)
        db.flush()
        if c.fsp_id:
            for _ in range(1 + int(r.random() * 3)):
                ev, level, disc = r.choice(fsp_mock.EVENTS)
                parts = 40 + int(r.random() * 300)
                db.add(FspAchievement(candidate_id=c.id, fsp_id=c.fsp_id, event=ev, level=level, discipline=disc, year=2022 + int(r.random() * 4),
                                      place=1 + int(r.random() * min(30, parts)), participants=parts, team=f"Команда №{1 + int(r.random() * 90)}",
                                      role=r.choice(["капитан", "бэкенд", "фронтенд", "аналитик"]), rank=r.choice(fsp_mock.RANKS)))
    # Демонстрационный работодатель
    eu = User(email="hr@transcode.example", role="employer", email_confirmed=True, consent_at=datetime.utcnow())
    db.add(eu)
    db.flush()
    e = Employer(user_id=eu.id, name="ТрансКод", about="Платформа городской логистики: 14 млн поездок в месяц, 60 разработчиков.",
                 field="Логистика, B2B", contact="hr@transcode.example", inn="7701234567", verified=True)
    db.add(e)
    db.flush()
    db.add(Token(token="demo-employer-token", user_id=eu.id))
    db.add_all([
        Vacancy(employer_id=e.id, title="Бэкенд-разработчик, сервис тарифов", spec="backend", grade=2, stack=["Python", "PostgreSQL", "Kafka"],
                salary_from=220000, salary_to=300000, work_format="гибрид", team="Команда тарифов, 7 человек: считаем цену поездки в реальном времени.",
                tasks=["пересчёт тарифов под нагрузкой 3 тыс. запросов в секунду", "перевод расчёта с монолита на события Kafka"]),
        Vacancy(employer_id=e.id, title="Фронтенд-разработчик, кабинет водителя", spec="frontend", grade=1, stack=["TypeScript", "React"],
                salary_from=120000, salary_to=170000, work_format="удалённо", team="Кабинет водителя, 5 человек.", tasks=["таблицы на 10 тыс. строк", "дизайн-система"]),
        Vacancy(employer_id=e.id, title="Старший инженер данных", spec="data", grade=3, stack=["SQL", "ClickHouse", "Airflow"],
                salary_from=330000, salary_to=420000, work_format="офис", team="Хранилище риск-моделей.", tasks=["витрины для скоринга", "контроль качества данных"]),
    ])
    t = Task(employer_id=e.id, title="Пересчёт тарифа без лишней работы", spec="backend", grade=2,
             text="Тариф поездки пересчитывается при каждом изменении пробок — 3 тыс. событий в секунду. Как не пересчитывать лишнее? Опишите подход в 3–5 предложениях.")
    db.add(t)
    db.flush()
    cat = db.query(Candidate).filter_by(spec="backend", grade=2).limit(4).all()
    texts = ["Пересчитываю только затронутые участки: событие пробки → зоны по геоиндексу → пересчёт этих зон. Остальное из кэша с TTL 30 секунд.",
             "Дебаунс по зоне: копим события 2–3 секунды и пересчитываем один раз. Цена фиксируется на момент заказа, задержка допустима.",
             "Kafka с ключом по зоне, потребитель держит последнее состояние и считает, только если изменение больше порога 5 %.",
             "Можно пересчитывать всё по крону раз в минуту, этого хватит."]
    for c, txt in zip(cat, texts):
        db.add(TaskAnswer(task_id=t.id, candidate_id=c.id, text=txt))
    db.commit()
    print(f"кандидатов: {db.query(Candidate).count()}, подтверждённых: {db.query(Candidate).filter(Candidate.grade.isnot(None)).count()}, "
          f"с историей ФСП: {db.query(Candidate).filter(Candidate.fsp_id.isnot(None)).count()}; токен работодателя: demo-employer-token")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    run(a.n, reset=a.reset)
