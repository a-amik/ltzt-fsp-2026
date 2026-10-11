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
from .models import Candidate, ColleagueRef, Employer, FspAchievement, Invite, Task, TaskAnswer, Token, User, Vacancy

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


# ── Рынок: компании, вакансии, задания, приглашения ───────────────────
# Все компании вымышленные. У каждой — профиль, статус найма, критерии подбора,
# вакансии с вилкой и задание категории: кандидату есть куда смотреть и откликаться.
MARKET = [
    {"email": "hr@severbank.example", "name": "Северный банк", "field": "Финтех, банк", "size": "1000+", "city": "Санкт-Петербург", "site": "severbank.example",
     "about": "Розничный банк на 4 млн клиентов: мобильное приложение, платежи, антифрод. 300 инженеров, свой процессинг.",
     "inn": "7801234560", "prefs": {"specs": ["backend", "mobile", "ml"], "grades": [2, 3], "formats": ["гибрид", "офис"], "cities": ["Санкт-Петербург"], "confirmed_only": True},
     "vacs": [("Бэкенд-разработчик, платежи", "backend", 3, ["Java", "PostgreSQL", "Kafka"], 330000, 420000, "удалённо", "Команда платежей, 9 человек, работает из разных городов.", ["СБП и переводы", "идемпотентность и сверка"]),
              ("Android-разработчик, мобильный банк", "mobile", 2, ["Kotlin"], 230000, 300000, "гибрид", "Мобильный банк, 12 человек.", ["экраны переводов", "модульность"]),
              ("ML-инженер, антифрод", "ml", 3, ["Python", "PyTorch", "MLflow"], 350000, 450000, "офис", "Антифрод, 6 человек.", ["модели в реальном времени", "мониторинг дрейфа"])],
     "task": ("Двойное списание", "backend", 3, "Клиент дважды нажал «Оплатить», запросы пришли с разницей 40 мс на два разных узла. Как гарантировать одно списание? 3–5 предложений.")},
    {"email": "jobs@medtechplus.example", "name": "МедТех Плюс", "field": "Медицина, B2B SaaS", "size": "200–1000", "city": "Казань", "site": "medtechplus.example",
     "about": "Медицинская информационная система для 900 клиник: запись, электронная карта, телемедицина.",
     "inn": "1650123457", "prefs": {"specs": ["frontend", "backend"], "grades": [1, 2], "formats": ["удалённо", "гибрид"], "cities": [], "fsp_first": True},
     "vacs": [("Фронтенд-разработчик, электронная карта", "frontend", 2, ["TypeScript", "React"], 200000, 260000, "удалённо", "Карта пациента, 6 человек.", ["формы на 200 полей", "офлайн-режим"]),
              ("Младший бэкенд-разработчик", "backend", 1, ["Python", "PostgreSQL"], 110000, 150000, "гибрид", "Расписание и запись, 5 человек.", ["слоты врачей", "уведомления"])],
     "task": ("Форма на 200 полей", "frontend", 2, "Форма осмотра — 200 полей, ввод тормозит на слабых ноутбуках клиник. Что проверите первым и как ускорите? 3–5 предложений.")},
    {"email": "team@lentadannyh.example", "name": "Лента данных", "field": "Аналитика, ритейл", "size": "50–200", "city": "Москва", "site": "lentadannyh.example",
     "about": "Аналитика продаж для сетей магазинов: 2 млрд чеков в год, витрины и прогноз спроса.",
     "inn": "7704567891", "prefs": {"specs": ["data", "ml"], "grades": [2, 3, 4], "formats": ["удалённо", "гибрид", "офис"], "cities": ["Москва"]},
     "vacs": [("Аналитик данных, прогноз спроса", "data", 2, ["SQL", "Python", "ClickHouse"], 210000, 280000, "удалённо", "Прогноз, 4 человека.", ["витрины по магазинам", "проверка прогноза"]),
              ("Ведущий инженер данных", "data", 4, ["ClickHouse", "Airflow"], 450000, 550000, "гибрид", "Платформа данных, 8 человек.", ["хранилище на 2 млрд строк", "наставничество"])],
     "task": ("Дубли в чеках", "data", 2, "В витрине продаж выросла выручка на 3 %, а в кассах — нет. Как найдёте причину? Опишите шаги и запросы словами.")},
    {"email": "it@umnygorod.example", "name": "Умный город", "field": "Городские сервисы, госИТ", "size": "200–1000", "city": "Новосибирск", "site": "umnygorod.example",
     "about": "Платформа городских сервисов: транспорт, ЖКХ, обращения жителей. Инфраструктура в своём облаке.",
     "inn": "5406123458", "prefs": {"specs": ["devops", "backend"], "grades": [2, 3], "formats": ["офис", "гибрид"], "cities": ["Новосибирск", "Томск"]},
     "vacs": [("DevOps-инженер, своё облако", "devops", 3, ["Kubernetes", "Terraform", "Prometheus"], 280000, 360000, "гибрид", "Платформа, 7 человек.", ["кластер на 400 узлов", "наблюдаемость"]),
              ("Бэкенд-разработчик, обращения жителей", "backend", 2, ["Go", "PostgreSQL"], 190000, 250000, "офис", "Обращения, 5 человек.", ["маршрутизация обращений", "интеграции с ведомствами"])],
     "task": None},
    {"email": "hr@ritmpay.example", "name": "Ритм-Платёж", "field": "Финтех, платежи", "size": "50–200", "city": "Москва", "site": "ritmpay.example",
     "about": "Платёжный шлюз для интернет-магазинов. Найм на паузе до января: команда укомплектована.",
     "inn": "7709876543", "hiring": "paused", "prefs": {"specs": ["backend"], "grades": [3], "formats": ["удалённо"]},
     "vacs": [("Старший бэкенд-разработчик, шлюз", "backend", 3, ["Go", "Redis"], 340000, 420000, "удалённо", "Шлюз, 5 человек.", ["задержка до 50 мс"])],
     "task": None},
]


