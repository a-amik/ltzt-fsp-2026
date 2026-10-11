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
from .scoring import GRADE_WORDS, SPEC_WORDS, find_grade, parse_money, parse_need, work_format

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
    return work_format(t)


# ── Разбор резюме ─────────────────────────────────────────────────────
# Резюме читаем по разделам: места работы, должность, грейд и стаж — из раздела опыта
# (строки с периодами работы), стек — из перечней навыков, а не из любого упоминания в тексте.

_B = r"(?<![a-zа-яё])"  # граница слова слева для латиницы и кириллицы
_E = r"(?![a-zа-яё])"
TECH = {  # технология справочника → шаблон по тексту в нижнем регистре
    "Python": r"python", "Java": r"java(?!script)", "PostgreSQL": r"postgres(?:ql)?", "Kafka": r"kafka", "Redis": r"redis",
    "Docker": r"docker", "TypeScript": r"typescript", "React": r"react(?![\s-]*native)", "Vue": r"vue(?:\.?js)?",
    "Next.js": r"next\.?js", "CSS": r"css", "Webpack": r"webpack", "Kotlin": r"kotlin", "Swift": r"swift",
    "Flutter": r"flutter", "React Native": r"react[\s-]*native", "SQL": r"sql", "ClickHouse": r"click\s?house",
    "Airflow": r"airflow", "Tableau": r"tableau", "PyTorch": r"py\s?t\s?orch", "scikit-learn": r"scikit[\s-]?learn|sklearn",
    "CUDA": r"cuda", "MLflow": r"mlflow", "Kubernetes": r"kubernetes|k8s", "Terraform": r"terraform", "Linux": r"linux",
    "Ansible": r"ansible", "Prometheus": r"prometheus",
}
TECH_RX = {k: re.compile(_B + f"(?:{v})" + _E) for k, v in TECH.items()}
GO_RX = re.compile(r"(?<![A-Za-z])(?:Go|[Gg]olang)(?![A-Za-z])")  # «Go» — только с заглавной: в английском тексте go — глагол
TECH_SPECS = {t: [s["id"] for s in SPECS if t in s["stack"]] for sp in SPECS for t in sp["stack"]}
# Упоминание «для галочки»: от такого слова до конца фразы технологии в стек не идут.
WEAK = re.compile(r"(?:дополнительн|в меньшей степени|знаком(?:ство)?(?:\s+с)?\b|изучаю|осваиваю|изучал\w* основ|интересуюсь|интересует|"
                  r"планирую|хочу (?:изучить|освоить)|базов\w* (?:знани|уровн)|начальн\w* уровн|familiar|basic knowledge|"
                  r"working knowledge|exposure to|currently learning|learning basics)[^.]*?(?:\.(?=\s|$)|$)", re.I)

