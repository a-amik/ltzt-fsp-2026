import random

from razryad.core import bank
from razryad.core.irt import estimate, p_correct, pick_next, should_stop, verdict
from razryad.core.scoring import fsp_strength, parse_money, parse_need, rank
from razryad.core.agents import negotiate


def test_bank_instances_are_unique_per_seed_and_have_answers():
    for t in bank.TEMPLATES:
        a, b = bank.instance(t, 1), bank.instance(t, 2)
        assert a["tpl"] == t.id
        if not a.get("open"):
            assert a["ok"] in a["opts"] and b["ok"] in b["opts"]
            assert "ok" not in bank.public(a)
    assert len(bank.TEMPLATES) >= 30
    assert all(len(bank.for_spec(s)) >= 10 for s in ["backend", "frontend", "mobile", "data", "ml", "devops"])


def test_bank_variety_and_shuffle():
    """Банк: варианты без повторов, эталон на разных местах, текст и (у задач с выбором) ответ зависят от зерна."""
    for t in bank.TEMPLATES:
        xs = [bank.instance(t, s) for s in range(1, 201)]   # instance сам падает на повторе вариантов
        assert len({x["q"] for x in xs}) > 1, t.id
        if not xs[0].get("open"):
            assert len({x["opts"].index(x["ok"]) for x in xs}) > 1, t.id
            assert len({x["ok"] for x in xs}) > 1, t.id
        assert bank.instance(t, 7) == bank.instance(t, 7)  # экземпляр воспроизводим по зерну


def test_estimate_moves_towards_truth():
    r = random.Random(1)
    true = 1.2
    answers = []
    pool = bank.for_spec("backend")
    used = set()
    theta = 0.0
    while not should_stop(len(answers), 9, "full") or len(answers) < 12:
        t, _ = pick_next(theta, pool, used, r)
        if not t:
            break
        used.add(t.id)
        answers.append({"a": t.a, "b": t.b, "score": 1.0 if r.random() < p_correct(true, t.a, t.b) else 0.0})
        theta, se = estimate(answers, 0.0)
    assert abs(theta - true) < 0.9 and se < 0.6


def test_verdict_rules():
    assert verdict(2, 0.1, 0.3)["kind"] == "ok"
    v = verdict(2, -0.9, 0.3)
    assert v["kind"] == "below" and v["offer_down"] == 1
    assert verdict(1, 0.8, 0.2)["offer_up"] is True   # уверенно выше: предлагаем тест выше, грейд сам не растёт
    assert verdict(1, 0.8, 0.2)["grade"] == 1


def test_fsp_strength_counts_results_not_participation():
    assert fsp_strength([]) == 0
    assert fsp_strength([{"place": None, "participants": 100, "year": 2026}]) == 0
    one = fsp_strength([{"place": 3, "participants": 212, "year": 2026}])
    two = fsp_strength([{"place": 3, "participants": 212, "year": 2026}, {"place": 10, "participants": 50, "year": 2025}])
    assert 0.9 < one < 1 and two > one


def test_rank_unconfirmed_below_confirmed():
    base = {"spec": "backend", "claimed_grade": 2, "stack": ["Python"], "fsp": [], "facts": [], "privacy": {}, "salary": None, "work_format": "гибрид"}
    conf = {**base, "id": 1, "grade": 2, "theta": -0.4, "se": 0.3}
    unconf = {**base, "id": 2, "grade": None, "theta": None, "se": None, "stack": ["Python", "PostgreSQL", "Kafka"]}
    need = {"spec": "backend", "grade": 2, "stack": ["Python", "PostgreSQL", "Kafka"]}
    out = rank([unconf, conf], need)
    assert [x["c"]["id"] for x in out] == [1, 2]
    assert rank([unconf, conf], need, {"confirmed_only": True})[0]["c"]["id"] == 1 and len(rank([unconf, conf], need, {"confirmed_only": True})) == 1


def test_rank_over_budget_after_fitting():
    """Ожидания выше вилки больше чем на 10 % — после укладывающихся, даже при лучшем тесте; до 10 % — на общих правах."""
    base = {"spec": "backend", "claimed_grade": 2, "grade": 2, "se": 0.3, "stack": ["Python"], "fsp": [], "facts": [], "privacy": {}, "work_format": "гибрид"}
    strong_dear = {**base, "id": 1, "theta": 0.4, "salary": 400000}
    weaker_fits = {**base, "id": 2, "theta": -0.3, "salary": 280000}
    slightly_over = {**base, "id": 3, "theta": 0.3, "salary": 320000}
    hidden = {**base, "id": 4, "theta": -0.4, "salary": None}
    need = {"spec": "backend", "grade": 2, "stack": ["Python"], "salary_to": 300000}
    assert [x["c"]["id"] for x in rank([strong_dear, weaker_fits, slightly_over, hidden], need)] == [3, 2, 4, 1]
    assert [x["c"]["id"] for x in rank([strong_dear, weaker_fits], {**need, "salary_to": None})] == [1, 2]


def test_fsp_near_discipline_counts_fully():
    e = {"place": 1, "participants": 100, "year": 2026}
    near = fsp_strength([{**e, "discipline": "продуктовое программирование"}], spec="frontend")
    far = fsp_strength([{**e, "discipline": "программирование БАС"}], spec="frontend")
    assert near == 1.0 and abs(far - 0.8) < 1e-9
    assert fsp_strength([e], spec="frontend") == 1.0  # без дисциплины — не штрафуем


