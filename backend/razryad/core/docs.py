"""Переезд на сервис: текст из файла и разбор своих документов на поля.

Работает только со своими данными стороны — резюме кандидата и текстом
вакансии самой компании. Чужие вакансии не импортируем (ответ экспертов ФСП).
Заглушка на правилах; с моделью — структурированный вывод по той же схеме.
"""
from __future__ import annotations

import io
import re
import zipfile

from .catalog import SPECS
from .scoring import GRADE_WORDS, SPEC_WORDS, parse_money, parse_need

ORG = re.compile(r"(?:ООО|АО|ПАО|ЗАО|ИП|ГК|LLC|Inc\.?|Ltd\.?)\s*[«\"]?[\w\- .]{2,40}[»\"]?|«[^»]{2,40}»")
BULLET = re.compile(r"^\s*(?:[-–—•*·]|\d+[.)])\s+(.+)$")


def extract_text(filename: str | None, raw: bytes) -> str:
    """PDF, DOCX или простой текст. Не разобрали — пустая строка, а не ошибка."""
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf") or raw[:4] == b"%PDF":
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)
        if name.endswith(".docx"):
            xml = zipfile.ZipFile(io.BytesIO(raw)).read("word/document.xml").decode("utf-8", "ignore")
            xml = re.sub(r"</w:p>", "\n", xml)
            return re.sub(r"<[^>]+>", "", xml)
    except Exception:
        return ""
    return raw.decode("utf-8", "ignore")


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]


def _spec(t: str) -> str | None:
    return next((s for s, ws in SPEC_WORDS.items() if any(re.search(rf"(?<![a-zа-яё]){re.escape(w)}", t) for w in ws)), None)


def _format(t: str) -> str | None:
    if re.search(r"удал[её]нн|remote", t):
        return "удалённо"
    if "гибрид" in t or "hybrid" in t:
        return "гибрид"
    if re.search(r"(?<![a-zа-яё])офис", t):
        return "офис"
    return None


def parse_resume(text: str) -> dict:
    """Резюме, выгруженное из hh.ru, Хабр Карьеры, LinkedIn или написанное своими словами.
    Всё распознанное получает метку «со слов», пока его не подтвердит тест."""
    t = text.lower()
    lines = _lines(text)
    stack = sorted({s for sp in SPECS for s in sp["stack"] if re.search(rf"(?<![a-z]){re.escape(s.lower())}(?![a-z])", t)})
    # Стаж — только рядом со словом «опыт»: «29 лет, проживает…» в резюме hh.ru — это возраст.
    m = (re.search(r"опыт[^\n\d]{0,24}(\d{1,2})\s*(?:лет|года|год)", t)
         or re.search(r"(\d{1,2})\s*(?:лет|года|год)[^\n]{0,24}(?:опыт|коммерческ|разработк)", t))
    years = int(m.group(1)) if m else 0
    # Имя — первая строка из двух-трёх слов с заглавной, без цифр и служебных слов.
    name = next((ln for ln in lines[:6] if re.fullmatch(r"[А-ЯЁA-Z][а-яёa-z\-]+(?:\s+[А-ЯЁA-Z][а-яёa-z\-]+){1,2}", ln)
                 and not re.search(r"резюме|опыт|разработчик|инженер|developer", ln.lower())), "")
    places = []
    for x in ORG.findall(text):
        x = x.strip(" .,")
        if x and x not in places and len(places) < 4:
            places.append(x)
    money = []
    for ln in lines:
        if re.search(r"зарплат|ожидани|₽|руб|на руки", ln.lower()):
            money += parse_money(ln.lower())
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone = re.search(r"\+?\d[\d\s()-]{9,}\d", text)
    return {"name": name, "spec": _spec(t), "stack": stack, "years": years, "workplaces": places,
            "salary": money[0] if money else None, "work_format": _format(t),
            "email": email.group(0) if email else "", "phone": phone.group(0).strip() if phone else "", "source": "word"}


def parse_vacancy(text: str) -> dict:
    """Текст своей вакансии — в поля формы. Чего нет в тексте, то не выдумываем: поле остаётся пустым."""
    t = text.lower()
    need = parse_need(text)
    lines = _lines(text)
    title = next((ln for ln in lines if 4 <= len(ln) <= 90 and not BULLET.match(ln)), "")
    title = re.sub(r"^(?:вакансия|ищем|нужен|нужна)\s*[:—-]?\s*", "", title, flags=re.I).rstrip(".")
    tasks, in_tasks = [], False
    for ln in lines:
        low = ln.lower()
        if re.match(r"^(?:задачи|что (?:предстоит|делать)|чем (?:предстоит|заниматься)|обязанности)", low):
            in_tasks = True
            continue
        if in_tasks and re.match(r"^(?:требования|мы предлагаем|условия|что мы|о нас|стек|команда)", low):
            in_tasks = False
        b = BULLET.match(ln)
        if in_tasks and b:
            tasks.append(b.group(1).rstrip(".;"))
    team = next((s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if re.search(r"команд", s.lower()) and 10 < len(s) < 220), "")
    found_spec = _spec(t)
    return {"title": title[:90], "spec": need["spec"], "spec_found": found_spec is not None,
            "grade": need["grade"], "grade_found": any(w in t for ws in GRADE_WORDS for w in ws),
            "stack": need["stack"], "salary_from": need["salary_from"], "salary_to": need["salary_to"],
            "work_format": _format(t) or need["work_format"], "team": team, "tasks": tasks[:6]}