MON = (r"(?:январ\w*|феврал\w*|март\w*|апрел\w*|ма[йяе]|июн\w*|июл\w*|август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*|"
       r"янв|фев|мар|апр|авг|сент?|окт|ноя|дек|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
       r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")
YEAR = r"(?:19[7-9]\d|20[0-4]\d)"
PRESENT = (r"(?:по\s+)?(?:настоящее\s+время|наст\.?\s*вр(?:емя)?\.?|н\.\s?в\.?|сейчас|текущ\w+ время|present|now|current(?:ly)?|"
           r"today|till now|to date)")
DATE = rf"(?:(?P<{{0}}m>{MON}),?\s+)?(?P<{{0}}y>{YEAR})"
RANGE = re.compile(_B + DATE.format("a") + r"\s*(?:–|—|-|−|to|по|until|till)\s*(?:" + DATE.format("b") + "|(?P<now>" + PRESENT + "))" + _E, re.I)
DATE_ANY = re.compile(rf"(?:{MON},?\s+)?{YEAR}|{PRESENT}", re.I)
ONE_YEAR = re.compile(rf"(?:^|\|)\s*(?P<y>{YEAR})\s*(?=,|\||$)")
DURATION = re.compile(r"\b\d+\s*(?:год|года|лет|месяц\w*|мес\.?|years?|yrs?|months?|mos?)\b\.?", re.I)
_MON_N = {"янв": 1, "jan": 1, "фев": 2, "feb": 2, "мар": 3, "mar": 3, "апр": 4, "apr": 4, "ма": 5, "may": 5, "июн": 6, "jun": 6,
          "июл": 7, "jul": 7, "авг": 8, "aug": 8, "сен": 9, "sep": 9, "окт": 10, "oct": 10, "ноя": 11, "nov": 11, "дек": 12, "dec": 12}

HEADERS = {
    "exp": ["опыт работы", "опыт", "профессиональный опыт", "трудовой опыт", "места работы", "карьера", "work experience",
            "experience", "professional experience", "employment", "employment history", "work history", "career", "relevant experience"],
    "skills": ["навыки", "ключевые навыки", "профессиональные навыки", "технические навыки", "hard skills", "skills", "technical skills",
               "core skills", "key skills", "стек", "технологии", "стек технологий", "tech stack", "technologies", "компетенции",
               "инструменты", "tools", "языки программирования"],
    "summary": ["о себе", "обо мне", "about", "about me", "summary", "professional summary", "profile", "профиль", "цель",
                "objective", "highlights"],
    "other": ["образование", "education", "проекты", "projects", "личные проекты", "собственные проекты", "пет проекты",
              "пет-проекты", "pet projects", "side projects", "personal projects", "достижения", "achievements", "языки",
              "languages", "интересы", "хобби", "interests", "hobbies", "курсы", "курсы и тренинги", "сертификаты", "certificates",
              "certifications", "open source", "publications", "публикации", "patent", "patents", "дополнительное образование",
              "контакты", "contacts", "ссылки и контакты", "занятость", "для hr", "гибкие навыки", "soft skills", "awards",
              "награды", "volunteering", "references", "рекомендации", "дополнительно", "дополнительная информация",
              "additional information"],
}
_HDR_WORDS = sorted(((h.split(), k) for k, hs in HEADERS.items() for h in hs), key=lambda x: -len(x[0]))
INLINE_HDR = re.compile(r"\s*\b(Опыт работы|Обо мне|О себе|Образование|Ключевые навыки|Навыки|Проекты|Work Experience|"
                        r"Experience|Education|Skills|Projects)\b\s*")

ROLE_RX = re.compile(_B + r"(?:разработчи\w*|программист\w*|developer|engineer\w*|инженер\w*|architect|архитектор\w*|lead|лид|"
                     r"тимлид\w*|техлид\w*|manager|менеджер\w*|intern|стаж[её]р\w*|тестировщи\w*|tester|qa|analyst|аналитик|"
                     r"scientist|consultant|консультант\w*|специалист\w*|specialist|руководител\w*|director|директор\w*|devops|sre|"
                     r"administrator|администратор\w*|cto|head of|founder|основател\w*)" + _E)
ROLE_AT = re.compile(r"(?P<role>[^|•:]{0,60}?" + _B + r"(?:разработчи\w*|программист\w*|developer|engineer\w*|инженер\w*|architect|"
                     r"архитектор\w*|lead|тимлид\w*|техлид\w*|manager|менеджер\w*|intern|стаж[её]р\w*|тестировщи\w*|analyst|"
                     r"аналитик\w*|scientist|consultant|специалист\w*|руководител\w*|director|директор\w*)(?:\s*\([^)]{1,20}\))?)"
                     r"\s+(?:в|at|@)\s+(?P<co>.+)", re.I)
NOT_COMPANY = re.compile(r"фриланс|freelance|самозанят|проектн\w* деятельн|собственн|личн\w* проект|pet[- ]?проект|self-employed|"
                         r"частн\w* практик|учёба|учеба|университет|university|институт \w+ образован|participation|responsibilit|обязанност|"
                         r"achievement|достижени|задачи|tasks|проект\b|project\b", re.I)
PLACES = {"россия", "russia", "рф", "москва", "moscow", "санкт-петербург", "спб", "remote", "удалённо", "удаленно", "армения",
          "беларусь", "казахстан", "usa", "seoul", "seattle"}
ORG_FORM = re.compile(r"(?<![\w])(?:ООО|ОАО|АО|ПАО|ЗАО|ГК|LLC|Inc\.?|Ltd\.?)\s*[«\"“]([^»\"”\n]{2,40})[»\"”]")

GRADE_RX = [(4, r"тимлид\w*|техлид\w*|team\s?lead|tech\s?lead|technical lead|lead|лид|ведущ\w*|head of|principal|staff"),
            (3, r"senior|сеньор|синьор|старш\w*"), (2, r"middle\+?|мидл"), (1, r"junior|джун\w*|младш\w*"),
            (0, r"intern|trainee|стаж[её]р\w*|практикант\w*")]
GRADE_RX = [(g, re.compile(_B + f"(?:{p})" + _E, re.I)) for g, p in GRADE_RX]
SPEC_RX = {
    "ml": r"ml|mlops|machine learning|deep learning|data scien\w*|nlp|computer vision|ai engineer|машинн\w* обучени\w*|нейросет\w*",
    "data": r"data analyst|data engineer|analytics engineer|bi[- ]analyst|bi[- ]аналитик\w*|аналитик\w* данных|дата[- ]?(?:аналитик|инженер)\w*|аналитик|dwh",
    "devops": r"devops|sre|site reliability|infrastructure engineer|platform engineer|cloud engineer|системн\w* администратор\w*|sysadmin|инфраструктур\w*",
    "mobile": r"ios|android|mobile|мобильн\w*|flutter|react native",
    "frontend": r"frontend|front-end|front end|фронтенд\w*|фронт-енд\w*|фронт|ui developer|верстальщик\w*",
    "backend": r"backend|back-end|back end|бэкенд\w*|бекенд\w*|бэк-енд\w*|серверн\w*|server-side",
}
SPEC_RX = {k: re.compile(_B + f"(?:{v})" + _E, re.I) for k, v in SPEC_RX.items()}
LANG_BACK = re.compile(_B + r"(?:python|golang|go|java(?!script)|php|c#|\.net|ruby|scala|node\.?js|c\+\+|rust|elixir|erlang)" + _E, re.I)
SOFT = [
    ("коммуникация", r"коммуникаб\w*|коммуникативн\w*|communication skills|communicative|общительн\w*"),
    ("наставничество", r"наставни\w*|ментор\w*|mentor\w*|coach\w*|обучал\w* (?:\w+ ){0,2}(?:разработчик|коллег|джун|стаж|сотрудник|новичк|инженер)\w*|"
                       r"trained (?:\w+ ){0,3}(?:engineers|developers)|educating developers"),
    ("лидерство", r"лидерск\w*|лидерств\w*|leadership|led (?:a |the )?(?:\w+ ){0,2}teams?|leading (?:\w+ ){0,2}teams?|"
                  r"руководил\w* (?:\w+ ){0,2}(?:команд|групп|отдел)\w*|координировал\w* (?:\w+ )?команд\w*|управлял\w* команд\w*|"
                  r"coordinated a team|building (?:\w+ ){0,2}teams|тимлид\w*|техлид\w*|team\s?lead|tech\s?lead"),
    ("работа в команде", r"работ\w* в команде|командн\w* (?:работ|игрок)\w*|team player|teamwork|team work|работать в коллективе"),
    ("английский", r"английск\w*|english"),
    ("аналитическое мышление", r"аналитическ\w* (?:склад|мышлени|способност|ум)\w*|analytical (?:thinking|skills|mind)\w*"),
    ("обучаемость", r"обучаем\w*|fast learner|quick learner|быстро (?:обучаюсь|учусь)"),
    ("стрессоустойчивость", r"стрессоустойчив\w*|stress[- ]resistan\w*"),
    ("ответственность", r"ответственност\w*|ответственный подход"),
]
SOFT = [(k, re.compile(_B + f"(?:{v})" + _E, re.I)) for k, v in SOFT]
CITY_LABEL = re.compile(_B + r"(?:город(?:\s+проживания)?|местонахождение|местоположение|проживаю(?:\s+в)?|проживает|живу\s+в|location|"
                        r"based\s+in|локация)\s*[:\-–—]?\s*(?P<v>[^|·\n;]{2,60})", re.I)
CITY_TAIL = re.compile(r"(?:^|[|,·]\s*)(?:г\.\s*)?([А-ЯЁ][а-яё]+(?:-[А-ЯЁ]?[а-яё]+)*(?:\s[А-ЯЁ][а-яё]+)?),\s*(?:Россия|РФ|Russia)\b")
COUNTRY = re.compile(r"^(?:россия|рф|russia|беларусь|казахстан|армения|украина|грузия|сербия|usa|сша)$", re.I)
PHONE = re.compile(r"(?<![\w+])(?:\+7|8|\+\d{1,3})[\s(.-]*\d{3}[\s).-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}(?!\d)"
                   r"|(?<![\w(])\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
FORMAT_NOISE = re.compile(r"hybrid (?:mobile )?app\w*|гибридн\w* приложени\w*|(?:ms |microsoft )?office (?:365|suite)|ms office|"
                          r"microsoft office|remote[- ]?config\w*|remote control|удал[её]нн\w* (?:сервер|доступ|репозитор|машин|хост)\w*", re.I)


def _prep(text: str) -> list[str]:
    """Строки резюме без мусора вёрстки. PDF, где каждое слово на своей строке, склеиваем во фразы;
    строку, оборванную на запятой, — со следующей."""
    for a, b in (("ﬁ", "fi"), ("ﬂ", "fl"), ("ĸ", "к"), (" ", " "), ("​", ""), ("\r", "")):
        text = text.replace(a, b)
    text = re.sub(r"\[([^\]\n]+)\]\([^)\s]+\)", r"\1", text)  # Markdown: [текст](ссылка) → текст
    text = re.sub(r"\*\*|__|`|[\U0001F000-\U0001FFFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]", "", text)
    lines = [ln for ln in (re.sub(r"^#{1,6}\s+|^-{3,}$", "", re.sub(r"\s+", " ", x).strip()).strip() for x in text.split("\n")) if ln]
    if len(lines) >= 40 and sum(len(ln.split()) == 1 for ln in lines) >= 0.7 * len(lines):
        flat = re.sub(r"\s+([,.;:])", r"\1", " ".join(ln for ln in lines if ln not in ("•", "·")))
        flat = INLINE_HDR.sub(lambda m: f"\n{m.group(1)}\n", flat)
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁ])|\n", flat) if s.strip()]
    lines = [ln for ln in lines if not re.fullmatch(r"[•·\-–—*ü▪◦]+", ln)]
    out: list[str] = []
    for ln in lines:
        if out and not _header(ln) and (re.search(r"[,(/&+]$|\s(?:и|and)$", out[-1]) or ln.startswith("|")):
            out[-1] = out[-1] + " " + ln
        else:
            out.append(ln)
    return out


