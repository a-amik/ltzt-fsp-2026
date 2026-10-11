import os

os.environ["RZ_DATABASE_URL"] = "sqlite:///./test.db"
if os.path.exists("test.db"):
    os.remove("test.db")

from fastapi.testclient import TestClient  # noqa: E402

from razryad.main import app  # noqa: E402

client = TestClient(app)


def auth(email, role):
    code = client.post("/api/auth/start", json={"email": email, "role": role}).json()["code"]
    r = client.post("/api/auth/confirm", json={"email": email, "code": code, "consent": True}).json()
    return {"Authorization": f"Bearer {r['token']}"}


def test_end_to_end():
    with client:
        c = auth("cand@example.com", "candidate")
        e = auth("hr@firm.example", "employer")
        # опрос и заявленный грейд
        p = client.patch("/api/candidate/profile", json={"name": "Тест Тестов", "spec": "backend", "stack": ["Python", "Kafka"], "work_format": "гибрид", "salary": 250000, "years": 3, "claimed_grade": 2}, headers=c).json()
        assert p["category"]["confirmed"] is False  # до теста категория по заявленному грейду, с меткой
        # ФСП ID: мок OIDC → code → привязка
        r = client.get("/api/fsp-id/authorize", params={"sub": "fsp-100001", "redirect_uri": "http://x/cb"}, follow_redirects=False)
        code = r.headers["location"].split("code=")[1].split("&")[0]
        link = client.post("/api/candidate/fsp/link", json={"code": code}, headers=c).json()
        assert link["achievements"]
        # тест
        s = client.post("/api/test/start", json={"claimed": 2, "mode": "express"}, headers=c).json()
        assert s["current"] and "ok" not in s["current"]
        while not s["finished"]:
            cur = s["current"]
            body = {"text": "Храним счётчики в Redis, скользящее окно, при превышении 429 с Retry-After, при отказе хранилища пропускаем."} if cur.get("open") else {"pick": cur["opts"][0]}
            s = client.post("/api/test/answer", json=body, headers=c).json()
        assert s["verdict"]["kind"] in ("ok", "below")
        prof = client.get("/api/candidate/profile", headers=c).json()
        # работодатель: потребность → подборка → карточка → предразговор → приглашение
        client.patch("/api/employer/company", json={"name": "Фирма", "contact": "hr@firm.example", "inn": "7701234567"}, headers=e)
        need = client.post("/api/employer/needs", json={"text": "Нужен бэкенд средний Python Kafka, гибрид, 220 000 – 300 000"}, headers=e).json()
        sel = client.get(f"/api/employer/needs/{need['id']}/selection", headers=e).json()
        assert sel["total"] >= 1 and sel["items"][0]["display"] and "contacts" not in sel["items"][0]  # имя видно, контакты закрыты до согласия
        cid = sel["items"][0]["id"]
        card = client.get(f"/api/employer/candidates/{cid}", headers=e).json()
        assert "contacts" not in card
        talk = client.post(f"/api/employer/candidates/{cid}/talk", json={"need_id": need["id"]}, headers=e).json()
        assert talk["verdict"]["kind"] in ("ok", "part", "no")
        bad = client.post("/api/employer/invites", json={"candidate_id": cid, "title": "Бэкенд", "salary_from": 0, "salary_to": 0, "contact": "tg"}, headers=e)
        assert bad.status_code == 422  # без вилки приглашение не уходит
        inv = client.post("/api/employer/invites", json={"candidate_id": cid, "title": "Бэкенд", "salary_from": 220000, "salary_to": 300000, "contact": "Телеграм @hr", "need_id": need["id"]}, headers=e).json()
        # кандидат видит вилку до общения, контакт работодателя — после принятия
        mine = client.get("/api/candidate/invites", headers=c).json()
        assert mine[0]["salary_from"] == 220000 and mine[0]["contact"] is None
        client.post(f"/api/candidate/invites/{inv['id']}", json={"status": "просмотрено"}, headers=c)
        acc = client.post(f"/api/candidate/invites/{inv['id']}", json={"status": "принято"}, headers=c).json()
        assert acc["status"] == "принято" and acc["contact"] == "Телеграм @hr"
        card2 = client.get(f"/api/employer/candidates/{cid}", headers=e).json()
        assert card2["contacts"]["email"] == "cand@example.com"
        st = client.get("/api/employer/invites", headers=e).json()
        assert st[0]["status"] == "принято" and len(st[0]["log"]) == 3
        # кандидат не видит чужого
        # У кандидата нет профиля компании, пока он его не заведёт; свой профиль компания не видит.
        assert client.get("/api/employer/invites", headers=c).status_code == 404
        assert client.post("/api/auth/profiles/employer", headers=c).json()["profiles"]["employer"]
        assert client.get("/api/employer/invites", headers=c).status_code == 200
        own = client.get("/api/candidate/profile", headers=c).json()["id"]
        assert client.get(f"/api/employer/candidates/{own}", headers=c).status_code == 404


