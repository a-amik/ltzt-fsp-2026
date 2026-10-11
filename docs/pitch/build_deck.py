"""Собирает презентацию «Разряда» на шаблоне ФСП.

Вход: base.pptx — шаблон организаторов, где оставлены и расставлены нужные
слайды (титул, о команде, команда, история, коротко о решении, проблема и решение,
стадии, четыре карточки, демо, большой экран, три карточки, шесть пунктов,
пункты, линии, финал). Выход: Razryad-pitch.pptx.

    uv run --with python-pptx python docs/pitch/build_deck.py <base.pptx> <img_dir> <out.pptx>

После ДЕМО встаёт слайд с роликом Razryad-demo.mp4 (обложка — demo-poster.png рядом
со сборщиком): в показе он запускается кликом и идёт без интернета. Номера слайдов
проставляются по порядку в конце сборки.
"""
import copy
import os
import sys

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

BASE, IMG, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
INK, PLUM, PINK, WHITE = '1C1D22', '520978', 'FF0053', 'FFFFFF'  # палитра шаблона ФСП
prs = Presentation(BASE)
S = prs.slides
IN = 914400


def at(slide, x, y, tol=0.08):
    """Фигура по координатам левого верхнего угла (дюймы)."""
    for sh in slide.shapes:
        if sh.left is not None and abs(sh.left / IN - x) < tol and abs(sh.top / IN - y) < tol:
            return sh
    raise KeyError((x, y))