def _header(ln: str) -> str | None:
    """Заголовок раздела: короткая строка без цифр из списка известных («Опыт работы», «Skills / Tools»)."""
    s = re.sub(r"^[^\wа-яё]+|[\s:.]+$", "", ln.lower()).strip()
    if not s or len(s) > 40 or re.search(r"\d", s):
        return None
    words = re.sub(r"[/&,]", " ", s).split()
    for hw, kind in _HDR_WORDS:
        if words[:len(hw)] == hw and len(words) - len(hw) <= 2 and (len(words) == len(hw) or len(hw) > 1 or kind != "exp"):
            return kind
    return None


def _sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    out, kind, cur = [], "head", []
    for ln in lines:
        k = _header(ln)
        if k:
            out.append((kind, cur))
            kind, cur = k, []
        else:
            cur.append(ln)
    out.append((kind, cur))
    return out


def _dateish(ln: str) -> bool:
    """Строка из одних дат: вёрстка PDF выносит периоды в отдельную колонку."""
    return not DATE_ANY.sub("", ln).strip(" -–—,.|")


def _strip_bullet(ln: str) -> str:
    return re.sub(r"^[•·\-–—*ü▪◦]\s*", "", ln).strip()


def _month(m: str | None) -> int | None:
    if not m:
        return None
    m = m.lower()
    return _MON_N.get(m[:3]) or (5 if m.startswith("ма") else None)