def ensure_market(db) -> None:
    """Досев компаний рынка: идемпотентно, по почте компании. Стенду пересев не нужен."""
    for m in MARKET:
        if db.query(User).filter_by(email=m["email"]).first():
            continue
        u = User(email=m["email"], role="employer", email_confirmed=True, consent_at=datetime.utcnow())
        db.add(u)
        db.flush()
        e = Employer(user_id=u.id, name=m["name"], about=m["about"], field=m["field"], contact=m["email"], inn=m["inn"], verified=True,
                     size=m["size"], city=m["city"], site=m["site"], hiring=m.get("hiring", "active"), prefs=m["prefs"])
        db.add(e)
        db.flush()
        for (title, sp, g, stack, lo, hi, wf, team, tasks) in m["vacs"]:
            db.add(Vacancy(employer_id=e.id, title=title, spec=sp, grade=g, stack=stack, salary_from=lo, salary_to=hi, work_format=wf, team=team, tasks=tasks))
        if m["task"]:
            title, sp, g, text = m["task"]
            db.add(Task(employer_id=e.id, title=title, spec=sp, grade=g, text=text))
    db.commit()


def ensure_statuses(db, seed: int = 7) -> None:
    """Статусы поиска и условия у синтетических кандидатов: кто-то ищет, кто-то
    только рассматривает, кто-то не ищет вовсе. Только если их ещё не раздавали."""
    if db.query(Candidate).filter(Candidate.wants.isnot(None)).count() > 5:
        return
    r = random.Random(seed)
    fields = ["Финтех", "Ритейл", "Медицина", "Логистика", "ГосИТ"]
    for c in db.query(Candidate).filter(Candidate.spec.isnot(None)):
        if c.wants is not None:
            continue
        c.search = r.choices(["active", "open", "closed"], weights=[6, 3, 1])[0]
        fm = [c.work_format] + ([x for x in WORK_FORMATS if x != c.work_format and r.random() < 0.35])
        c.wants = {"formats": fm, "cities": [c.city] if c.city and c.work_format != "удалённо" else [], "relocate": r.random() < 0.2,
                   "fields": r.sample(fields, r.choice([0, 0, 1, 2])), "hide": []}
    db.commit()


ASK_POOL = ["Кто будет руководителем и как устроена команда?", "Как пересматривают зарплату?", "Как устроен онбординг в первый месяц?",
            "Можно ли работать из другого города?", "Сколько этапов собеседования?", "Какой технический долг в проекте?"]