def test_cooldown_and_openapi():
    with client:
        c = auth("cand2@example.com", "candidate")
        client.patch("/api/candidate/profile", json={"spec": "frontend", "claimed_grade": 1}, headers=c)
        s = client.post("/api/test/start", json={"claimed": 1, "mode": "express"}, headers=c).json()
        while not s["finished"]:
            s = client.post("/api/test/answer", json={"pick": "нет такого"} if not s["current"].get("open") else {"text": "x" * 30}, headers=c).json()
        assert s["verdict"]["kind"] == "below"  # все ответы неверны
        # ступень ниже — сразу
        assert client.post("/api/test/start", json={"claimed": 0, "mode": "express"}, headers=c).status_code == 200
        spec = client.get("/openapi.json").json()
        assert "/api/employer/needs/{need_id}/selection" in spec["paths"]


def test_interview_feedback_and_conduct():
    with client:
        c = auth("cand3@example.com", "candidate")
        e = auth("hr3@firm.example", "employer")
        client.patch("/api/candidate/profile", json={"spec": "backend", "claimed_grade": 2, "salary": 100000}, headers=c)
        s = client.post("/api/test/start", json={"claimed": 2, "mode": "express"}, headers=c).json()
        while not s["finished"]:
            cur = s["current"]
            s = client.post("/api/test/answer", json={**({"text": "x" * 40} if cur.get("open") else {"pick": cur["opts"][0]}), "events": [{"e": "blur"}]}, headers=c).json()
        h = client.get("/api/test/history", headers=c).json()[0]
        assert h["conduct"]["blur"] >= 1 and h["conduct"]["items"] == h["n"]
        cid = client.get("/api/candidate/profile", headers=c).json()["id"]
        inv = client.post("/api/employer/invites", json={"candidate_id": cid, "title": "x", "salary_from": 100000, "salary_to": 200000, "contact": "tg"}, headers=e).json()
        assert client.post(f"/api/employer/invites/{inv['id']}/feedback", json={"grade_ok": True}, headers=e).status_code == 409
        client.post(f"/api/candidate/invites/{inv['id']}", json={"status": "принято"}, headers=c)
        fb = client.post(f"/api/employer/invites/{inv['id']}/feedback", json={"grade_ok": True, "note": "ок"}, headers=e).json()
        assert fb["fact"]["v"] == "подтверждён 1 из 1"
        prof = client.get("/api/candidate/profile", headers=c).json()
        assert any(f["src"] == "interview" for f in prof["facts"])
        card = client.get(f"/api/employer/candidates/{cid}", headers=e).json()
        assert card["conduct"]["items"] >= 3 and any(f["src"] == "interview" for f in card["facts"])


def test_migration_import():
    """Переезд: резюме кандидата и текст своей вакансии раскладываются в поля, всё распознанное — «со слов»."""
    with client:
        c = auth("move@example.com", "candidate")
        e = auth("move-hr@firm.example", "employer")
        r = client.post("/api/candidate/about", json={"text": "Бэкенд на Python, опыт 6 лет, ООО «Северный банк». PostgreSQL, Kafka. Удалённо, ожидания 280 000 ₽ на руки."}, headers=c).json()
        assert r["parsed"]["years"] == 6 and "Kafka" in r["parsed"]["stack"]
        prof = r["profile"]
        assert prof["spec"] == "backend" and prof["work_format"] == "удалённо"
        assert any(f["k"] == "Места работы" and f["src"] == "word" for f in prof["facts"])
        assert all(str(f["v"]).strip() for f in prof["facts"])  # пустые значения в факты не идут
        files = {"file": ("resume.txt", "Опыт работы 4 года. Go, Redis".encode(), "text/plain")}
        assert client.post("/api/candidate/resume", files=files, headers=c).status_code == 200
        v = client.post("/api/employer/vacancies/parse", json={"text": "Бэкенд-разработчик (Middle)\nЗадачи:\n- Писать сервисы на Python\nУсловия: гибрид, 220–300 тыс. ₽"}, headers=e).json()
        assert v["title"].startswith("Бэкенд") and v["grade"] == 2 and v["salary_from"] == 220000 and v["tasks"] == ["Писать сервисы на Python"]
        files = {"file": ("vac.txt", "Фронтенд-разработчик\nReact, TypeScript. Офис, до 250 тыс.".encode(), "text/plain")}
        f = client.post("/api/employer/vacancies/parse-file", files=files, headers=e).json()
        assert f["spec"] == "frontend" and f["salary_to"] == 250000 and f["salary_from"] is None


def test_badge_signed():
    """Значок отдаётся только по подписанному адресу; номер кандидата без подписи ничего не открывает."""
    with client:
        c = auth("badge@example.com", "candidate")
        client.patch("/api/candidate/profile", json={"spec": "frontend", "claimed_grade": 1}, headers=c)
        b = client.get("/api/candidate/badge", headers=c).json()
        r = client.get(b["path"])
        assert r.status_code == 200 and "Фронтенд" in r.text and "не подтверждён" in r.text
        cid = b["path"].split("/")[-1].split("-")[0]
        assert client.get(f"/api/badge/{cid}-0000000000000000.svg").status_code == 404