def _periods(text: str, single: bool, months_only: bool) -> list[tuple[int, int]]:
    """Периоды работы в месяцах от нулевого года: «Май 2024 — настоящее время», «2012-2020», «| 2021»."""
    from datetime import date
    today = date.today()
    now = today.year * 12 + today.month
    out = []
    for m in RANGE.finditer(text):
        ma, mb = _month(m.group("am")), _month(m.group("bm"))
        if months_only and ma is None:
            continue
        start = int(m.group("ay")) * 12 + (ma or 1)
        end = now if m.group("now") else int(m.group("by")) * 12 + ((mb + 1) if mb else 1)
        if start < end <= now + 1:
            out.append((start, min(end, now)))
    if single:
        for ln in text.split("\n"):
            if not RANGE.search(ln):
                for m in ONE_YEAR.finditer(_strip_bullet(ln)):
                    y = int(m.group("y"))
                    out.append((y * 12 + 1, min((y + 1) * 12 + 1, now)))
    return out


def _union_years(periods: list[tuple[int, int]]) -> int:
    total, cur = 0, None
    for s, e in sorted(periods):
        if cur and s <= cur[1]:
            cur = (cur[0], max(cur[1], e))
        else:
            if cur:
                total += cur[1] - cur[0]
            cur = (s, e)
    if cur:
        total += cur[1] - cur[0]
    return total // 12