SERGEY_AGENT = {"importance": {"pay": "stop", "format": "high", "stack": "low", "grade": "high", "motive": "high"},
                "stops": ["office", "outstaff"], "asks": ["Кто будет руководителем и как устроена команда?", "Есть ли путь до руководителя направления?", "Как пересматривают зарплату?"],
                "brief": "Ищу продуктовую компанию с нагрузкой, где через год можно вырасти до руководителя направления. Стек вторичен, деньги — нет",
                "auto_decline": True}


def ensure_agents(db, seed: int = 11) -> None:
    """Настройка агента у части кандидатов: важность критериев, стоп-факторы, вопросы компаниям."""
    if db.query(Candidate).filter(Candidate.agent.isnot(None)).count() > 5:
        return
    r = random.Random(seed)
    demo = db.query(User).filter_by(email=DEMO_EMP_EMAIL).first()
    for c in db.query(Candidate).filter(Candidate.spec.isnot(None)):
        if demo and c.user_id == demo.id:
            continue  # у Сергея своя настройка
        if c.agent is not None or r.random() > 0.55:
            continue
        imp = {k: r.choices(["high", "low", "stop"], weights=[6, 2, 1])[0] for k in ("pay", "format", "stack", "motive")}
        c.agent = {"importance": imp, "stops": r.sample(["office", "duty", "outstaff", "grey", "longtest"], r.choice([0, 1, 1, 2])),
                   "asks": r.sample(ASK_POOL, r.choice([1, 2, 3])), "brief": "", "auto_decline": r.random() < 0.3}
    db.commit()


TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))


def mail_of(name: str, n: int) -> str:
    """Почта кандидата по имени: k.smirnov252@mail.ru — как у живых людей, без служебных доменов."""
    parts = [("".join(TR.get(ch, ch) for ch in w.lower())) for w in name.split()]
    return f"{parts[0][0]}.{parts[-1]}{n}@{['mail.ru', 'yandex.ru', 'gmail.com'][n % 3]}" if len(parts) > 1 else f"user{n}@mail.ru"


def ensure_mails(db) -> None:
    """Служебные адреса cand0000@demo.razryad — в почты по именам."""
    for u in db.query(User).filter(User.email.like("%@demo.razryad")):
        c = db.query(Candidate).filter_by(user_id=u.id).first()
        if c and c.name:
            u.email = mail_of(c.name, c.id)
    db.commit()


DEMO_EMP_EMAIL = "hr@transcode.example"