def by_name(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(name)


def put(sh, lines, size=None, bold=None, color=None):
    """Текст в фигуру с сохранением оформления первого абзаца и первого прогона.
    lines — строка или список строк; строка вида ('жирное', 'обычное') даёт два прогона."""
    tf = sh.text_frame
    if isinstance(lines, str):
        lines = [lines]
    p0 = tf.paragraphs[0]
    ppr = copy.deepcopy(p0._p.pPr) if p0._p.pPr is not None else None
    r0 = p0.runs[0]._r if p0.runs else None
    rpr = copy.deepcopy(r0.rPr) if r0 is not None and r0.rPr is not None else None
    for p in list(tf.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    for r in list(p0.runs):
        p0._p.remove(r._r)
    for tag in ('fld', 'br'):
        for f in p0._p.findall('{http://schemas.openxmlformats.org/drawingml/2006/main}' + tag):
            p0._p.remove(f)
    for i, line in enumerate(lines):
        p = p0 if i == 0 else tf.add_paragraph()
        if i and ppr is not None:
            p._p.insert(0, copy.deepcopy(ppr))
        parts = line if isinstance(line, tuple) else (line,)
        for j, part in enumerate(parts):
            run = p.add_run()
            if rpr is not None:
                run._r.insert(0, copy.deepcopy(rpr))
            run.text = part
            if size:
                run.font.size = Pt(size)
            if bold is not None or (isinstance(line, tuple) and j == 0 and len(parts) > 1):
                run.font.bold = True if (isinstance(line, tuple) and j == 0 and len(parts) > 1) else bold
            if color:
                run.font.color.rgb = RGBColor.from_string(color)


def drop(slide, *shapes):
    for sh in shapes:
        sh._element.getparent().remove(sh._element)


def title(slide, text, pill=None, w=None, color=None, size=None):
    """Заголовок слайда в «таблетке» шаблона; таблетку растягиваем под длину."""
    t = next(sh for sh in slide.shapes if sh.is_placeholder and sh.placeholder_format.type == 1) if any(
        sh.is_placeholder and sh.placeholder_format.type == 1 for sh in slide.shapes) else None
    if t is None:
        t = next(sh for sh in slide.shapes if sh.name.startswith('Заголовок'))
    if not t.text_frame.paragraphs[0].runs:
        t.text_frame.text = text
        if color or size:
            for r in t.text_frame.paragraphs[0].runs:
                if color:
                    r.font.color.rgb = RGBColor.from_string(color)
                if size:
                    r.font.size = Pt(size)
    else:
        put(t, text, color=color, size=size)
    if pill is not None and w:
        pill.width = Inches(w)


def textbox(slide, x, y, w, h, lines, size=14, color='1C1D22', bold=False, align=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines if isinstance(lines, list) else [lines]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(6)
        if align:
            p.alignment = align
        parts = line if isinstance(line, tuple) else (line,)
        for j, part in enumerate(parts):
            r = p.add_run()
            r.text = part
            r.font.size = Pt(size)
            r.font.color.rgb = RGBColor.from_string(color)
            r.font.bold = bold or (isinstance(line, tuple) and j == 0 and len(parts) > 1)
    return tb


# ── 1. Титул ─────────────────────────────────────────────────────────
s = S[0]
title(s, 'Разряд', color=WHITE, size=60)
put(by_name(s, 'Текст 4'), 'Команда «Разряд» · Цифровая платформа-агрегатор ИТ-вакансий с верифицированным профилем достижений участника ФСП')

# ── 2. О команде, суть, уникальность ────────────────────────────────
s = S[1]
put(by_name(s, 'Заголовок 6'), 'Работодатель приходит сам', color=PLUM, size=26, bold=True)
put(at(s, 7.45, 2.87), 'Кандидат сдаёт адаптивный тест на свой грейд и попадает в категорию. Работодатель находит категорию, агенты сторон сверяют ожидания, и он сам приглашает человека с вилкой зарплаты.', size=12)
put(at(s, 7.48, 5.33), 'У каждого факта профиля видно происхождение: ФСП, встреча с работодателем, тест или «со слов». Результаты соревнований федерации поднимают кандидата внутри категории.', size=12)
put(at(s, 0.37, 4.25), [('Капитан: ', 'Амбарцум Амаякян, руководитель направления, продукт и разработка'),
                         ('Участников: ', '2'),
                         ('Как собрались: ', 'второй совместный хакатон ЛЦТ после «Маршрута дня» для Билайна'),
                         ('Город: ', 'Москва')], size=12)
ph = at(s, 0.0, 0.37)
pic = s.shapes.add_picture(f'{IMG}/cview.jpg', Inches(0.25), Inches(0.55), height=Inches(3.0))
if pic.width > Inches(6.6):
    r = Inches(6.6) / pic.width
    pic.width, pic.height = Inches(6.6), int(pic.height * r)
drop(s, ph)

# ── 3. Команда ───────────────────────────────────────────────────────
s = S[2]
title(s, 'КОМАНДА')
put(at(s, 0.57, 3.96), 'Амбарцум Амаякян', size=13)
# Контакты — из CONTACTS ниже; пустые строки не печатаем, заглушек «@—» на слайде не бывает.
CONTACTS = {'amik': {'tg': '', 'phone': '', 'org': 'Скорозвон'}, 'ivan': {'tg': '', 'phone': '', 'org': ''}}


def contact_lines(role, c):
    return [role] + [x for x in (f"Телеграм: {c['tg']}" if c['tg'] else '', f"Телефон: {c['phone']}" if c['phone'] else '', c['org']) if x]


put(at(s, 0.57, 4.65), contact_lines('Капитан, продукт и разработка', CONTACTS['amik']), size=10)
put(at(s, 3.09, 3.96), 'Иван Пластун', size=13)
put(at(s, 3.09, 4.65), contact_lines('Консультант по предметной области', CONTACTS['ivan']), size=10)
for x in (5.42, 7.94, 10.46):
    drop(s, at(s, x, 1.66))
for x in (5.61, 8.13, 10.65):
    drop(s, at(s, x, 3.96), at(s, x, 4.65))
for name in ('Рисунок 1', 'Рисунок 2', 'Рисунок 3', 'Рисунок 4', 'Рисунок 5'):
    try:
        drop(s, by_name(s, name))
    except KeyError:
        pass

# ── 4. История и сложности ──────────────────────────────────────────
s = S[3]
title(s, 'ИСТОРИЯ И ВЫЗОВЫ')
put(at(s, 0.58, 1.75), 'Собрались на хакатоне ЛЦТ 2026: до этого вместе делали «Маршрут дня» для Билайна — планировщик выездов инженеров. Для ФСП взяли задачу, где решает не алгоритм, а механика рынка.', size=12)
put(at(s, 0.58, 3.75), 'На рынке найма ИТ работодатель тонет в откликах, а кандидат пишет в пустоту. Хотелось сервис, где первым пишет работодатель — и сразу с деньгами, а победы в соревнованиях ФСП что-то значат для карьеры.', size=12, color=INK)
put(at(s, 0.58, 5.62), 'Без надзора тест не отличает человека от человека с моделью. Мы не стали это прятать: тест — входной билет, а сильнее него в профиле стоят реестр ФСП и итог встречи с работодателем. Проверяли себя на синтетике, и первый прогон показал, что подбор не лучше поиска по резюме — разобрались, почему, и переписали разметку.', size=11, color=INK)

# ── 5. Коротко о решении ─────────────────────────────────────────────
s = S[4]
put(by_name(s, 'Текст 2'), ['Адаптивный тест на модели IRT: банк из 41 калиброванного шаблона, у каждого кандидата свои варианты и свой набор, 6—12 заданий, экспресс — 3—4.',
                             'Категория «специализация × грейд», порядок внутри — тест, стек, ФСП, свежесть, у каждой позиции объяснение.',
                             'Переговоры агентов со всей категорией: общий протокол по пяти критериям.',
                             'FastAPI, React, PostgreSQL, Docker; ФСП ID — по протоколу OIDC.'], size=12)
put(by_name(s, 'Текст 6'), ['Работодатель пишет первым и с вилкой — кандидат видит деньги до разговора.',
                             'Победы в соревнованиях ФСП превращаются в место в выдаче, а не в строчку резюме.',
                             'Работодатель видит, как ведёт себя компания: доля ответов, сроки, вилки против рынка — это защита от фиктивных вакансий.',
                             'Дальше: интеграция с реестром ФСП и ATS работодателей.'], size=12)

# ── 6. Проблема и решение ────────────────────────────────────────────
s = S[5]
title(s, 'ПРОБЛЕМА И РЕШЕНИЕ', pill=at(s, 0.38, 0.35), w=4.6)
put(by_name(s, 'Текст 2'), [('Резюме не проверено. ', 'Отбор идёт по ключевым словам; каждый четвёртый в выдаче по резюме слабее заявленного (наша валидация).')], size=13, color=INK)
put(by_name(s, 'Текст 3'), [('Работодатель приходит сам. ', 'Он ищет в категории, подтверждённой тестом, и пишет первым — с вилкой зарплаты.')], size=13, color=INK)
put(by_name(s, 'Текст 4'), [('Факт с происхождением. ', 'ФСП, встреча, тест или «со слов»: работодатель видит, чему верить, кандидат — как подняться.')], size=13, color=INK)

# ── 7. Стадии: сквозной путь ────────────────────────────────────────
s = S[6]
title(s, 'СКВОЗНОЙ ПУТЬ', pill=at(s, 0.38, 0.35), w=3.9)
steps = [('Вход', 'Почта с кодом или ФСП ID — достижения сами встают в профиль'),
         ('Опрос и тест', 'Специализация, стек, заявленный грейд, адаптивный тест'),
         ('Категория', 'Специализация × грейд, место по силе профиля'),
         ('Подборка и переговоры', 'Агенты сверяют стек, грейд, деньги, формат'),
         ('Приглашение', 'Вилка обязательна, контакты — после «да»')]
for (h, t), (a, b) in zip(steps, [('Текст 1', 'Текст 2'), ('Текст 7', 'Текст 8'), ('Текст 3', 'Текст 4'), ('Текст 9', 'Текст 10'), ('Текст 5', 'Текст 6')]):
    put(by_name(s, a), h, size=13, color=PLUM, bold=True)
    put(by_name(s, b), t, size=10, color=INK)

# ── 8. Механика теста: четыре карточки ──────────────────────────────
s = S[7]
title(s, 'ТЕСТ', pill=at(s, 0.38, 0.35), w=2.2)
cards = [('Шаблон', 'Не задача, а форма с параметрами и эталоном. Сотни вариантов одной трудности: цифры и сюжет у каждого свои.'),
         ('Адаптивный показ', 'Следующее задание — из трёх самых информативных в текущей оценке, одно случайно. Набор у каждого свой.'),
         ('Стоп по точности', '6—12 заданий на грейд, стоп при погрешности ≤ 0,38. Экспресс для жюри — 3—4.'),
         ('Грейд', 'Не прошёл — тест на ступень ниже сразу. Выше — отдельным тестом. Повтор — через 90 дней.')]
for i, (h, t) in enumerate(cards):
    put(by_name(s, f'Текст {14 + i}'), f'0{i + 1}', size=14, color=PINK, bold=True)
    put(by_name(s, f'Текст {1 + 2 * i}'), h, size=14, color=PLUM, bold=True)
    put(by_name(s, f'Текст {2 + 2 * i}'), t, size=11, color=INK)

# ── 9. Демо: кандидат и работодатель ────────────────────────────────
s = S[8]
title(s, 'ДЕМО', pill=at(s, 0.38, 0.35), w=2.2)
for name, img in (('Рисунок 4', 'cview.jpg'), ('Рисунок 5', 'proto.jpg')):
    ph = by_name(s, name)
    s.shapes.add_picture(f'{IMG}/{img}', ph.left, ph.top, width=ph.width, height=ph.height)
    drop(s, ph)
put(by_name(s, 'Текст 2'), [('Кандидат. ', 'Так его видит работодатель: категория, оценка, место в категории, соревнования ФСП и факты «со слов».')], size=12, color=INK)
put(by_name(s, 'Текст 3'), [('Работодатель. ', 'Протокол переговоров агентов: по каждому критерию — совпадает, с оговоркой или расхождение.')], size=12, color=INK)


def browser_label(slide, text):
    """Адресная строка макета браузера в шаблоне — «www.lider.com»; пишем своё."""
    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == 6:  # группа
                yield from walk(sh.shapes)
            else:
                yield sh
    for sh in walk(slide.shapes):
        if sh.has_text_frame and 'lider' in sh.text_frame.text:
            runs = [r for p in sh.text_frame.paragraphs for r in p.runs]
            runs[0].text = text
            for r in runs[1:]:
                r.text = ''


browser_label(s, 'стенд «Разряда»')

# ── 9а. Ролик: сквозной сценарий в самом слайде ─────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
STAND = 'd5d5d58b3bosodm1111q.4kscn31j.apigw.yandexcloud.net'


def add_video_slide(prs, after, layout_from):
    """Слайд «ДЕМО: РОЛИК» с встроенным Razryad-demo.mp4 сразу после слайда after (номер с нуля)."""
    v = prs.slides.add_slide(layout_from.slide_layout)
    for ph in list(v.placeholders):
        if ph.placeholder_format.type != 1:
            drop(v, ph)
    title(v, 'ДЕМО: РОЛИК')
    h = Inches(5.25)
    w = int(h * 1440 / 900)  # ролик 1440 × 900
    v.shapes.add_movie(os.path.join(HERE, 'Razryad-demo.mp4'), Inches(0.55), Inches(1.55), w, h,
                       poster_frame_image=os.path.join(HERE, 'demo-poster.png'), mime_type='video/mp4')
    textbox(v, 9.15, 1.7, 3.75, 5.2, [('Сквозной сценарий, 2 мин 25 с. ', 'Кандидат регистрируется, проходит опрос и адаптивный тест. Работодатель описывает потребность, агент проводит переговоры со всей категорией, приглашение уходит с вилкой. Кандидат принимает — контакты открываются.'),
                                     ('Клик по кадру — запуск. ', 'Ролик встроен в слайд и идёт без интернета.'),
                                     ('Пройти самому: ', STAND)], size=12)
    ids = prs.slides._sldIdLst
    el = ids[-1]
    ids.remove(el)
    ids.insert(after + 1, el)
    return v


# ── 10. Большой экран: переговоры с категорией ──────────────────────
s = S[9]
title(s, 'ПЕРЕГОВОРЫ С КАТЕГОРИЕЙ')
ph = by_name(s, 'Объект 2')
pic = s.shapes.add_picture(f'{IMG}/mass.jpg', Inches(0.55), Inches(1.6), height=Inches(5.2))
if pic.width > Inches(8.1):
    r = Inches(8.1) / pic.width
    pic.width, pic.height = Inches(8.1), int(pic.height * r)
drop(s, ph)
textbox(s, 8.9, 1.75, 3.9, 5.0, [('Один сценарий со всеми. ', 'Агент работодателя проходит стек, грейд, деньги, формат и мотивацию с каждым кандидатом категории.'),
                                ('Сто строк, а не сто профилей. ', 'Наверху — с кем совпало всё; клик открывает протокол.'),
                                ('Подсказка по деньгам. ', 'Сколько кандидатов добавится, если поднять верх вилки на 10 %.'),
                                ('Решение за человеком. ', 'Выбрать «совпало» и пригласить одним приглашением.')], size=12)

# ── 11. Подбор: три карточки ─────────────────────────────────────────
s = S[10]
title(s, 'ПОДБОР', color=PLUM)
cards = [('Категория', 'Специализация × грейд из теста, а не из резюме. Работодатель видит все грейды с числом людей.'),
         ('Порядок', 'Тест 60 %, стек 20 %, ФСП 10 %, свежесть 10 %. Без ФСП — ноль, не штраф. Неподтверждённые и дороже вилки больше чем на 10 % — ниже.'),
         ('Объяснение', 'К каждой позиции строки «почему здесь» с источником факта и разбор балла. Фильтры не теряют отбор.')]
for i, (h, t) in enumerate(cards):
    put(by_name(s, f'Текст {14 + i}'), f'0{i + 1}', size=14, color=PINK, bold=True)
    put(by_name(s, f'Текст {1 + 2 * i}'), h, size=14, color=PLUM, bold=True)
    put(by_name(s, f'Текст {2 + 2 * i}'), t, size=11, color=INK)

# ── 12. Валидация: шесть пунктов ─────────────────────────────────────
s = S[11]
title(s, 'ВАЛИДАЦИЯ', pill=at(s, 0.38, 0.35), w=3.0)
items = [('75,7 %', 'грейд совпал с истинным, ошибок больше чем на ступень нет'),
         ('0,86', 'корреляция оценок при повторном прохождении'),
         ('0,44', 'средняя разделяющая сила заданий; ниже 0,3 — 1 из 41'),
         ('9 % против 24 %', 'у кого вырос грейд после утечки 30 % ответов: банк против общего набора'),
         ('69,7 % против 78,8 %', 'точность без калибровки и с ней — довод ТЗ против генерации'),
         ('0,94 против 0,73', 'точность первой десятки подборки (P@10) против поиска по резюме; слабее запроса — 2,6 % против 26 %')]
for i, (n, t) in enumerate(items):
    put(by_name(s, f'Текст {14 + i}'), f'0{i + 1}', size=14, color=PLUM, bold=True)
    put(by_name(s, f'Текст {1 + 2 * i}'), n, size=18, color=PINK, bold=True)
    put(by_name(s, f'Текст {2 + 2 * i}'), t, size=11, color=INK)

# ── 13. Иерархия доверия ─────────────────────────────────────────────
s = S[12]
title(s, 'ЧЕМУ ВЕРИТЬ', pill=at(s, 0.38, 0.35), w=3.2)
put(by_name(s, 'Текст 3'), [('Онлайн-тест без надзора не отличает человека от человека с моделью. ', ''),
                             'Поэтому тест в «Разряде» — входной билет. Выше него в профиле стоят источники, которые подсказать нельзя.',
                             'Реестр ФСП — это и есть очная проверка с надзором, у которой федерация уже решила вопрос масштаба.'], size=14, color=INK)
rows = [('ФСП', 'очные соревнования, вес в ранжировании'),
        ('Встреча', 'итог интервью от работодателя — факт профиля'),
        ('Код', 'репозитории со ссылкой на коммит — после MVP'),
        ('Разбор', 'найти ошибку, проверить ответ модели — 5 шаблонов'),
        ('Тест', 'знание стека и основ — категория')]
for i, (a, b) in enumerate(rows):
    put(by_name(s, f'Текст {4 + i}'), [(a + '  ', b)], size=13, color=INK)

# ── 14. План развития ────────────────────────────────────────────────
s = S[13]
title(s, 'ДАЛЬШЕ', color=PLUM)
plan = ['Реестр ФСП вместо мока: вход через ФСП ID и достижения по номеру участника',
        'Банк до сотен шаблонов, параметры — по накопленным ответам и итогам встреч',
        'Задания с кодом в песочнице со скрытыми тестами',
        'ATS работодателей: карточка кандидата и статусы через вебхук',
        'Сверка компаний по ИНН и лимиты приглашений против фиктивных вакансий']
for i, t in enumerate(plan):
    put(by_name(s, f'Текст {7 + i}'), t, size=15, color=INK)

# ── 15. Финал ────────────────────────────────────────────────────────
s = S[14]
title(s, 'Спасибо', color=WHITE, size=54)
put(by_name(s, 'Текст 4'), 'Код, стенд и документация: github.com/a-amik/ltzt-fsp-2026')

# Подсказки макетов («Образец текста») в показе PowerPoint не видны, но попадают
# в PDF, собранный LibreOffice, — очищаем их в каждом использованном макете.
for layout in {id(sl.slide_layout): sl.slide_layout for sl in prs.slides}.values():
    for ph in layout.placeholders:
        if ph.placeholder_format.type not in (1, 3) and ph.has_text_frame and ph.text_frame.text.strip() in ('Образец текста', 'Фото команды'):
            for para in ph.text_frame.paragraphs:
                for r in para.runs:
                    r.text = ''

def number_slides(prs):
    """Номер в углу — порядковый: в шаблоне номера стоят текстом и после перестановки слайдов врут."""
    A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    for i, sl in enumerate(prs.slides, 1):
        for sh in sl.shapes:
            if sh.name.startswith('Номер слайда') and sh.has_text_frame:
                ts = sh.text_frame._txBody.iter(A + 't')
                first = next(ts, None)
                if first is not None:
                    first.text = str(i)
                    for t in ts:
                        t.text = ''


# Слайд с роликом вставляем последним: до этого все слайды берутся по номерам S[i] шаблона.
add_video_slide(prs, 8, S[9])
number_slides(prs)
prs.save(OUT)
print('ok', OUT, len(prs.slides))