def _years_phrase(t: str) -> int | None:
    m = (re.search(r"опыт[^\n\d]{0,30}?(\d{1,2})(?:[.,]\d+)?\s*\+?\s*(?:лет|года|год)", t)
         or re.search(r"(\d{1,2})\+?\s*(?:лет|года|год)[^\n]{0,24}(?:опыт|коммерческ|разработк|пишу|работаю|программирую)", t)
         or re.search(r"(\d{1,2})(?:[.,]\d+)?\+?\s*years?(?:\s+of)?(?:\s+[a-z-]+){0,2}\s+(?:experience|exp\b)", t)
         or re.search(r"experience[^\n\d]{0,20}(\d{1,2})\+?\s*years", t))
    return int(m.group(1)) if m else None


def _roleish(s: str) -> bool:
    return bool(ROLE_RX.search(s.lower()))


def _is_company(s: str) -> bool:
    s = s.strip(" «»\"'.,;:()-–—")
    if len(s) < 2 or len(s) > 70 or len(s.split()) > 10 or not re.search(r"[A-Za-zА-Яа-яЁё]{2}", s) or _dateish(s):
        return False
    low = s.lower()
    if NOT_COMPANY.search(low) or _roleish(s) or low in PLACES or re.fullmatch(r"[A-Z]{2}", s) or re.fullmatch(PRESENT, low):
        return False
    words = low.split()
    if len(words) >= 4 and re.search(r"(?:ed|ing|ал|ил|ял|ел|лся|лась)$", words[0]):  # «Prepared the Cards…» — фраза, не компания
        return False
    if s[0].isalpha() and s[0].islower():
        return bool(re.fullmatch(r"[a-z][\w.-]+", s))  # «netboxify» — бренд со строчной; русская строчная — уже фраза
    return True