def ensure_demo_dual(db) -> None:
    """Демо-аккаунт с двумя профилями: Сергей Морозов, техлид тарифов «ТрансКода».
    Нанимает в свою команду от имени компании и сам рассматривает предложения:
    своя компания его профиля не видит, остальные — видят и пишут."""
    ensure_market(db)
    ensure_statuses(db)
    ensure_agents(db)
    ensure_mails(db)
    u = db.query(User).filter_by(email=DEMO_EMP_EMAIL).first()
    if not u:
        return
    e = db.query(Employer).filter_by(user_id=u.id).first()
    if e and not e.city:
        e.size, e.city, e.site = "200–1000", "Москва", "transcode.example"
        e.prefs = {"specs": ["backend", "frontend", "data"], "grades": [1, 2, 3], "formats": ["гибрид", "удалённо", "офис"], "cities": ["Москва"], "fsp_first": True}
    own = db.query(Candidate).filter_by(user_id=u.id).first()
    if own:
        if own.agent is None:
            own.agent = SERGEY_AGENT
        db.commit()
        return
    stack = ["Python", "PostgreSQL", "Kafka", "Redis"]
    c = Candidate(user_id=u.id, name="Сергей Морозов", phone="+7 900 000-00-00", city="Москва", spec="backend", stack=stack, work_format="гибрид",
                  salary=380000, years=8, claimed_grade=3, grade=3, theta=1.12, se=0.27, grade_since=datetime.utcnow() - timedelta(days=21),
                  fsp_id="fsp-100009", search="open", agent=SERGEY_AGENT,
                  wants={"formats": ["гибрид", "удалённо"], "cities": ["Москва"], "relocate": False, "fields": ["Финтех"], "hide": [], "note": "Рост до руководителя направления"},
                  facts=[{"k": "Стек", "v": ", ".join(stack), "src": "word", "approved": True},
                         {"k": "Опыт", "v": "8 лет коммерческой разработки", "src": "word", "approved": True},
                         {"k": "Места работы", "v": "ТрансКод — 4 г. (сейчас, техлид команды тарифов); Финпоток — 3 г.; веб-студия — 1 г.", "src": "word", "approved": True},
                         {"k": "Формат", "v": "гибрид", "src": "word", "approved": True},
                         {"k": "Роль в команде", "v": "техлид, 7 человек", "src": "word", "approved": True},
                         {"k": "Английский", "v": "B2", "src": "word", "approved": True},
                         {"k": "Почему ищет", "v": "рост до руководителя направления", "src": "word", "approved": True}])
    db.add(c)
    db.flush()
    db.add(FspAchievement(candidate_id=c.id, fsp_id="fsp-100009", event="Кубок Федерации по спортивному программированию", level="всероссийское",
                          discipline="продуктовое программирование", year=2025, place=4, participants=180, team="Команда №12", role="капитан", rank="I разряд"))
    # Приглашения от других компаний: кабинет кандидата у демо-аккаунта живой с первого входа.
    bank = db.query(Employer).filter_by(name="Северный банк").first()
    lenta = db.query(Employer).filter_by(name="Лента данных").first()
    t0 = datetime.utcnow()
    if bank:
        v = db.query(Vacancy).filter_by(employer_id=bank.id, spec="backend").first()
        db.add(Invite(employer_id=bank.id, candidate_id=c.id, vacancy_id=v.id if v else None, title="Бэкенд-разработчик, платежи",
                      text="Сергей, видели ваш подтверждённый «Старший» и Кубок Федерации. Команде платежей нужен человек, который вырастет в лида направления.",
                      salary_from=380000, salary_to=450000, contact="hr@severbank.example", work_format="гибрид",
                      log=[{"t": (t0 - timedelta(hours=5)).isoformat(), "s": "отправлено"}]))
    if lenta:
        db.add(Invite(employer_id=lenta.id, candidate_id=c.id, title="Бэкенд потоковой загрузки чеков",
                      text="Ищем инженера на загрузку 2 млрд чеков в год: Kafka и PostgreSQL — ваш стек.",
                      salary_from=320000, salary_to=360000, contact="team@lentadannyh.example", work_format="удалённо", status="просмотрено",
                      log=[{"t": (t0 - timedelta(days=2)).isoformat(), "s": "отправлено"}, {"t": (t0 - timedelta(days=1)).isoformat(), "s": "просмотрено"}]))
    db.commit()


# ── Отзывы: репутация компаний, отзывы коллег, рекомендации ────────────
# Открытые отзывы — только оценка и число, без текстов (решение участника 11.10.2026).
REPUTATION = {
    "ТрансКод": {"staff": {"n": 4, "avg": 3.9, "notes": ["Сильная команда, релизы с переработками", "Вилку держат, пересмотр раз в год"]},
                 "open": [{"src": "Dream Job", "rating": 4.1, "count": 37}, {"src": "Хабр Карьера", "rating": 4.0, "count": 21}], "cands_note": "Отвечают за 2 дня, вилку держат"},
    "Северный банк": {"staff": {"n": 9, "avg": 3.6, "notes": ["Стабильно, но много согласований", "Хороший ДМС, медленные релизы"]},
                      "open": [{"src": "Dream Job", "rating": 3.7, "count": 412}, {"src": "Хабр Карьера", "rating": 3.8, "count": 96}], "cands_note": "Отвечают за 3 дня, три этапа собеседования"},
    "МедТех Плюс": {"staff": {"n": 3, "avg": 4.3, "notes": ["Удалёнка без оговорок", "Нагрузка ровная, продукт полезный"]},
                    "open": [{"src": "Dream Job", "rating": 4.4, "count": 58}], "cands_note": "Отвечают в тот же день"},
    "Лента данных": {"staff": {"n": 2, "avg": 4.0, "notes": ["Сильные аналитики, процессов мало"]},
                     "open": [{"src": "Хабр Карьера", "rating": 4.2, "count": 14}], "cands_note": "Отвечают за 2 дня"},
    "Умный город": {"staff": {"n": 5, "avg": 3.4, "notes": ["Сроки диктует госзаказчик", "Своё облако, интересная инфраструктура"]},
                    "open": [{"src": "Dream Job", "rating": 3.5, "count": 73}], "cands_note": "Отвечают за неделю"},
    "Ритм-Платёж": {"staff": {"n": 2, "avg": 4.1, "notes": ["Маленькая сильная команда"]},
                    "open": [{"src": "Dream Job", "rating": 4.0, "count": 19}], "cands_note": "Найм на паузе"},
}