def test_parse_money_formats():
    assert parse_money("300 000 – 380 000") == [300000, 380000]
    assert parse_money("от 200к") == [200000]
    assert parse_money("200–250 тыс") == [200000, 250000]
    assert parse_money("от 200 до 260 тыс") == [200000, 260000]
    assert parse_money("вилка 1,2 млн") == [1200000]
    assert parse_money("опыт 3 года, react 18") == []
    assert parse_need("бэкенд от 200к")["salary_to"] is None
    assert parse_need("бэкенд до 300 тыс")["salary_from"] is None


def test_parse_need():
    p = parse_need("Ищем старшего фронтенд-разработчика на React и TypeScript, удалённо, 300 000 – 380 000")
    assert p["spec"] == "frontend" and p["grade"] == 3 and set(p["stack"]) == {"TypeScript", "React"}
    assert p["salary_from"] == 300000 and p["salary_to"] == 380000 and p["work_format"] == "удалённо"


def test_negotiate_only_approved_facts():
    c = {"spec": "backend", "grade": 2, "claimed_grade": 2, "theta": 0.1, "se": 0.3, "stack": ["Python"], "salary": 400000, "privacy": {"salary": True},
         "facts": [{"k": "Стек", "v": "Python", "src": "test", "approved": True}, {"k": "Формат", "v": "офис", "src": "word", "approved": False}]}
    t = negotiate(c, {"stack": ["Python", "Kafka"], "grade": 2, "salary_from": 200000, "salary_to": 300000, "work_format": "удалённо", "tasks": [], "team": ""})
    names = {x["name"]: x["state"] for x in t["crit"]}
    assert names["Формат"] == "nodata" and names["Деньги"] == "no" and t["verdict"]["kind"] == "no"


def test_negotiate_open_top_salary():
    c = {"spec": "backend", "grade": 2, "claimed_grade": 2, "theta": 0.1, "se": 0.3, "stack": ["Python"], "salary": 400000, "privacy": {"salary": True}, "facts": []}
    t = negotiate(c, {"stack": ["Python"], "grade": 2, "salary_from": 200000, "salary_to": 0, "work_format": None, "tasks": [], "team": ""})
    assert {x["name"]: x["state"] for x in t["crit"]}["Деньги"] == "part"


def test_validation_runs_small():
    """Процедура валидации собирается и даёт числа в разумных пределах."""
    import random
    from razryad import validate as V
    w = V.World.make(random.Random(1))
    acc = V.exp_accuracy(w, 60, random.Random(2))
    assert 0.4 < acc["exact"] <= 1.0
    m = V.exp_matching(w, 300, random.Random(3), needs_n=4)
    assert 0 <= m["ours"]["p10"] <= 1


def test_candidate_agent_settings():
    """Настройка агента кандидата меняет переговоры: вопросы, стоп-факторы, важность."""
    from razryad.core.agents import negotiate
    c = {"stack": ["Python"], "grade": 2, "claimed_grade": 2, "theta": 0.1, "se": 0.3, "salary": 300000, "privacy": {"salary": True},
         "facts": [{"k": "Стек", "v": "Python", "src": "test", "approved": True}, {"k": "Формат", "v": "удалённо", "src": "word", "approved": True}]}
    offer = {"stack": ["Python", "Go", "Kafka"], "grade": 2, "salary_from": 200000, "salary_to": 250000, "work_format": "офис", "tasks": [], "team": "Платежи, 5 человек.", "field": "Финтех"}
    base = negotiate(c, offer)
    assert base["verdict"]["kind"] == "no" and not base["asks"]
    c["agent"] = {"importance": {"pay": "low", "format": "low", "stack": "low"}, "stops": [], "asks": ["Кто будет руководителем и как устроена команда?", "Как пересматривают зарплату?"]}
    t = negotiate(c, offer)
    assert t["verdict"]["kind"] == "ok"                      # неважное не портит итог
    assert t["asks"][0]["a"] == "Платежи, 5 человек." and t["asks"][1]["a"] is None
    assert "Как пересматривают зарплату?" in t["open"]
    c["agent"]["stops"] = ["office"]
    t = negotiate(c, offer)
    assert t["verdict"]["kind"] == "no" and t["stops"] == ["Офис без удалёнки"]


def test_parse_resume_sections():
    """Резюме читаем по разделам: места работы — из строк опыта, а не из кавычек; стек — из перечня навыков;
    стаж — по периодам; грейд и должность — по последнему месту."""
    from razryad.core.docs import parse_resume
    text = """Иван Петров
Город: Казань · +7 (900) 123-45-67 · ivan@example.com
Бэкенд-разработчик
Опыт работы
Senior Python-разработчик | ООО «Ромашка» | Март 2022 — Март 2025
Делал сервис «Лидеры цифровой трансформации» для участников «от — до», да.
Стек: Python, PostgreSQL, Kafka, React
Junior разработчик | Северный банк | Январь 2020 — Февраль 2022
Навыки
Python, Docker, Redis, SQL
Дополнительно знаком с: Vue, Kubernetes
Языки: английский B2; наставничество джунов, работа в команде
Образование
КФУ, 2014 — 2019"""
    r = parse_resume(text)
    assert r["name"] == "Иван Петров" and r["city"] == "Казань" and r["spec"] == "backend"
    assert r["workplaces"] == ["ООО «Ромашка»", "Северный банк"]
    assert r["years"] == 5 and r["grade"] == 3 and r["role"] == "Senior Python-разработчик"
    assert r["stack"] == ["Docker", "Kafka", "PostgreSQL", "Python", "Redis", "SQL"]  # React — чужой стек из строки опыта, Vue — «знаком»
    assert {"английский", "работа в команде"} <= set(r["soft"]) and r["phone"].startswith("+7")
    free = parse_resume("Бэкенд на Python, опыт 6 лет, ООО «Северный банк». PostgreSQL, Kafka. Удалённо.")
    assert free["years"] == 6 and free["workplaces"] == ["ООО «Северный банк»"] and free["grade"] is None