def _clean_co(s: str) -> str:
    s = re.split(r"\s*\(|\s+\|\s+|\s+[-–—]\s+", s)[0].strip(" \"'.,;:-–—")
    return s if s.count("«") == s.count("»") else s.strip("«»")


def _jobs(lines: list[str], fallback: bool) -> list[dict]:
    """Строки с периодами работы → [{company, role}]. «Должность | Компания | Период», «Компания - Должность Период»,
    «Должность в Компания», «Role at Company», строка компании над строкой «должность: период»."""
    jobs = []
    for i, raw in enumerate(lines):
        ln = _strip_bullet(raw)
        m = ROLE_AT.search(ln)
        if m and _is_company(_clean_co(RANGE.split(m.group("co"))[0])):
            co = _clean_co(re.split(r",", RANGE.split(m.group("co"))[0])[0])
            jobs.append({"company": co, "role": m.group("role").strip(" ,.-–—")})
            continue
        has_range = RANGE.search(ln)
        if not has_range and (fallback or not ONE_YEAR.search(ln)):
            continue
        rest = RANGE.sub(" ", ln)
        rest = ONE_YEAR.sub(" ", rest) if not has_range else rest
        rest = re.sub(r"\([^)]*\)", " ", DURATION.sub(" ", rest))
        segs = [s.strip(" .,;:-–—()") for s in re.split(r"\s*(?:\||;|,|:|·|\s[-–—]\s|\.\s|\s@\s|\sat\s)\s*", rest)]
        segs = [s for s in segs if s and not re.fullmatch(r"[\d\W]+", s)]
        roles = [s for s in segs if _roleish(s)]
        cos = [s for s in segs if not _roleish(s) and _is_company(s)]
        co = cos[0] if cos else ""
        prev = _strip_bullet(lines[i - 1]) if i else ""
        # Строка выше — компания, если она короткая и не похожа на пункт списка дел («Разработал…», «Built…», «Helping…»).
        first_word = prev.split()[0].lower() if prev else ""
        prev_ok = (prev and not RANGE.search(prev) and ":" not in prev and len(prev.split()) <= 8 and not lines[i - 1].startswith(("•", "-"))
                   and not re.search(r"(?:ed|ing|л|ла|лся|лась)$", first_word))
        named = any(NOT_COMPANY.search(x) for x in segs)  # «Freelance - Software Engineer»: место названо, хоть и не компания
        if not co and roles and prev_ok and not named and not _roleish(prev):
            first = re.split(r"\s*[,|]\s*", prev)[0]
            co = first if _is_company(first) else ""
        if not roles and prev_ok and _roleish(prev):
            roles = [prev]
        if not segs and not fallback and i + 1 < len(lines):  # «Компания» / «Декабрь 2022 — Май 2025» / «Tech Lead, …»
            co = co or (prev if prev_ok and not named and _is_company(prev) else "")
            roles = [x for x in re.split(r"\s*,\s*", _strip_bullet(lines[i + 1])) if _roleish(x) and len(x.split()) <= 5][:2]
        if co or roles:
            jobs.append({"company": _clean_co(co) if co else "", "role": ", ".join(roles)[:80]})
    return jobs


def _techs(s: str) -> set[str]:
    s = WEAK.sub(" ", s)
    low = s.lower()
    found = {k for k, rx in TECH_RX.items() if rx.search(low)}
    if GO_RX.search(s):
        found.add("Go")
    return found


def _is_list(ln: str) -> bool:
    """«Подпись: a, b, c» — строка-перечень навыков."""
    m = re.match(r"^[•·\-–*]?\s*([^:–—|]{2,40}?)\s*[:–—]\s*(.+)$", ln)
    return bool(m) and len(m.group(1).split()) <= 5 and m.group(2).count(",") + m.group(2).count("|") >= 2