def ensure_refs(db, seed: int = 13) -> None:
    """Репутация компаний и стартовые отзывы: у трети кандидатов — готовые отзывы коллег, у части — рекомендации."""
    from .core.refs import answer_for, colleagues
    for name, rep in REPUTATION.items():
        e = db.query(Employer).filter_by(name=name).first()
        if e and not e.reputation:
            e.reputation = rep
    db.commit()
    if db.query(ColleagueRef).count():
        return
    r = random.Random(seed)
    for c in db.query(Candidate).filter(Candidate.spec.isnot(None)).order_by(Candidate.id):
        roll = r.random()
        if roll > 0.45:
            continue
        cols = colleagues(db, c, limit=3)
        for o, where in cols[: 1 + int(r.random() * 2)]:
            db.add(ColleagueRef(candidate_id=c.id, author_id=o.id, kind="review", status="ready", relation=where, answers=answer_for(c, o)))
        if roll < 0.2 and cols:
            o, where = cols[-1]
            db.add(ColleagueRef(candidate_id=c.id, author_id=o.id, kind="rec", status="answered", relation=where, approved=True, answers=answer_for(c, o)))
    db.commit()


def ensure_persona_refs(db) -> None:
    """Готовым аккаунтам — входящие запросы отзывов о бывших коллегах, чтобы вкладка «Отзывы» была живой."""
    from .core.refs import colleagues
    bank = db.query(Employer).filter_by(name="Северный банк").first()
    med = db.query(Employer).filter_by(name="МедТех Плюс").first()
    for tok in ("persona-cand-middle", "demo-employer-token"):
        t = db.get(Token, tok)
        me = t and db.query(Candidate).filter_by(user_id=t.user_id).first()
        if not me or db.query(ColleagueRef).filter_by(author_id=me.id, status="asked").first():
            continue
        for (o, where), e in zip(colleagues(db, me, limit=2), (bank, med)):
            if not db.query(ColleagueRef).filter_by(candidate_id=o.id, author_id=me.id).first():
                db.add(ColleagueRef(candidate_id=o.id, author_id=me.id, employer_id=e.id if e else None, kind="review", status="asked", relation=where))
    db.commit()


# ── Готовые входы: разные типы кандидатов и компаний ───────────────────
# Токен вешается на уже засеянного человека нужного типа; повторный старт ничего не меняет.
PERSONAS = [
    {"key": "cand-middle", "side": "cand", "title": "Бэкенд, средний, грейд подтверждён", "hint": "Результаты ФСП, ищет работу, есть приглашения",
     "q": lambda db: db.query(Candidate).filter(Candidate.spec == "backend", Candidate.grade == 2, Candidate.fsp_id.isnot(None), Candidate.search == "active")},
    {"key": "cand-junior", "side": "cand", "title": "Фронтенд, младший, грейд не подтверждён", "hint": "Тест не сдан, в выдаче ниже подтверждённых",
     "q": lambda db: db.query(Candidate).filter(Candidate.spec == "frontend", Candidate.grade.is_(None), Candidate.claimed_grade == 1)},
    {"key": "cand-senior-open", "side": "cand", "title": "Аналитик данных, старший", "hint": "Не ищет активно, рассматривает предложения",
     "q": lambda db: db.query(Candidate).filter(Candidate.spec == "data", Candidate.grade == 3, Candidate.search == "open")},
    {"key": "cand-lead-closed", "side": "cand", "title": "DevOps, ведущий", "hint": "Не ищет работу: в выдаче его нет",
     "q": lambda db: db.query(Candidate).filter(Candidate.spec == "devops", Candidate.grade == 4), "set": {"search": "closed"}},
    {"key": "cand-intern", "side": "cand", "title": "Машинное обучение, стажёр", "hint": "Первая работа, учебные проекты",
     "q": lambda db: db.query(Candidate).filter(Candidate.spec == "ml", Candidate.claimed_grade == 0)},
    {"key": "dual", "side": "both", "title": "Техлид «ТрансКода», ищет работу", "hint": "Два профиля: кандидат и компания",
     "token": "demo-employer-token"},
    {"key": "emp-bank", "side": "emp", "title": "Финтех, 1000+ человек", "hint": "Нанимает: бэкенд, мобильная разработка, ML", "email": "hr@severbank.example"},
    {"key": "emp-paused", "side": "emp", "title": "Платежи, 50–200 человек", "hint": "Найм на паузе", "email": "hr@ritmpay.example"},
]


def ensure_personas(db) -> None:
    for p in PERSONAS:
        tok = p.get("token") or f"persona-{p['key']}"
        if p.get("token") or db.get(Token, tok):
            continue
        if "q" in p:
            c = p["q"](db).order_by(Candidate.id).first()
            uid = c.user_id if c else None
            for k, v in (p.get("set") or {}).items():
                if c:
                    setattr(c, k, v)
        else:
            u = db.query(User).filter_by(email=p["email"]).first()
            uid = u.id if u else None
        if uid:
            db.add(Token(token=tok, user_id=uid))
    db.flush()
    t = db.get(Token, "persona-cand-middle")
    c = t and db.query(Candidate).filter_by(user_id=t.user_id).first()
    if c:
        _persona_invites(db, c)
    db.commit()
    ensure_refs(db)
    ensure_persona_refs(db)


def _persona_invites(db, c) -> None:
    """Средний бэкенд с подтверждённым грейдом получает живые приглашения: одно новое, одно просмотренное."""
    if db.query(Invite).filter_by(candidate_id=c.id).first():
        return
    t0 = datetime.utcnow()
    for name, status, hours in (("Умный город", "отправлено", 3), ("ТрансКод", "просмотрено", 30)):
        e = db.query(Employer).filter_by(name=name).first()
        v = e and db.query(Vacancy).filter_by(employer_id=e.id, spec="backend", grade=2).first()
        if not v:
            continue
        log = [{"t": (t0 - timedelta(hours=hours)).isoformat(), "s": "отправлено"}]
        if status == "просмотрено":
            log.append({"t": (t0 - timedelta(hours=hours - 4)).isoformat(), "s": "просмотрено"})
        db.add(Invite(employer_id=e.id, candidate_id=c.id, vacancy_id=v.id, title=v.title, status=status, log=log,
                      text=f"{c.name.split()[0]}, увидели подтверждённый «Средний» и ваш стек. Хотим познакомиться: 30 минут с техлидом.",
                      salary_from=v.salary_from, salary_to=v.salary_to, contact=e.contact, work_format=v.work_format))


def personas(db) -> list[dict]:
    """Готовые входы для экрана входа: имя, тип, подсказка и токен."""
    out = []
    for p in PERSONAS:
        tok = p.get("token") or f"persona-{p['key']}"
        t = db.get(Token, tok)
        if not t:
            continue
        c = db.query(Candidate).filter_by(user_id=t.user_id).first()
        e = db.query(Employer).filter_by(user_id=t.user_id).first()
        name = (c.name if p["side"] in ("cand", "both") and c else e.name if e else "") or ""
        out.append({"key": p["key"], "side": p["side"], "token": tok, "name": name, "title": p["title"], "hint": p["hint"]})
    return out


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
                      facts=[{"k": "Стек", "v": ", ".join(stack), "src": "word", "approved": True},
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
    ensure_demo_dual(db)
    ensure_personas(db)
    print(f"кандидатов: {db.query(Candidate).count()}, подтверждённых: {db.query(Candidate).filter(Candidate.grade.isnot(None)).count()}, "
          f"с историей ФСП: {db.query(Candidate).filter(Candidate.fsp_id.isnot(None)).count()}; токен работодателя: demo-employer-token")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    run(a.n, reset=a.reset)