def _spec_of(s: str) -> str | None:
    hits = [(m.start(), k) for k, rx in SPEC_RX.items() for m in [rx.search(s)] if m]
    return min(hits)[1] if hits else None


def _grade_of(s: str) -> int | None:
    found = [g for g, rx in GRADE_RX if rx.search(s)]
    return max(found) if found else None


def _name(lines: list[str]) -> str:
    m = re.search(r"(?i:меня зовут|my name is)\s+([А-ЯЁA-Z][а-яёa-z-]+\s+[А-ЯЁA-Z][а-яёa-z-]+)", " ".join(lines))
    if m:
        return m.group(1)
    for ln in lines:
        s = re.split(r"\s+[–—|·-]\s+|[,|·•]|(?=GitHub|LinkedIn|E-?mail|Email|Telegram|Phone|Тел\.|https?://)", ln)[0].strip()
        if re.search(r"(?<!\S)[^\W\d_](?!\S)", s):  # «Aleksa Ć ukovi ć» — буквы, разнесённые вёрсткой PDF
            s = re.sub(r"(?<!\S)([^\W\d_])\s(?=[^\W\d_]{2,})", r"\1", s)
            s = re.sub(r"([^\W\d_]{2,})\s([^\W\d_])(?!\S)", r"\1\2", s)
        words = s.split()
        if not 2 <= len(words) <= 3 or re.search(r"резюме|resume|\bcv\b|опыт|разработчик|инженер|developer|engineer|программист|"
                                                 r"навыки|skills|summary|контакт|experience|образован|education|location|телефон|email",
                                                 s.lower()):
            continue
        if not all(re.fullmatch(r"[^\W\d_][^\W\d_'’]*(?:-[^\W\d_]+)?", w) and w[0].isupper() and len(w) >= 2 for w in words):
            continue
        upper = [w.isupper() for w in words]
        if any(upper) and not all(upper):
            continue
        return " ".join("-".join(p.capitalize() for p in w.split("-")) for w in words) if all(upper) else s
    return ""


def _city(head: list[str], text: str) -> str:
    for m in CITY_LABEL.finditer(text):
        for part in m.group("v").split(","):
            p = re.sub(r"^г\.\s*|[.\s]+$", "", part.strip())
            if p and not COUNTRY.match(p) and p[0].isupper() and re.fullmatch(r"[^\W\d_]+(?:[- ][^\W\d_]+){0,2}", p):
                return p
    for ln in head:
        m = CITY_TAIL.search(ln)
        if m:
            return m.group(1)
    return ""


def parse_resume(text: str) -> dict:
    """Резюме, выгруженное из hh.ru, Хабр Карьеры, LinkedIn или написанное своими словами.
    Всё распознанное получает метку «со слов», пока его не подтвердит тест."""
    lines = _prep(text)
    full = "\n".join(lines)
    t = full.lower()
    secs = _sections(lines)
    head = [ln for ln in secs[0][1] if not _dateish(ln)][:12]
    summary = next((ls[:2] for k, ls in secs if k == "summary" and ls), [])
    exp = [ln for k, ls in secs if k == "exp" for ln in ls]

    jobs = _jobs(exp, fallback=False)
    if not jobs:  # раздела опыта нет или вёрстка увела его в конец файла — ищем по всему тексту, строже
        jobs = _jobs(lines, fallback=True)
    places = []
    for j in jobs:
        co = j["company"]
        if co and not any(co.lower() in p.lower() or p.lower() in co.lower() for p in places):
            places.append(co)
    if not places:
        places = [m.group(0).strip() for m in ORG_FORM.finditer(text)][:4]
    role = jobs[0]["role"] if jobs else ""

    # Стаж: фраза «опыт N лет» → сумма периодов раздела опыта → периоды с месяцами по всему тексту.
    years = _years_phrase(t)
    if years is None:
        per = _periods("\n".join(exp), single=True, months_only=False)
        years = _union_years(per or _periods(full.replace("\n", " "), single=False, months_only=True))

    # Специализация: заголовок резюме и «о себе» → последняя должность → стек.
    spec = next((s for s in map(_spec_of, head + summary) if s), None) or (_spec_of(role) if role else None)
    if not spec and role and LANG_BACK.search(role):
        spec = "backend"

    # Стек: перечни навыков; технологии из строк «Стек:» в опыте — только своей специализации;
    # без перечней — упоминания своей специализации и то, что названо не меньше двух раз.
    main, job, prose = set(), set(), {}
    for k, ls in secs:
        for ln in ls:
            found = _techs(ln)
            if not found:
                continue
            if k == "exp":
                if re.match(r"^[•·\-–*]?\s*(?:стек|stack|технологии|tech stack|tools|использовал\w*|used|environment)\b", ln, re.I):
                    job |= found
                else:
                    for f in found:
                        prose[f] = prose.get(f, 0) + 1
            elif k == "skills" or _is_list(ln):
                main |= found
            else:
                for f in found:
                    prose[f] = prose.get(f, 0) + 1
    if not spec:
        score = {}
        for tech in (main | job | set(prose)):
            for s in TECH_SPECS.get(tech, []):
                score[s] = score.get(s, 0) + 1 / len(TECH_SPECS[tech])
        spec = max(score, key=score.get) if score else None
    pool = set(next((s["stack"] for s in SPECS if s["id"] == spec), [])) if spec else None
    if main or job:
        stack = main | (job & pool if pool is not None else job)
    else:
        stack = {f for f, n in prose.items() if pool is None or f in pool or n >= 2}

    grade = _grade_of(role) if role else None
    if grade is None:
        grade = next((g for g in map(_grade_of, head) if g is not None), None)

    money = []
    for ln in lines:
        if re.search(r"зарплат|ожидани|₽|руб|на руки", ln.lower()):
            money += parse_money(ln.lower())
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone = PHONE.search(text)
    return {"name": _name([ln for ln in lines[:20] if not _dateish(ln)][:8]),
            "spec": spec, "stack": sorted(stack), "years": years, "workplaces": places[:4],
            "salary": money[0] if money else None, "work_format": work_format(FORMAT_NOISE.sub(" ", t)),
            "email": email.group(0) if email else "", "phone": phone.group(0).strip() if phone else "",
            "grade": grade, "role": role, "city": _city(head, full),
            "soft": [k for k, rx in SOFT if rx.search(t)], "source": "word"}


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
    # О команде — фраза со словом «команда», кроме самого заголовка; с числом людей или «мы/наш» — первой.
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip() and s.strip().rstrip(".") != title and not BULLET.match(s)]
    teamish = [s for s in sents if re.search(r"команд", s.lower()) and 10 < len(s) < 220]
    team = next((s for s in teamish if re.search(r"\d|человек|мы\b|наш", s.lower())), teamish[0] if teamish else "")
    # Грейд — сначала из заголовка: в тексте бывают чужие грейды («менторить middle-разработчиков»).
    g = find_grade(title) if title else None
    grade = g if g is not None else need["grade"]
    # Вилка — из строк про деньги, если такие есть: в остальном тексте числа про нагрузку и людей.
    money_lines = [ln.lower() for ln in lines if re.search(r"зарплат|оклад|вилк|доход|₽|руб|на руки|gross|net|компенсац", ln.lower())]
    lo, hi = need["salary_from"], need["salary_to"]
    if money_lines:
        m2 = parse_need(" ".join(money_lines))
        nums = parse_money(" ".join(money_lines))
        if nums:
            lo, hi = m2["salary_from"], m2["salary_to"]
    found_spec = _spec(t)
    return {"title": title[:90], "spec": need["spec"], "spec_found": found_spec is not None,
            "grade": grade, "grade_found": g is not None or find_grade(t) is not None,
            "stack": need["stack"], "salary_from": lo, "salary_to": hi,
            "work_format": _format(t) or need["work_format"], "team": team, "tasks": tasks[:6]}
