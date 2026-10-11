"""Банк шаблонов заданий.

Шаблон — не текст задачи, а её форма: условие с параметрами, генератор данных
и эталон. У шаблона две калиброванные величины модели IRT 2PL: трудность b на
шкале θ и различающая сила a. Экземпляр собирается из шаблона и зерна: цифры,
имена и сюжет у каждого кандидата свои, трудность одна. Где задача
вычислительная, от зерна меняется и верный ответ; где концептуальная, зерно
выбирает одну из равнозначных ситуаций. Порядок вариантов перемешивает
instance() от того же зерна, повтор вариантов — ошибка шаблона. Параметры
a и b начальные (экспертные), уточняются по сдачам (см. validation).
"""
from __future__ import annotations

import ipaddress
import math
import random
from collections import deque
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable

NB = "\u00a0"  # неразрывный пробел: «5 %», «300 мс»

STORIES = ["заказов", "платежей", "сообщений", "поездок", "матчей", "посылок"]
# Предметная область: родительный падеж множественного числа и ресурс API.
AREAS = [("заказов", "orders"), ("платежей", "payments"), ("сообщений", "messages"), ("поездок", "trips"),
         ("матчей", "matches"), ("посылок", "parcels"), ("бронирований", "bookings"), ("счетов", "invoices")]


def pick(r: random.Random, xs):
    return xs[int(r.random() * len(xs))]


def shuffled(r: random.Random, xs):
    xs = list(xs)
    r.shuffle(xs)
    return xs


def dec(x, nd: int = 1) -> str:
    """Число с десятичной запятой."""
    return f"{x:.{nd}f}".replace(".", ",")


def pct(x, nd: int = 0) -> str:
    return f"{dec(x, nd)}{NB}%"


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def times(x) -> str:
    """«в 2 раза», «в 5 раз», «в 1,2 раза»."""
    if isinstance(x, int) or float(x).is_integer():
        n = int(x)
        return f"в {n} {plural(n, 'раз', 'раза', 'раз')}"
    return f"в {dec(x, 2).rstrip('0').rstrip(',')} раза"


def options(ok: str, distractors, r: random.Random | None = None, n: int = 4, gen=None, sample: bool = False) -> list[str]:
    """Эталон и n − 1 разных дистракторов. Повтор и совпадение с эталоном отбрасываются,
    недостающее добирает gen(r). Порядок потом перемешивает instance()."""
    ds = list(distractors)
    if sample:
        r.shuffle(ds)
    out = [ok]
    for d in ds:
        if len(out) == n:
            break
        if d not in out:
            out.append(d)
    for _ in range(500):
        if len(out) >= n or gen is None:
            break
        d = gen(r)
        if d not in out:
            out.append(d)
    if len(out) < n:
        raise ValueError(f"не набралось {n} разных вариантов: {out}")
    return out


def num_opts(r: random.Random, ok: int, near=(), lo: int | None = 0, spread: int = 4, fmt=str) -> tuple[list[str], str]:
    """Числовой ответ: правдоподобные ошибки near, недостающее — соседние числа. Возвращает (варианты, эталон)."""
    fits = lambda x: lo is None or x >= lo
    steps = [d for d in range(-spread, spread + 1) if d]

    def gen(r):
        x = ok + r.choice(steps)
        return fmt(x if fits(x) else ok + abs(x - ok))
    return options(fmt(ok), [fmt(x) for x in near if fits(x)], r, gen=gen), fmt(ok)


@dataclass
class Template:
    id: str
    title: str
    skill: str
    specs: list[str]           # для каких специализаций годится
    fmt: str                   # выбор | вычисление | открытый | разбор
    a: float
    b: float
    make: Callable[[random.Random], dict]
    tags: list[str] = field(default_factory=list)   # стек, по которому подбираются задания под вакансию


def _mc(q, opts, ok, code=False):
    return {"q": q, "opts": opts, "ok": ok, "code": code}


T: list[Template] = []


def tpl(id, title, skill, specs, fmt, a, b, tags=()):
    def deco(fn):
        T.append(Template(id, title, skill, list(specs), fmt, a, b, fn, list(tags)))
        return fn
    return deco


ALL = ["backend", "frontend", "mobile", "data", "ml", "devops"]
DEV = ["backend", "frontend", "mobile"]

# ── Общие: алгоритмы и основы ──────────────────────────────────────────

CPLX = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)"]


@tpl("T01", "Сложность поиска", "Алгоритмы", ALL, "выбор", 1.1, -1.8)
def _(r):
    n, (what, _res) = pick(r, ["10 000", "1 000 000", "50 000", "200 000"]), pick(r, AREAS)
    q, ok = pick(r, [
        (f"Отсортированный массив из {n} идентификаторов {what}. Какова сложность поиска одного идентификатора бинарным поиском?", "O(log n)"),
        (f"Неотсортированный список из {n} идентификаторов {what}. Какова сложность поиска одного идентификатора перебором?", "O(n)"),
        (f"Массив из {n} записей {what}. Какова сложность чтения записи по известному индексу?", "O(1)"),
        (f"Сбалансированное дерево поиска хранит {n} идентификаторов {what}. Какова сложность поиска одного ключа?", "O(log n)"),
        (f"Нужно отсортировать {n} записей {what} сортировкой слиянием. Какова сложность сортировки?", "O(n log n)"),
    ])
    return _mc(q, options(ok, CPLX, r, sample=True), ok)


@tpl("T02", "Код ответа HTTP", "Сети и API", ["backend", "frontend", "mobile", "devops"], "выбор", 1.0, -1.3, ["REST"])
def _(r):
    _what, res = pick(r, AREAS)
    i = 100 + int(r.random() * 9900)
    q, ok, skip = pick(r, [
        (f"POST /api/{res} успешно создал запись. Какой код ответа ожидает клиент по REST-соглашению?", "201", ()),
        (f"GET /api/{res}/{i}: записи с таким идентификатором нет. Какой код ответа уместен?", "404", ()),
        (f"Запрос GET /api/{res} пришёл без токена авторизации. Какой код ответа уместен?", "401", ()),
        (f"Пользователь вошёл, но запрашивает GET /api/{res}/{i} — запись другого клиента, доступа к ней у него нет. Какой код ответа уместен?", "403", ("404",)),
        (f"DELETE /api/{res}/{i} удалил запись, тело ответа пустое. Какой код ответа уместен?", "204", ("200",)),
        (f"Клиент превысил лимит запросов к /api/{res}. Какой код ответа уместен?", "429", ()),
    ])
    pool = [c for c in ["200", "201", "204", "301", "400", "401", "403", "404", "409", "429", "500"] if c not in skip]
    return _mc(q, options(ok, pool, r, sample=True), ok)


@tpl("T03", "Подсчёт по условию", "SQL", ["backend", "data", "ml"], "вычисление", 1.3, -0.8, ["SQL", "PostgreSQL", "ClickHouse"])
def _(r):
    _what, table = pick(r, AREAS)
    col = pick(r, ["amount", "price", "duration", "weight", "score"])
    vals = [10 + int(r.random() * 90) for _ in range(7)]
    k = pick(r, vals) if r.random() < 0.5 else 30 + int(r.random() * 40)
    op = pick(r, [">", ">="])
    ok = sum(1 for v in vals if (v > k if op == ">" else v >= k))
    opts, ok_s = num_opts(r, ok, [ok + 1, ok - 1, ok + 2])
    return _mc(f"В таблице {table} колонка {col} содержит значения: {', '.join(map(str, vals))}.\nЧто вернёт SELECT COUNT(*) FROM {table} WHERE {col} {op} {k}?", opts, ok_s)


@tpl("T04", "Вывод программы", "Язык и типы", ["backend", "data", "ml"], "вычисление", 1.4, -0.3, ["Python"])
def _(r):
    a = 2 + int(r.random() * 6)
    b = a + 4 + int(r.random() * 7)
    kind = pick(r, ["sum", "sum_step", "len_step"])
    if kind == "sum":
        expr, ok = f"sum(range({a}, {b}))", sum(range(a, b))
        near = [ok + b, ok - a, sum(range(a, b + 1))]
    elif kind == "sum_step":
        s = pick(r, [2, 3])
        expr, ok = f"sum(range({a}, {b}, {s}))", sum(range(a, b, s))
        near = [sum(range(a, b + 1, s)), sum(range(a, b)), ok - a]
    else:
        s = pick(r, [2, 3, 4])
        expr, ok = f"len(range({a}, {b}, {s}))", len(range(a, b, s))
        near = [len(range(a, b + 1, s)), (b - a) // s, b - a]
    opts, ok_s = num_opts(r, ok, near, lo=0)
    return _mc(f"Что напечатает код?\n\nprint({expr})", opts, ok_s, code=True)


@tpl("T05", "Вложенные циклы", "Алгоритмы", ALL, "выбор", 1.2, 0.1)
def _(r):
    i, j = pick(r, [("i", "j"), ("a", "b"), ("x", "y"), ("row", "col")])
    w = pick(r, ["work", "process", "check", "send"])
    c = 3 + int(r.random() * 8)
    code, ok = pick(r, [
        (f"for {i} in range(n):\n    for {j} in range({i}, n):\n        {w}()", "O(n²)"),
        (f"for {i} in range(n):\n    for {j} in range({i}):\n        {w}()", "O(n²)"),
        (f"for {i} in range(n):\n    for {j} in range({c}):\n        {w}()", "O(n)"),
        (f"for {i} in range(n):\n    {j} = 1\n    while {j} < n:\n        {w}()\n        {j} *= 2", "O(n log n)"),
        (f"for {i} in range(n):\n    for {j} in range(n):\n        for k in range({j}):\n            {w}()", "O(n³)"),
        (f"{i} = n\nwhile {i} > 1:\n    {w}()\n    {i} //= 2", "O(log n)"),
    ])
    pool = ["O(log n)", "O(n)", "O(n log n)", "O(n²)", "O(n³)", "O(2ⁿ)"]
    return _mc(f"{code}\n\nКакова асимптотика числа вызовов {w}()?", options(ok, pool, r, sample=True), ok, code=True)


@tpl("T12", "Изменяемый аргумент по умолчанию", "Язык и типы", ["backend", "data", "ml"], "выбор", 0.9, 0.3, ["Python"])
def _(r):
    fn = pick(r, ["add", "collect", "remember", "push"])
    p = pick(r, ["bucket", "acc", "seen", "items"])
    v1, v2, v3 = r.sample(range(1, 10), 3)
    kind = pick(r, ["two", "three", "explicit"])
    if kind == "two":
        calls, res, alls = [f"{fn}({v1})", f"{fn}({v2})"], [v1, v2], [v1, v2]
    elif kind == "three":
        calls, res, alls = [f"{fn}({v1})", f"{fn}({v2})", f"{fn}({v3})"], [v1, v2, v3], [v1, v2, v3]
    else:
        calls, res, alls = [f"{fn}({v1})", f"{fn}({v2}, [])", f"{fn}({v3})"], [v1, v3], [v1, v2, v3]
    last = int(calls[-1].split("(")[1].split(")")[0].split(",")[0])
    q = f"def {fn}(item, {p}=[]):\n    {p}.append(item)\n    return {p}\n\n" + "\n".join(calls) + "\n\nЧто вернёт последний вызов?"
    ok = str(res)
    return _mc(q, options(ok, [str([last]), str(alls), "None", str([v1])], r, gen=lambda r: str(r.sample([v1, v2, v3], 2))), ok, code=True)


@tpl("T13", "Структура данных под задачу", "Алгоритмы", ALL, "выбор", 1.0, -1.0)
def _(r):
    what, _res = pick(r, AREAS)
    q, ok, ds = pick(r, [
        (f"Нужно за O(1) в среднем проверять, встречался ли идентификатор {what} раньше. Какая структура данных подходит?",
         "Хеш-множество", ["Отсортированный массив", "Связный список", "Куча", "Стек"]),
        (f"Из очереди {what} каждый раз нужно забирать запись с самым ранним сроком, а новые добавлять за O(log n). Какая структура данных подходит?",
         "Куча", ["Стек", "Хеш-множество", "Связный список", "Очередь FIFO"]),
        ("Редактор должен отменять последние действия пользователя в обратном порядке. Какая структура данных подходит?",
         "Стек", ["Очередь FIFO", "Хеш-множество", "Куча"]),
        (f"Обработчик {what} должен брать записи строго в порядке поступления. Какая структура данных подходит?",
         "Очередь FIFO", ["Стек", "Куча", "Хеш-множество"]),
        (f"Нужно для каждого клиента за O(1) в среднем находить число его {what}. Какая структура данных подходит?",
         "Хеш-таблица (словарь)", ["Стек", "Очередь FIFO", "Связный список", "Куча"]),
    ])
    return _mc(q, options(ok, ds, r, sample=True), ok)


def _dyck(r: random.Random, pairs: int) -> str:
    s, left, bal = [], pairs, 0
    while left or bal:
        if left and (bal == 0 or r.random() < 0.5):
            s.append("("); left -= 1; bal += 1
        else:
            s.append(")"); bal -= 1
    return "".join(s)


def _balanced(s: str) -> bool:
    bal = 0
    for ch in s:
        bal += 1 if ch == "(" else -1
        if bal < 0:
            return False
    return bal == 0


@tpl("T14", "Стек и скобки", "Алгоритмы", ALL, "вычисление", 1.2, -0.6)
def _(r):
    s = _dyck(r, pick(r, [3, 4, 5]))
    if r.random() < 0.5:
        i = int(r.random() * (len(s) - 1))
        s = s[:i] + s[i + 1] + s[i] + s[i + 2:]          # перестановка соседних знаков
        if r.random() < 0.3:
            s = s[:-1]                                    # или ещё и обрыв
    ok = "Да" if _balanced(s) else "Нет"
    return _mc(f"Правильна ли скобочная последовательность {s}?", options(ok, ["Да", "Нет"], n=2), ok)

# ── Бэкенд ─────────────────────────────────────────────────────────────


@tpl("T06", "Составной индекс", "Базы данных", ["backend", "data"], "выбор", 1.5, 0.5, ["PostgreSQL", "SQL"])
def _(r):
    table, x, y = pick(r, [("orders", "user_id", "created_at"), ("products", "shop_id", "price"), ("places", "city", "rating"),
                           ("events", "account_id", "updated_at"), ("trips", "driver_id", "started_at"), ("messages", "chat_id", "sent_at"),
                           ("tickets", "queue_id", "priority")])
    order = pick(r, ["DESC", "ASC"])
    lim = pick(r, [10, 20, 50])
    ok = f"({x}, {y})"
    return _mc(f"Частый запрос: SELECT * FROM {table} WHERE {x} = $1 ORDER BY {y} {order} LIMIT {lim}. Какой индекс лучше?",
               options(ok, [f"({y}, {x})", f"({x}) и отдельно ({y})", f"Хеш-индекс по {x}"]), ok)


@tpl("T07", "Гонка за счётчик", "Конкурентность", ["backend", "mobile"], "вычисление", 1.3, 0.9)
def _(r):
    t, m = pick(r, [2, 3, 4]), pick(r, [100, 1000, 500])
    v = pick(r, ["counter", "hits", "total", "seen"])
    s0, k = pick(r, [0, 10, 100]), pick(r, [1, 2, 5])
    ok = s0 + 2 * k   # классика: один поток «съедает» почти всё чужое, минимум — два шага
    opts, ok_s = num_opts(r, ok, [s0 + k, s0 + k * m, s0 + t * m * k, s0], lo=s0)
    return _mc(f"{t} потока без синхронизации по {m} раз выполняют {v} += {k} (чтение, сложение, запись). Сначала {v} = {s0}. "
               f"Каково минимально возможное итоговое значение {v}?", opts, ok_s)


@tpl("T08", "Уровень изоляции", "Базы данных", ["backend", "data"], "выбор", 1.2, 1.3, ["PostgreSQL", "SQL"])
def _(r):
    _what, table = pick(r, AREAS)
    col = pick(r, ["amount", "status", "price", "balance"])
    x, i = pick(r, [100, 500, 1000]), 1 + int(r.random() * 999)
    q, ok = pick(r, [
        (f"В одной транзакции два одинаковых SELECT ... FROM {table} WHERE amount > {x} вернули разное число строк: между ними другая транзакция вставила запись и зафиксировалась.", "SERIALIZABLE"),
        (f"В одной транзакции дважды прочитали строку {table} с id = {i} и получили разные значения {col}: между чтениями другая транзакция изменила строку и зафиксировалась.", "REPEATABLE READ"),
        (f"Транзакция прочитала значение {col} в {table}, которое другая транзакция записала, но потом откатила.", "READ COMMITTED"),
    ])
    return _mc(q + " Какой минимальный уровень изоляции по стандарту SQL это исключает?",
               options(ok, ["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"]), ok)


def _frac(f: Fraction) -> str:
    return "Все" if f == 1 else f"Около {f.numerator}/{f.denominator}"


@tpl("T09", "Консистентное хеширование", "Проектирование", ["backend", "devops"], "вычисление", 1.4, 1.8, ["Redis"])
def _(r):
    n = pick(r, [3, 4, 5, 7, 9])
    kind = pick(r, ["add", "remove", "add_k"])
    if kind == "add":
        k, ok = 1, Fraction(1, n + 1)
        q = f"Кэш распределён по {n} узлам консистентным хешированием. Добавили ещё один узел. Какая доля ключей переедет?"
        near = [Fraction(1, n), Fraction(n, n + 1), Fraction(1)]
    elif kind == "remove":
        ok = Fraction(1, n)
        q = f"Кэш распределён по {n} узлам консистентным хешированием. Один узел вывели из кольца. Какая доля ключей переедет?"
        near = [Fraction(1, n - 1), Fraction(n - 1, n), Fraction(1)]
    else:
        k = pick(r, [2, 3])
        ok = Fraction(k, n + k)
        q = f"Кэш распределён по {n} узлам консистентным хешированием. Добавили ещё {k} узла. Какая доля ключей переедет?"
        near = [Fraction(1, n + k), Fraction(k, n), Fraction(n, n + k), Fraction(1)]
    gen = lambda r: _frac(Fraction(1, pick(r, [2, 3, 4, 6, 8, 10, 12])))
    return _mc(q, options(_frac(ok), [_frac(f) for f in near if f <= 1], r, gen=gen), _frac(ok))


@tpl("T11", "Очередь и повторы", "Сети и API", ["backend", "data"], "выбор", 1.2, 1.0, ["Kafka"])
def _(r):
    topic = pick(r, ["orders", "payments", "clicks", "events"])
    kind = pick(r, ["redo", "lost", "idle", "order"])
    if kind == "redo":
        q = f"Потребитель топика {topic} в Kafka упал после обработки сообщения, но до коммита смещения. Что произойдёт после перезапуска?"
        ok, ds = "Сообщение обработается повторно", ["Сообщение потеряется", "Kafka откатит обработку", "Группа потребителей остановится"]
    elif kind == "lost":
        q = f"Потребитель топика {topic} коммитит смещение сразу при получении сообщения, до обработки, и упал посреди обработки. Что произойдёт после перезапуска?"
        ok, ds = "Сообщение будет пропущено", ["Сообщение обработается повторно", "Kafka откатит коммит", "Группа потребителей остановится"]
    elif kind == "idle":
        p = pick(r, [3, 4, 6])
        c = p + 1 + int(r.random() * 3)
        d = c - p
        q = f"В топике {topic} {p} {plural(p, 'партиция', 'партиции', 'партиций')}. В одну группу потребителей добавили {c} {plural(c, 'экземпляр', 'экземпляра', 'экземпляров')}. Что будет с нагрузкой?"
        ok = f"{d} {plural(d, 'потребитель будет', 'потребителя будут', 'потребителей будут')} простаивать"
        ds = [f"Все {c} получат сообщения поровну", "Kafka сама добавит партиции", f"{c} {plural(c, 'потребитель будет', 'потребителя будут', 'потребителей будут')} простаивать"]
    else:
        key = pick(r, ["user_id", "order_id", "account_id"])
        q = f"Сообщения в топик {topic} пишутся с ключом {key}. Что гарантирует Kafka о порядке сообщений одного {key}?"
        ok, ds = "Они попадут в одну партицию, порядок внутри неё сохранится", ["Порядок не гарантируется вообще", "Порядок сохранится во всём топике", "Порядок сохранится, только если партиция одна"]
    return _mc(q, options(ok, ds), ok)


@tpl("T15", "Идемпотентность", "Сети и API", ["backend", "mobile"], "выбор", 1.1, 0.0, ["REST"])
def _(r):
    _what, res = pick(r, AREAS)
    m = pick(r, ["PUT", "DELETE", "GET", "HEAD"])
    return _mc(f"Клиент повторяет запросы к /api/{res} после таймаута. Какой из методов HTTP по спецификации идемпотентен?",
               options(m, ["POST", "PATCH", "Ни один"]), m)


@tpl("T16", "N+1 запрос", "Базы данных", ["backend"], "вычисление", 1.3, -0.1, ["PostgreSQL", "SQL"])
def _(r):
    n, (what, _res) = pick(r, [20, 30, 50, 100, 200]), pick(r, AREAS)
    if r.random() < 0.5:
        ok = n + 1
        q = f"Список из {n} {what} выводится циклом, и для каждого элемента отдельно запрашивается автор. Сколько запросов к базе уйдёт без оптимизации, считая запрос списка?"
        near = [n, 2, 2 * n]
    else:
        ok = 2 * n + 1
        q = f"Список из {n} {what} выводится циклом, и для каждого элемента отдельно запрашиваются автор и категория. Сколько запросов к базе уйдёт без оптимизации, считая запрос списка?"
        near = [n + 1, 2 * n, 3, n + 2]
    opts, ok_s = num_opts(r, ok, near, lo=1)
    return _mc(q, opts, ok_s)


@tpl("T10", "Ограничение частоты запросов", "Проектирование", ["backend", "devops"], "открытый", 1.1, 2.2, ["Redis"])
def _(r):
    rps, (what, _res) = pick(r, ["5 000", "20 000", "80 000"]), pick(r, AREAS)
    lim = pick(r, [50, 100, 200, 500])
    return {"q": f"Сервис {what} принимает {rps} запросов в секунду от партнёров. Нужно ограничить каждого партнёра {lim} запросами в секунду на нескольких экземплярах API. Опишите подход в трёх-пяти предложениях.",
            "open": True, "ai": True, "rubric": ["общее хранилище счётчиков (Redis и т. п.)", "алгоритм: скользящее окно или ведро токенов", "что отвечаем при превышении (429, Retry-After)", "что будет при отказе хранилища"],
            "keys": [["redis", "хранилищ", "общ", "централ"], ["окн", "ведр", "токен", "bucket", "window"], ["429", "retry", "отказ", "ошибк"], ["недоступ", "упад", "fallback", "деград"]]}

# ── Фронтенд ───────────────────────────────────────────────────────────

# (выражение a, выражение b, a == b, a === b)
JS_EQ = [("0", "'0'", True, False), ("1", "'1'", True, False), ("null", "undefined", True, False), ("''", "0", True, False),
         ("null", "0", False, False), ("NaN", "NaN", False, False), ("0", "false", True, False), ("undefined", "0", False, False),
         ("'abc'", "'abc'", True, True), ("2", "2", True, True)]


@tpl("F01", "Равенство в JavaScript", "Язык и типы", ["frontend"], "вычисление", 1.0, -1.2, ["TypeScript"])
def _(r):
    a, b, loose, strict = pick(r, JS_EQ)
    form = pick(r, ["loose", "strict", "and", "or"])
    expr, val = {"loose": (f"{a} == {b}", loose), "strict": (f"{a} === {b}", strict),
                 "and": (f"{a} == {b} && {a} === {b}", loose and strict), "or": (f"{a} == {b} || {a} === {b}", loose or strict)}[form]
    ok = "true" if val else "false"
    return _mc(f"Что вернёт выражение {expr} в JavaScript?", options(ok, ["true", "false", "TypeError", "undefined"]), ok, code=True)


@tpl("F02", "Ключи в списке React", "Рендеринг", ["frontend"], "выбор", 1.2, -0.4, ["React"])
def _(r):
    items = pick(r, ["товаров корзины", "задач", "участников", "адресов доставки"])
    act = pick(r, ["удаления первого элемента", "вставки элемента в начало", "сортировки списка"])
    key, ok = pick(r, [("index", "Состояние полей сдвинется: React сопоставит строки по позиции"),
                       ("index", "Состояние полей сдвинется: React сопоставит строки по позиции"),
                       ("Math.random()", "Строки пересоздадутся на каждом рендере, ввод в полях сбросится"),
                       ("item.id", "Состояние останется у своих строк: React сопоставит их по id")])
    pool = ["Состояние полей сдвинется: React сопоставит строки по позиции", "Строки пересоздадутся на каждом рендере, ввод в полях сбросится",
            "Состояние останется у своих строк: React сопоставит их по id", "React выбросит исключение"]
    return _mc(f"Список {items} с полем ввода в каждой строке рендерится через map с key={{{key}}}. Что будет после {act}?",
               options(ok, pool), ok)


def _js_loop(prog):
    """Событийный цикл для простого кода: sync — сразу, micro — после синхронного кода, macro — потом."""
    out = [x for kind, x in prog if kind == "sync"]
    out += [x for kind, x in prog if kind == "micro"]
    out += [x for kind, x in prog if kind == "macro"]
    return out


@tpl("F03", "Событийный цикл", "Язык и типы", ["frontend", "backend"], "вычисление", 1.4, 0.4, ["TypeScript"])
def _(r):
    kinds = ["sync", "macro", "micro"] + [pick(r, ["sync", "micro", "macro"]) for _ in range(int(r.random() * 2) + 1)]
    while True:
        r.shuffle(kinds)
        labels = r.sample(range(1, len(kinds) + 1), len(kinds))
        prog = list(zip(kinds, labels))
        out = _js_loop(prog)
        if out != labels:
            break
    lines = []
    for kind, x in prog:
        if kind == "sync":
            lines.append(f"console.log({x});")
        elif kind == "macro":
            lines.append(f"setTimeout(() => console.log({x}));")
        else:
            lines.append(pick(r, [f"Promise.resolve().then(() => console.log({x}));", f"queueMicrotask(() => console.log({x}));"]))
    j = lambda xs: " ".join(map(str, xs))
    ok = j(out)
    near = [j(labels),
            j([x for k, x in prog if k == "sync"] + [x for k, x in prog if k == "macro"] + [x for k, x in prog if k == "micro"]),
            j([x for k, x in prog if k == "sync"] + [x for k, x in prog if k != "sync"])]
    return _mc("\n".join(lines) + "\n\nПорядок вывода?", options(ok, near, r, gen=lambda r: j(shuffled(r, labels))), ok, code=True)


@tpl("F04", "Эффект и зависимости", "Рендеринг", ["frontend"], "выбор", 1.3, 0.8, ["React"])
def _(r):
    p = pick(r, ["id", "userId", "query", "page"])
    _what, res = pick(r, AREAS)
    A = "Запрос не повторится: массив зависимостей пуст"
    B = f"Запрос уйдёт заново при каждой смене {p}"
    C = "Запросы пойдут по кругу: эффект срабатывает после каждого рендера"
    load = f"fetch(`/api/{res}?{p}=${{{p}}}`).then(r => r.json()).then(setData);"
    code, ok = pick(r, [
        (f"useEffect(() => {{ {load} }}, []);", A),
        (f"useEffect(() => {{ {load} }}, [{p}]);", B),
        (f"useEffect(() => {{ {load} }});", C),
        (f"const params = {{ {p} }};\nuseEffect(() => {{ {load} }}, [params]);", C),
    ])
    return _mc(f"{code}\n\nПроп {p} приходит от родителя и меняется. Что происходит?",
               options(ok, [A, B, C, "React предупредит и перезапустит эффект", "Компонент размонтируется"], r, sample=True), ok, code=True)


def _spec_css(sel: str) -> tuple[int, int, int]:
    ids = cls = els = 0
    for tok in sel.split():
        ids += tok.count("#")
        cls += tok.count(".")
        if tok[0].isalpha():
            els += 1
    return ids, cls, els


@tpl("F05", "Специфичность CSS", "Рендеринг", ["frontend"], "вычисление", 1.1, -0.2, ["CSS"])
def _(r):
    anc = ["#main", "#app", "#page", ".card", ".list", ".panel", ".wide", "div", "section", "article", "ul"]
    last = [".title", "h2.title", "h2", ".title.active", "h2.title.active"]
    while True:
        sels = []
        for _ in range(3):
            toks = r.sample(anc, int(r.random() * 3)) + [pick(r, last)]
            sels.append(" ".join(toks))
        specs = [_spec_css(s) for s in sels]
        if len(set(specs)) == 3 and len(set(sels)) == 3:
            break
    ok = sels[specs.index(max(specs))]
    return _mc(f"Все три селектора выбирают один и тот же заголовок h2.title.active и задают ему разный цвет. Какой победит?\n\n" + "\n".join(sels),
               options(ok, [s for s in sels if s != ok] + ["Последний в файле"]), ok, code=True)


@tpl("F06", "Кэширование запроса", "Сети и API", ["frontend", "mobile"], "выбор", 1.2, 1.1, ["REST"])
def _(r):
    _what, res = pick(r, AREAS)
    kind = pick(r, ["etag", "lm", "nocache", "nostore", "maxage"])
    if kind == "etag":
        q = f"Ответ GET /api/{res} пришёл с заголовком ETag. Как проверить свежесть без повторной загрузки тела?"
        ok, ds = "If-None-Match с ETag, ждём 304", ["Повторить GET без заголовков", "Отправить HEAD и сравнить Content-Length", "If-Modified-Since с ETag, ждём 200"]
    elif kind == "lm":
        q = f"Ответ GET /api/{res} пришёл с заголовком Last-Modified, ETag нет. Как проверить свежесть без повторной загрузки тела?"
        ok, ds = "If-Modified-Since с этой датой, ждём 304", ["If-None-Match с этой датой, ждём 304", "Повторить GET без заголовков", "Отправить HEAD и сравнить Content-Length"]
    elif kind == "nocache":
        q = f"Ответ GET /api/{res} пришёл с Cache-Control: no-cache. Что это значит для браузера?"
        ok, ds = "Хранить можно, но перед использованием проверять у сервера", ["Не сохранять ответ вовсе", "Брать из кэша без проверки", "Кэшировать только на прокси"]
    elif kind == "nostore":
        q = f"Ответ GET /api/{res} пришёл с Cache-Control: no-store. Что это значит для браузера?"
        ok, ds = "Не сохранять ответ ни в каком кэше", ["Хранить, но каждый раз проверять у сервера", "Хранить до закрытия вкладки", "Кэшировать только на прокси"]
    else:
        n = pick(r, [60, 300, 600, 3600])
        t = pick(r, [n // 2, n - 10, n + 30, 2 * n])
        q = f"Ответ GET /api/{res} пришёл с Cache-Control: max-age={n}, без no-cache. Через {t} с тот же запрос понадобился снова. Что сделает браузер?"
        fresh, stale = "Возьмёт ответ из кэша без запроса к серверу", "Срок истёк: проверит у сервера или загрузит заново"
        ok = fresh if t < n else stale
        ds = [stale if ok == fresh else fresh, "Всегда загрузит ответ заново", "Возьмёт из кэша, только если сервер ответит 304"]
    return _mc(q, options(ok, ds), ok)

# ── Мобильная разработка ──────────────────────────────────────────────


@tpl("M01", "Главный поток", "Платформа", ["mobile"], "выбор", 1.0, -0.9, ["Kotlin", "Swift"])
def _(r):
    what, _res = pick(r, AREAS)
    s = pick(r, [6, 8, 10, 12])
    A = "Интерфейс замрёт до ответа"
    B = "Приложение упадёт с NetworkOnMainThreadException"
    C = "Система покажет диалог «Приложение не отвечает» (ANR)"
    D = "Приложение упадёт: менять View можно только из главного потока"
    q, ok = pick(r, [
        (f"Приложение на iOS загружает список {what} синхронно, Data(contentsOf:), прямо в главном потоке; сервер отвечает за {pick(r, [2, 3, 4])} с. Что увидит пользователь?", A),
        (f"Приложение на Android загружает список {what} через HttpURLConnection прямо в главном потоке. Что произойдёт?", B),
        (f"Приложение на Android по нажатию {s} секунд считает отчёт по {what} в главном потоке, а пользователь продолжает нажимать на экран. Что произойдёт?", C),
        (f"Приложение на Android загрузило список {what} в фоновом потоке и прямо оттуда меняет TextView. Что произойдёт?", D),
    ])
    return _mc(q, options(ok, [A, B, C, D, "Ничего: запрос асинхронный", "Запрос не отправится"], r, sample=True), ok)


@tpl("M02", "Жизненный цикл", "Платформа", ["mobile"], "выбор", 1.2, 0.3, ["Kotlin"])
def _(r):
    scr = pick(r, ["экран корзины", "экран чата", "экран карты", "экран профиля"])
    A = "Будет пересоздана: onDestroy, затем onCreate"
    B = "Остановится: onPause, затем onStop"
    C = "Получит только onPause: она остаётся частично видимой"
    D = "Будет создана заново, сохранённое состояние придёт в savedInstanceState"
    G = "Не пересоздастся: вызовется onConfigurationChanged"
    q, ok = pick(r, [
        (f"Пользователь повернул экран на Android, открыт {scr}. Что произойдёт с Activity по умолчанию?", A),
        (f"Пользователь нажал «Домой», пока открыт {scr}. Что произойдёт с Activity?", B),
        (f"Поверх Activity, где открыт {scr}, появилась Activity в виде диалога, не на весь экран. Что произойдёт с нижней Activity?", C),
        (f"Приложение было в фоне, система завершила процесс из-за нехватки памяти. Пользователь вернулся через список недавних, там был {scr}. Что произойдёт с Activity?", D),
        (f"В манифесте у Activity указано android:configChanges=\"orientation|screenSize\". Пользователь повернул экран, открыт {scr}. Что произойдёт?", G),
    ])
    return _mc(q, options(ok, [A, B, C, D, G, "Продолжит работать без изменений", "Будет уничтожена без восстановления"], r, sample=True), ok)


@tpl("M03", "Офлайн-синхронизация", "Проектирование", ["mobile"], "открытый", 1.1, 1.6)
def _(r):
    what = pick(r, ["заказы", "заметки", "сообщения", "черновики отчётов"])
    return {"q": f"Приложение создаёт {what} без сети, а потом синхронизирует их с сервером. Как избежать дублей и конфликтов? Опишите подход в трёх-пяти предложениях.",
            "open": True, "ai": True, "rubric": ["локальная очередь операций", "идемпотентные ключи у операций", "правило разрешения конфликтов", "что показываем пользователю"],
            "keys": [["очеред", "локальн", "хранилищ"], ["идемпотент", "uuid", "ключ"], ["конфликт", "версия", "last write", "merge"], ["пользовател", "статус", "показ"]]}

# ── Данные ─────────────────────────────────────────────────────────────


@tpl("D01", "GROUP BY и HAVING", "SQL", ["data", "backend"], "вычисление", 1.2, -0.5, ["SQL"])
def _(r):
    cats = r.sample(["A", "B", "C", "D", "E"], pick(r, [3, 4]))
    rows = [(c, 1 + int(r.random() * 6)) for c in cats] + [(pick(r, cats), 1 + int(r.random() * 6)) for _ in range(pick(r, [3, 4]))]
    r.shuffle(rows)
    agg = pick(r, ["SUM(v)", "COUNT(*)"])
    vals = {}
    for c, v in rows:
        vals[c] = vals.get(c, 0) + (v if agg == "SUM(v)" else 1)
    k = pick(r, sorted(set(vals.values()))) if r.random() < 0.6 else pick(r, [3, 4, 5, 6])
    ok = sum(1 for v in vals.values() if v > k)
    opts, ok_s = num_opts(r, ok, [ok + 1, ok - 1, len(cats), sum(1 for v in vals.values() if v >= k)])
    rs = ", ".join(f"({c}, {v})" for c, v in rows)
    return _mc(f"Строки таблицы t (cat, v): {rs}.\nЧто вернёт SELECT COUNT(*) FROM (SELECT cat FROM t GROUP BY cat HAVING {agg} > {k}) s?", opts, ok_s)


@tpl("D02", "Устойчивые метрики", "Статистика", ["data", "ml"], "выбор", 1.0, -0.7)
def _(r):
    subj = pick(r, ["зарплат", "сумм чека", "времени доставки", "длительности сессии"])
    kind = pick(r, ["center", "median", "spread", "mode"])
    if kind == "center":
        q = f"Распределение {subj} с длинным правым хвостом. Какая метрика центра устойчивее к выбросам?"
        ok, ds = "Медиана", ["Среднее", "Мода", "Размах"]
    elif kind == "spread":
        q = f"Распределение {subj} с редкими огромными выбросами. Какая мера разброса к ним устойчивее?"
        ok, ds = "Межквартильный размах", ["Стандартное отклонение", "Размах (максимум − минимум)", "Дисперсия"]
    elif kind == "mode":
        q = "Нужно назвать самый частый способ оплаты среди заказов (карта, СБП, наличные). Какая метрика центра подходит?"
        ok, ds = "Мода", ["Среднее", "Медиана", "Межквартильный размах"]
    else:
        base = sorted(r.sample(range(10, 40), 6))
        out = pick(r, [180, 240, 300, 420])
        xs = shuffled(r, base + [out])
        med = sorted(xs)[3]
        mean = round(sum(xs) / 7)
        q = f"Время доставки семи заказов, мин: {', '.join(map(str, xs))}. Чему равна медиана?"
        ok = str(med)
        ds = [str(mean), str(sorted(xs)[2]), str(sorted(xs)[4]), str(out)]
    return _mc(q, options(ok, ds), ok)


@tpl("D03", "Идемпотентный пайплайн", "Пайплайны", ["data"], "выбор", 1.3, 0.9, ["Airflow"])
def _(r):
    table = pick(r, ["sales_daily", "events_daily", "payments_daily", "visits_daily"])
    kind = pick(r, ["partition", "logical", "merge"])
    if kind == "partition":
        q = f"Задача Airflow упала посреди загрузки дня в {table} и перезапустилась. Какой приём делает повтор безопасным?"
        ok, ds = "Удалять и перезаписывать партицию дня целиком", ["Дописывать строки в конец", "Отключить повторы", "Загружать только новые часы"]
    elif kind == "logical":
        d = pick(r, [2, 3, 5])
        q = f"Задача Airflow грузит в {table} данные «за вчера», вычисляя дату через datetime.now(). Упавший запуск перезапустили спустя {d} {plural(d, 'день', 'дня', 'дней')}. Что пошло не так и как исправить?"
        ok, ds = ("Загружен не тот день: брать дату из интервала запуска (data_interval_start), а не из now()",
                  ["Ничего: вчерашний день загрузится как обычно", "Нужно увеличить retries", "Нужно запускать задачу чаще"])
    else:
        q = f"Источник при сбоях связи присылает часть событий повторно, у каждого события есть уникальный event_id. Как грузить их в {table} без дублей?"
        ok, ds = "MERGE (upsert) по event_id вместо простой вставки", ["Простая вставка, дубли убрать в отчёте", "Отключить повторы у источника", "Грузить раз в сутки"]
    return _mc(q, options(ok, ds), ok)


@tpl("D04", "Соединение таблиц", "SQL", ["data", "backend"], "вычисление", 1.3, 0.2, ["SQL"])
def _(r):
    n = pick(r, [3, 4, 5, 6])
    cnt = [pick(r, [0, 0, 1, 2, 3]) for _ in range(n)]
    if all(c == 0 for c in cnt):
        cnt[0] = 2
    join = pick(r, ["LEFT JOIN", "JOIN"])
    ok = sum(max(c, 1) for c in cnt) if join == "LEFT JOIN" else sum(cnt)
    other = sum(cnt) if join == "LEFT JOIN" else sum(max(c, 1) for c in cnt)
    opts, ok_s = num_opts(r, ok, [other, n, sum(cnt) + n, ok + 1])
    desc = "; ".join(f"id {i + 1} — {c}" for i, c in enumerate(cnt))
    return _mc(f"В таблице a {n} {plural(n, 'строка', 'строки', 'строк')} с id 1…{n}. В таблице b строк на каждый a_id: {desc}.\nСколько строк вернёт SELECT * FROM a {join} b ON b.a_id = a.id?", opts, ok_s)


MARTS = [
    ("заказов", ["Сумма заказа", "Число товаров", "Скидка в рублях"], ["Город покупателя", "Категория товара", "Канал продаж", "Дата заказа"]),
    ("поездок", ["Расстояние, км", "Стоимость поездки", "Время в пути, мин"], ["Тариф", "Город", "Класс автомобиля", "Дата поездки"]),
    ("звонков", ["Длительность, с", "Стоимость звонка", "Число переадресаций"], ["Оператор", "Регион абонента", "Тариф", "Час звонка"]),
    ("платежей", ["Сумма платежа", "Комиссия", "Возвращённая сумма"], ["Банк-эмитент", "Страна карты", "Способ оплаты", "Дата платежа"]),
    ("доставок", ["Вес посылки, кг", "Стоимость доставки", "Число мест"], ["Пункт выдачи", "Служба доставки", "Регион", "Неделя отправки"]),
]


@tpl("D05", "Факт и измерение", "Моделирование данных", ["data"], "выбор", 1.1, -0.6, ["SQL", "ClickHouse"])
def _(r):
    what, measures, dims = pick(r, MARTS)
    if r.random() < 0.5:
        ok = pick(r, measures)
        q = f"Строим витрину {what} по схеме «звезда». Какое поле — мера таблицы фактов, которую складывают в отчётах?"
        ds = r.sample(dims, 3)
    else:
        ok = pick(r, dims)
        q = f"Строим витрину {what} по схеме «звезда». Какое поле — атрибут измерения, а не мера таблицы фактов?"
        ds = list(measures)
    return _mc(q, options(ok, ds), ok)


SCD_ENT = [("клиентов", "город клиента на момент заказа", "клиенты иногда переезжают", "город"),
           ("товаров", "категорию товара на момент продажи", "товары иногда переносят в другие категории", "категория"),
           ("сотрудников", "отдел сотрудника на момент сделки", "сотрудники иногда переходят между отделами", "отдел"),
           ("магазинов", "регион магазина на момент продажи", "магазины иногда переподчиняют другим регионам", "регион")]


@tpl("D06", "Медленно меняющееся измерение", "Моделирование данных", ["data"], "выбор", 1.3, 0.9, ["SQL"])
def _(r):
    gen, ctx, moves, fld = pick(r, SCD_ENT)
    S2, S1, S3 = "SCD2: новая строка-версия с датами действия", "SCD1: перезаписывать значение", "SCD3: столбец с прежним значением"
    pool = [S2, S1, S3, "Новая таблица измерения на каждый год"]
    kind = pick(r, ["s2", "s1", "s3", "count"])
    if kind == "s2":
        return _mc(f"Отчёт должен показывать {ctx}, а {moves}. Как вести измерение {gen}?", options(S2, pool), S2)
    if kind == "s1":
        return _mc(f"Аналитикам нужно только актуальное значение поля «{fld}», история не нужна, а {moves}. Как вести измерение {gen}?", options(S1, pool), S1)
    if kind == "s3":
        return _mc(f"Нужно видеть актуальное и одно предыдущее значение поля «{fld}», более старая история не нужна. Как вести измерение {gen}?", options(S3, pool), S3)
    n = pick(r, [200, 500, 1000, 1200])
    a, b = pick(r, [20, 40, 60, 80]), pick(r, [5, 10, 15])
    ok = n + a + 2 * b
    opts, ok_s = num_opts(r, ok, [n, n + a + b, n + 2 * (a + b), a + 2 * b], lo=1, spread=10)
    return _mc(f"Измерение {gen} ведётся как SCD2. Сначала в нём было {n} строк, по одной на запись. За год у {a} записей поле «{fld}» сменилось один раз, "
               f"у {b} — дважды. Сколько строк стало в измерении?", opts, ok_s)


@tpl("D07", "Раздувание суммы при соединении", "Моделирование данных", ["data", "backend"], "вычисление", 1.4, 1.7, ["SQL"])
def _(r):
    k = pick(r, [2, 3])
    orders = [(i + 1, pick(r, [300, 500, 800, 1000, 1200, 1500, 2000]), pick(r, [1, 1, 2, 3]), pick(r, [1, 2, 3, 4])) for i in range(k)]
    if all(p == 1 and it == 1 for _, _, p, it in orders):
        orders[0] = (1, orders[0][1], 2, 3)
    ok = sum(a * p * it for _, a, p, it in orders)
    near = [sum(a for _, a, _, _ in orders), sum(a * p for _, a, p, _ in orders), sum(a * it for _, a, _, it in orders), sum(a * (p + it) for _, a, p, it in orders)]
    desc = "\n".join(f"заказ {i}: amount = {a}, платежей {p}, позиций {it}" for i, a, p, it in orders)
    opts, ok_s = num_opts(r, ok, near, lo=1, spread=3)
    return _mc(f"Заказы, у каждого — строки в payments и в items:\n{desc}\n\n"
               "SELECT SUM(o.amount)\nFROM orders o\nJOIN payments p ON p.order_id = o.id\nJOIN items i ON i.order_id = o.id;\n\nЧто вернёт запрос?", opts, ok_s, code=True)


@tpl("D08", "Парадокс Симпсона", "Статистика", ["data", "ml"], "вычисление", 1.3, 2.0)
def _(r):
    segs = pick(r, [("новые", "постоянные"), ("мобильные", "десктоп"), ("Москва", "регионы")])
    for _ in range(200):
        base1, base2 = r.uniform(0.2, 0.4), r.uniform(0.03, 0.08)
        lift = r.uniform(1.08, 1.25)
        better = pick(r, ["А", "Б"])
        paradox = r.random() < 0.7
        big, small = pick(r, [1600, 1800, 2000, 2400]), pick(r, [200, 300, 400])
        if paradox:
            n = {better: (small, big), ("Б" if better == "А" else "А"): (big, small)}
        else:
            m1, m2 = pick(r, [800, 1000, 1200]), pick(r, [800, 1000, 1200])
            n = {"А": (m1, m2), "Б": (m1 + pick(r, [-100, 0, 100]), m2 + pick(r, [-100, 0, 100]))}
        conv = {v: (round(n[v][0] * base1 * (lift if v == better else 1)), round(n[v][1] * base2 * (lift if v == better else 1))) for v in "АБ"}
        rate = lambda v, s: Fraction(conv[v][s], n[v][s])
        tot = lambda v: Fraction(sum(conv[v]), sum(n[v]))
        w1 = "А" if rate("А", 0) > rate("Б", 0) else "Б" if rate("Б", 0) > rate("А", 0) else None
        w2 = "А" if rate("А", 1) > rate("Б", 1) else "Б" if rate("Б", 1) > rate("А", 1) else None
        wt = "А" if tot("А") > tot("Б") else "Б" if tot("Б") > tot("А") else None
        if w1 and w1 == w2 and wt:
            break
    else:
        raise ValueError
    combo = lambda s, t: f"{s} лучше в каждом сегменте, {t} — в сумме"
    ok = combo(w1, wt)
    buy = lambda x: f"{x} {plural(x, 'покупка', 'покупки', 'покупок')}"
    lines = "\n".join(f"{v}: {segs[0]} — {n[v][0]} визитов, {buy(conv[v][0])}; {segs[1]} — {n[v][1]} визитов, {buy(conv[v][1])}" for v in "АБ")
    return _mc(f"A/B-тест, конверсия в покупку по сегментам:\n{lines}\n\nКакой вывод верен?",
               options(ok, [combo(s, t) for s in "АБ" for t in "АБ"]), ok)


@tpl("D09", "Выбор графика", "Визуализация", ["data"], "выбор", 1.0, -1.0, ["Tableau"])
def _(r):
    what, val, x, y = pick(r, [("заказов", "сумма заказа", "сумма заказа", "число товаров в нём"), ("поездок", "стоимость поездки", "стоимость поездки", "расстояние"),
                               ("посылок", "вес посылки", "стоимость доставки", "вес посылки"), ("бронирований", "цена номера", "цена номера", "срок до заезда")])
    q, ok = pick(r, [
        (f"Нужно показать, как менялось число {what} по дням за последние три месяца. Какой график подходит лучше?", "Линейный график"),
        (f"Нужно сравнить число {what} по {pick(r, [6, 8, 12])} городам. Какой график подходит лучше?", "Столбчатая диаграмма"),
        (f"Нужно показать, как распределена {val} по {pick(r, ['10 000', '50 000'])} записям {what}. Какой график подходит лучше?", "Гистограмма"),
        (f"Нужно проверить, связаны ли {x} и {y} по данным {what}. Какой график подходит лучше?", "Диаграмма рассеяния"),
    ])
    return _mc(q, options(ok, ["Линейный график", "Столбчатая диаграмма", "Гистограмма", "Диаграмма рассеяния", "Круговая диаграмма"], r, sample=True), ok)


@tpl("D10", "Обманчивая ось", "Визуализация", ["data"], "вычисление", 1.2, 0.6, ["Tableau"])
def _(r):
    subj = pick(r, ["выручка двух магазинов", "число заказов в двух городах", "конверсия двух вариантов лендинга в баллах", "продажи двух менеджеров"])
    for _ in range(200):
        a = pick(r, [100, 120, 150, 200, 240, 300])
        p = pick(r, [Fraction(1, 10), Fraction(1, 5), Fraction(1, 4), Fraction(1, 2)])
        k = pick(r, [1, 2, 3, 4])
        d = a * p
        if d.denominator == 1 and (d / k).denominator == 1 and a - d / k > 0:
            break
    b, y0 = int(a + d), int(a - d / k)
    vis, act = k + 1, 1 + p
    act_s = times(float(act))
    ok = f"На картинке {times(vis)}, на деле {act_s}"
    ds = [f"На картинке {act_s}, на деле {times(vis)}", f"На картинке {act_s}, на деле {act_s}", f"На картинке {times(vis)}, на деле {times(vis)}"]
    return _mc(f"Столбчатая диаграмма: {subj}. Ось Y начинается с {y0}, столбец А — {a}, столбец Б — {b}. Во сколько раз столбец Б выше столбца А на картинке и во сколько раз больше само значение?",
               options(ok, ds), ok)

# ── ML ─────────────────────────────────────────────────────────────────


@tpl("L01", "Утечка данных", "Данные", ["ml", "data"], "выбор", 1.3, 0.4, ["scikit-learn"])
def _(r):
    target = pick(r, ["оттока", "дефолта", "покупки", "клика"])
    F1 = "Обучать нормализацию только на обучающей части (в Pipeline)"
    F2 = "Делить по времени: обучение раньше теста"
    F3 = "Делить по пользователям (GroupKFold)"
    F4 = "Считать кодирование по целевой только на фолдах обучения"
    q, ok = pick(r, [
        (f"Модель {target}: нормализацию признаков посчитали по всей выборке до разбиения на обучение и тест. Оценка качества завышена. Как исправить?", F1),
        (f"Модель {target} на истории за два года: строки перемешали и разбили случайно, в тесте оказались месяцы раньше части обучения. Как исправить оценку?", F2),
        (f"Модель {target}: у каждого пользователя десятки строк, разбиение случайное по строкам, и один пользователь попадает и в обучение, и в тест. Как исправить?", F3),
        (f"Модель {target}: категорию заменили средним целевой переменной по всей выборке, потом разбили на фолды. Качество на кросс-валидации подозрительно высокое. Как исправить?", F4),
    ])
    return _mc(q, options(ok, [F1, F2, F3, F4, "Увеличить долю теста", "Добавить регуляризацию"], r, sample=True), ok)


@tpl("L02", "Метрика при дисбалансе", "Классический ML", ["ml"], "выбор", 1.1, -0.3)
def _(r):
    p = pick(r, [1, 2, 5, 10])
    kind = pick(r, ["which", "const", "pr"])
    if kind == "which":
        q, ok, ds = f"Положительный класс составляет {p}{NB}% выборки. Какая метрика хуже всего отражает качество?", "Accuracy", ["ROC AUC", "PR AUC", "F1"]
    elif kind == "const":
        q = f"Положительный класс составляет {p}{NB}% выборки. Модель всегда предсказывает отрицательный класс. Чему равна её accuracy?"
        ok, ds = pct(100 - p), [pct(p), pct(50), pct(0), pct(100)]
    else:
        for _ in range(100):
            tp, fp, fn = pick(r, [20, 30, 40, 60, 80]), pick(r, [5, 10, 20, 40, 60]), pick(r, [10, 20, 40, 60, 120])
            if (100 * tp) % (tp + fp) == 0 and (100 * tp) % (tp + fn) == 0 and fp != fn:
                break
        else:
            tp, fp, fn = 40, 10, 60
        prec, rec = 100 * tp // (tp + fp), 100 * tp // (tp + fn)
        if r.random() < 0.5:
            q, ok, other = f"Модель пометила {tp + fp} объектов как положительные, из них верно {tp}. Всего положительных в выборке {tp + fn}. Чему равна precision?", prec, rec
        else:
            q, ok, other = f"Модель пометила {tp + fp} объектов как положительные, из них верно {tp}. Всего положительных в выборке {tp + fn}. Чему равен recall?", rec, prec
        ds = [pct(other), pct(100 - ok), pct(round(100 * tp / (tp + fp + fn))), pct(min(100, ok + 10))]
        ok = pct(ok)
    return _mc(q, options(ok, ds, r, gen=lambda r: pct(pick(r, range(5, 100, 5)))), ok)


@tpl("L03", "Кривые обучения", "Глубокое обучение", ["ml"], "выбор", 1.2, 0.7, ["PyTorch"])
def _(r):
    e = pick(r, [3, 5, 8, 12])
    A = "Ранняя остановка и регуляризация"
    B = "Усложнить модель или ослабить регуляризацию"
    C = "Уменьшить learning rate"
    tr = dec(pick(r, [0.9, 1.1, 1.3]), 2)
    q, ok = pick(r, [
        (f"Потери на обучении падают, на валидации растут с {e}-й эпохи. Что делать в первую очередь?", A),
        (f"Потери и на обучении, и на валидации держатся около {tr} и почти не отличаются, после {e}-й эпохи перестали падать. Что делать в первую очередь?", B),
        (f"После {e * 100} шагов потери на обучении начали скакать на порядок, а потом стали NaN. Что делать в первую очередь?", C),
    ])
    return _mc(q, options(ok, [A, B, C, "Увеличить learning rate", "Убрать валидацию"], r, sample=True), ok)


@tpl("L04", "Размерности матриц", "Математика", ["ml"], "вычисление", 1.1, -0.8, ["PyTorch"])
def _(r):
    n, d, k = r.sample([16, 32, 64, 100, 128, 256, 300, 512, 768, 10, 5], 3)
    kind = pick(r, ["xw", "xtx", "xxt", "bad"])
    E = "Ошибка: размерности не согласованы"
    if kind == "xw":
        q, ok = f"X.shape == ({n}, {d}), W.shape == ({d}, {k}). Какой будет форма X @ W?", f"({n}, {k})"
    elif kind == "xtx":
        q, ok = f"X.shape == ({n}, {d}). Какой будет форма X.T @ X?", f"({d}, {d})"
    elif kind == "xxt":
        q, ok = f"X.shape == ({n}, {d}). Какой будет форма X @ X.T?", f"({n}, {n})"
    else:
        q, ok = f"X.shape == ({n}, {d}), W.shape == ({n}, {k}). Какой будет форма X @ W?", E
    pool = [f"({n}, {k})", f"({d}, {k})", f"({n}, {d})", f"({k}, {n})", f"({d}, {d})", f"({n}, {n})", E]
    return _mc(q, options(ok, pool, r, sample=True), ok, code=True)


@tpl("L05", "Байес и редкое событие", "Математика", ["ml", "data"], "вычисление", 1.3, 1.0)
def _(r):
    p = pick(r, [Fraction(1, 2), Fraction(1), Fraction(2)])
    s, f = pick(r, [80, 90, 95, 99]), pick(r, [1, 2, 5])
    subj, pos, neg = pick(r, [("Детектор мошенничества", "мошеннических транзакций", "честных"), ("Спам-фильтр", "спама среди писем", "обычных писем"),
                              ("Контроль качества", "бракованных деталей", "годных")])
    post = (s * p) / (s * p + f * (100 - p))
    ok = round(float(post) * 100)
    ps = dec(float(p), 1).replace(",0", "")
    q = (f"{subj}: доля {pos} — {ps}{NB}%. Он ловит {s}{NB}% положительных и ошибочно помечает {f}{NB}% {neg}. "
         "Какая доля помеченных на самом деле положительные? Округлите до процента.")
    opts, ok_s = num_opts(r, ok, [s, 100 - f, round(float(p)), min(99, ok * 2)], lo=1, spread=6, fmt=lambda x: pct(x))
    return _mc(q, opts, ok_s)


@tpl("L06", "Модель в проде", "Продакшен ML", ["ml"], "выбор", 1.2, 0.5, ["MLflow"])
def _(r):
    dom = pick(r, ["рекомендаций", "скоринга заявок", "антифрода", "прогноза спроса"])
    A = "Проверить дрейф: сравнить распределения признаков в проде и на обучении"
    B = "Свести расчёт признаков к одному коду для обучения и сервиса"
    C = "Теневой запуск или A/B на небольшой доле трафика"
    D = "Реестр моделей с версиями и откатом (например, MLflow)"
    gen = ["Переобучить модель на большем числе эпох", "Поднять порог классификации", "Выкатить сразу на весь трафик", "Увеличить размер батча"]
    q, ok = pick(r, [
        (f"Модель {dom} месяц работала стабильно, затем качество стало падать; код и модель не менялись, а {pick(r, ['пришло много новых пользователей после рекламы', 'партнёр сменил формат данных', 'запустили новую линейку товаров'])}. Что проверить в первую очередь?", A),
        (f"Офлайн модель {dom} даёт хорошее качество, а с первого дня в проде заметно хуже. Признак «{pick(r, ['число покупок за 30 дней', 'средний чек', 'частота входов'])}» на обучении считали SQL-запросом по истории, а в сервисе — отдельным кодом. Что исправить?", B),
        (f"Новая модель {dom} офлайн лучше старой. Как выкатить её с наименьшим риском?", C),
        (f"Выкаченная модель {dom} сломала выдачу, а какие веса работали вчера, никто точно не знает. Чего не хватало?", D),
    ])
    return _mc(q, options(ok, r.sample(gen, 3)), ok)


@tpl("L07", "Пакетный инференс", "Продакшен ML", ["ml"], "вычисление", 1.3, 1.2, ["PyTorch"])
def _(r):
    t0, t1 = pick(r, [10, 20, 30, 40]), pick(r, [1, 2, 4])
    b, rps = pick(r, [8, 16, 32]), pick(r, [500, 1000, 2000, 3000])
    thr = Fraction(1000 * b, t0 + t1 * b)          # запросов в секунду на воркер
    ok = math.ceil(Fraction(rps) / thr)
    near = [math.ceil(Fraction(rps * (t0 + t1), 1000)), math.ceil(Fraction(rps * t1, 1000)), ok - 1, ok + 1]
    opts, ok_s = num_opts(r, ok, near, lo=1)
    return _mc(f"Модель на одном воркере обрабатывает батч из B запросов за {t0} + {t1}·B мс. Воркер берёт батчи по {b} {plural(b, 'запросу', 'запроса', 'запросов')} подряд, без простоя. "
               f"Сколько воркеров минимум нужно, чтобы держать {rps} запросов в секунду?", opts, ok_s)


@tpl("L08", "Порог по стоимости ошибок", "Классический ML", ["ml"], "вычисление", 1.3, 1.7, ["scikit-learn"])
def _(r):
    dom, fp_s, fn_s = pick(r, [("антифрода", "лишняя ручная проверка транзакции", "пропущенное мошенничество"),
                               ("удержания клиентов", "скидка клиенту, который и так бы остался", "ушедший клиент"),
                               ("кредитного скоринга", "отказ надёжному заёмщику", "выданный кредит, который не вернут")])
    for _ in range(100):
        c_fp = pick(r, [100, 200, 300, 500, 1000])
        thr = pick(r, [Fraction(1, 20), Fraction(1, 10), Fraction(1, 5), Fraction(1, 4), Fraction(2, 5)])
        c_fn = c_fp * (1 - thr) / thr
        if c_fn.denominator == 1:
            break
    c_fn = int(c_fn)
    fmt = lambda x: f"p > {dec(float(x), 2)}"
    ok = fmt(thr)
    ds = [fmt(1 - thr), fmt(Fraction(1, 2)), fmt(Fraction(c_fp, c_fn)) if c_fp != c_fn else fmt(Fraction(3, 4))]
    rub = lambda x: f"{x:,}".replace(",", NB) + f"{NB}₽"
    return _mc(f"Модель {dom} выдаёт откалиброванную вероятность p положительного класса. Ложная тревога ({fp_s}) стоит {rub(c_fp)}, "
               f"пропуск ({fn_s}) — {rub(c_fn)}, верное решение — 0{NB}₽. При каком пороге выгодно помечать объект как положительный?",
               options(ok, ds, r, gen=lambda r: fmt(Fraction(pick(r, [3, 6, 15, 30, 60]), 100))), ok)


@tpl("L09", "ROC AUC по парам", "Классический ML", ["ml"], "вычисление", 1.4, 2.1, ["scikit-learn"])
def _(r):
    np_, nn = pick(r, [(3, 4), (4, 3), (3, 3), (2, 5)])
    for _ in range(200):
        sc = r.sample(range(5, 96, 5), np_ + nn)
        pos, neg = sorted(sc[:np_], reverse=True), sorted(sc[np_:], reverse=True)
        good = sum(1 for a in pos for b in neg if a > b)
        if np_ * nn / 2 < good < np_ * nn:
            break
    tot = np_ * nn
    fmt = lambda x: dec(x, 2)
    acc = (sum(1 for a in pos if a >= 50) + sum(1 for b in neg if b < 50)) / (np_ + nn)
    ok = fmt(good / tot)
    near = [fmt(1 - good / tot), fmt(acc), fmt((good + 1) / tot), fmt((good - 1) / tot)]
    s = lambda xs: "; ".join(dec(x / 100, 2) for x in xs)
    return _mc(f"Скоры модели на {np_ + nn} объектах:\nположительные: {s(pos)}\nотрицательные: {s(neg)}\n\nЧему равен ROC AUC?",
               options(ok, near, r, gen=lambda r: fmt(r.randrange(1, tot) / tot)), ok, code=True)

# ── DevOps ─────────────────────────────────────────────────────────────


def _rwx(m: str) -> str:
    return "".join(("r" if int(c) & 4 else "-") + ("w" if int(c) & 2 else "-") + ("x" if int(c) & 1 else "-") for c in m)


@tpl("O01", "Права на файл", "Linux", ["devops", "backend"], "вычисление", 1.0, -1.1, ["Linux"])
def _(r):
    m = pick(r, ["6", "7", "5", "4"]) + pick(r, ["0", "4", "5", "6", "7"]) + pick(r, ["0", "4", "5"])
    ok = _rwx(m)
    near = [_rwx(m[::-1]), "rwxrwxrwx", _rwx(m[0] + m[0] + m[0]), _rwx(str(7 - int(m[0])) + m[1:])]
    gen = lambda r: _rwx("".join(pick(r, "01234567") for _ in range(3)))
    return _mc(f"Что означает chmod {m} в виде строки прав (владелец, группа, остальные)?", options(ok, near, r, gen=gen), ok)


@tpl("O02", "Проверки готовности", "Контейнеры", ["devops", "backend"], "выбор", 1.3, 0.6, ["Kubernetes"])
def _(r):
    s = pick(r, [30, 60, 120, 180])
    q, ok = pick(r, [
        (f"Под в Kubernetes жив, но ещё {s} секунд прогревает кэш и не должен получать трафик. Какая настройка это описывает?", "readinessProbe"),
        ("Процесс в контейнере жив, но завис во взаимоблокировке и больше не отвечает. Нужно, чтобы Kubernetes сам перезапускал контейнер. Какая настройка нужна?", "livenessProbe"),
        (f"Приложение стартует до {s} секунд, и livenessProbe убивает его раньше, чем оно поднимется. Какая настройка решает это?", "startupProbe"),
        ("Перед остановкой пода нужно подождать несколько секунд, чтобы балансировщик успел убрать его из ротации. Какая настройка нужна?", "preStop-хук"),
    ])
    return _mc(q, options(ok, ["readinessProbe", "livenessProbe", "startupProbe", "preStop-хук"]), ok)


@tpl("O03", "Состояние Terraform", "Инфраструктура как код", ["devops"], "выбор", 1.2, 1.2, ["Terraform"])
def _(r):
    res = pick(r, ["yandex_compute_instance.web", "yandex_vpc_network.main", "aws_s3_bucket.logs", "yandex_mdb_postgresql_cluster.db"])
    kind = pick(r, ["lock", "drift", "rename", "secret"])
    if kind == "lock":
        q = "Двое инженеров применяют terraform apply одновременно с локальным state. Чем это грозит и как защититься?"
        ok, ds = "Расхождением state и ресурсов: нужен удалённый state с блокировкой", ["Ничем: Terraform сольёт изменения", "Удалением всех ресурсов", "Ошибкой синтаксиса"]
    elif kind == "drift":
        q = f"Кто-то вручную изменил {res} в консоли облака. Что покажет terraform plan?"
        ok, ds = "Расхождение и изменения, которые вернут ресурс к коду", ["Ничего: state уже обновлён", "Ошибку блокировки state", "Предложение удалить все ресурсы модуля"]
    elif kind == "rename":
        new = res.split(".")[0] + "." + pick(r, ["primary", "frontend", "archive"])
        q = f"В коде переименовали ресурс {res} в {new}, больше ничего не меняли. Что сделает terraform apply?"
        ok, ds = "Удалит ресурс и создаст новый, если не добавить блок moved или terraform state mv", ["Просто переименует ресурс в state", "Ничего: имя в коде ни на что не влияет", "Остановится с ошибкой синтаксиса"]
    else:
        q = f"Пароль базы передан в {res} через переменную с sensitive = true. Где окажется значение?"
        ok, ds = "В state открытым текстом: state нужно шифровать и закрыть к нему доступ", ["Нигде: sensitive не даёт его сохранить", "Только в выводе plan, замаскированным", "В state в виде хеша"]
    return _mc(q, options(ok, ds), ok)


@tpl("O04", "Алерт по метрике", "Наблюдаемость", ["devops", "backend"], "выбор", 1.1, 0.1, ["Prometheus"])
def _(r):
    A = "Гистограмма длительностей и histogram_quantile"
    B = "rate() счётчика ошибок, делённый на rate() всех запросов"
    C = "Gauge свободного места и сравнение с порогом"
    D = "increase() счётчика перезапусков за окно"
    q, ok = pick(r, [
        (f"Нужен алерт «95{NB}% запросов медленнее {pick(r, [200, 300, 500])} мс за 5 минут». Что нужно в Prometheus?", A),
        (f"Нужен алерт «доля ответов 5xx больше {pick(r, [1, 2, 5])}{NB}% за 5 минут». Что нужно в Prometheus?", B),
        (f"Нужен алерт «на диске осталось меньше {pick(r, [5, 10, 15])}{NB}% места». Что нужно в Prometheus?", C),
        (f"Нужен алерт «контейнер перезапустился больше {pick(r, [3, 5])} раз за час». Что нужно в Prometheus?", D),
    ])
    return _mc(q, options(ok, [A, B, C, D, "Средняя задержка за минуту", "Счётчик запросов без rate()"], r, sample=True), ok)


@tpl("O05", "Подсеть и маска", "Сети", ["devops"], "вычисление", 1.1, -0.3, ["Linux"])
def _(r):
    p = pick(r, [22, 23, 24, 25, 26, 27, 28, 29])
    ip = ipaddress.IPv4Address(f"10.{int(r.random() * 256)}.{int(r.random() * 256)}.{1 + int(r.random() * 254)}")
    net = ipaddress.ip_network(f"{ip}/{p}", strict=False)
    kind = pick(r, ["hosts", "network", "broadcast"])
    if kind == "hosts":
        ok = 2 ** (32 - p) - 2
        opts, ok_s = num_opts(r, ok, [2 ** (32 - p), 2 ** (32 - p) - 1, 2 ** (31 - p) - 2, 2 ** (33 - p) - 2], lo=1)
        return _mc(f"Сколько адресов можно раздать узлам в подсети {net}, если адрес сети и широковещательный не используются?", opts, ok_s)
    block = 2 ** (32 - p)
    na, ba = net.network_address, net.broadcast_address
    o = str(ip).split(".")
    zero = ipaddress.IPv4Address(".".join(o[:3] + ["0"]))
    if kind == "network":
        ok, near, q = str(na), [str(zero), str(ba), str(na + block) if int(na) + block < 2 ** 32 else str(na - block)], f"Какой адрес сети у узла {ip}/{p}?"
    else:
        ok, near, q = str(ba), [str(na), str(ba - 1), str(ipaddress.IPv4Address(".".join(o[:3] + ["255"])))], f"Какой широковещательный адрес у подсети узла {ip}/{p}?"
    gen = lambda r: str(na + r.randrange(1, block)) if block > 2 else str(na + 4)
    return _mc(q, options(ok, near, r, gen=gen), ok)


@tpl("O06", "Диагностика сети", "Сети", ["devops", "backend"], "выбор", 1.2, 0.7, ["Linux"])
def _(r):
    port, n = pick(r, [8000, 8080, 3000, 9000]), pick(r, [30, 60])
    host = pick(r, ["api.example.ru", "pay.internal", "auth.example.com"])
    A = "Приложение не слушает этот адрес и порт: упало или запущено на другом"
    B = "Приложение не уложилось в proxy_read_timeout"
    C = "Имя не разрешается в DNS: проверить запись и настройки резолвера"
    D = "Порт закрыт фаерволом или группой безопасности между машинами"
    E = "Истёк сертификат на сервере: перевыпустить"
    q, ok = pick(r, [
        (f"nginx отвечает 502, в error.log — «connect() failed (111: Connection refused) while connecting to upstream» для 127.0.0.1:{port}. В чём причина?", A),
        (f"nginx отвечает 504 ровно через {n} секунд, а приложение в своём логе заканчивает этот запрос через {n + pick(r, [5, 15, 30])} секунд. В чём причина?", B),
        (f"curl https://{host}/ сразу пишет «Could not resolve host». В чём причина?", C),
        (f"С машины приложения nc -zv db.internal 5432 висит и падает по таймауту, а на самой машине базы порт 5432 слушается. В чём причина?", D),
        (f"curl https://{host}/ пишет «SSL certificate problem: certificate has expired». В чём причина?", E),
    ])
    return _mc(q, options(ok, [A, B, C, D, E], r, sample=True), ok)

# ── Разбор кода: ИИ разрешён ───────────────────────────────────────
# Модель решит выбор из четырёх за секунду, и мы это признаём. В заданиях формата «разбор»
# кандидату прямо сказано, что модель можно использовать: оценивается суждение — найти ошибку,
# объяснить последствие, выбрать исправление с учётом ограничения. Это то, что остаётся
# после ИИ и что работодатель покупает.

def _review(q, opts, ok, code=True):
    return {"q": q, "opts": opts, "ok": ok, "code": code, "ai": True}


@tpl("R01", "Граница среза", "Проектирование", ["backend", "data", "ml"], "разбор", 1.3, 0.2, ["Python"])
def _(r):
    what = pick(r, STORIES)
    fn = pick(r, ["tail_sum", "last_total", "recent_sum"])
    A, B, C, D = "Берёт k + 1 элемент", "Берёт k − 1 элемент", "Берёт первые k элементов, а не последние", "При k = 0 вернёт сумму всех элементов вместо 0"
    body, ok = pick(r, [("sum(xs[len(xs) - k - 1:])", A), ("sum(xs[len(xs) - k + 1:])", B), ("sum(xs[:k])", C), ("sum(xs[-k:])", D)])
    return _review(f"ИИ разрешён. Функция должна вернуть сумму последних k {what}:\n\ndef {fn}(xs, k):\n    return {body}\n\nЧто с ней не так?",
                   options(ok, [A, B, C, D, "Падает при k > len(xs)", "Всё верно"], r, sample=True), ok)


@tpl("R02", "Устаревшее замыкание", "Рендеринг", ["frontend"], "разбор", 1.3, 0.6, ["React"])
def _(r):
    kind = pick(r, ["interval", "click", "timeout"])
    if kind == "interval":
        k, ms = pick(r, [1, 2, 5]), pick(r, [500, 1000, 2000])
        q = (f"ИИ разрешён. Счётчик по таймеру:\n\nconst [n, setN] = useState(0);\nuseEffect(() => {{\n  const t = setInterval(() => setN(n + {k}), {ms});\n"
             f"  return () => clearInterval(t);\n}}, []);\n\nЧто увидит пользователь и как исправить?")
        ok = f"Застрянет на {k}; setN(v => v + {k})"
        ds = [f"Будет расти на {k}; всё верно", "Ошибка компиляции", "Будет расти вдвое быстрее; добавить n в зависимости и убрать cleanup"]
    elif kind == "click":
        c = pick(r, [2, 3, 4])
        calls = "\n".join("  setN(n + 1);" for _ in range(c))
        q = f"ИИ разрешён. Кнопка должна прибавлять {c}:\n\nconst [n, setN] = useState(0);\nconst add = () => {{\n{calls}\n}};\n\nЧто произойдёт по нажатию и как исправить?"
        ok = f"Прибавит 1, а не {c}; setN(v => v + 1) в каждом вызове"
        ds = [f"Прибавит {c}; всё верно", f"Прибавит {c}, но с задержкой; обернуть в useEffect", "Ошибка: setN нельзя вызывать дважды"]
    else:
        n0, m = pick(r, [0, 1, 2, 3]), pick(r, [2, 3, 4])
        q = (f"ИИ разрешён. Кнопка «Показать» выводит счётчик через 3 секунды:\n\nconst show = () => setTimeout(() => alert(n), 3000);\n\n"
             f"Счётчик равен {n0}, пользователь нажал «Показать» и сразу {m} раза нажал «+1». Что покажет alert и как получить актуальное значение?")
        ok = f"Покажет {n0}: замыкание видит n на момент нажатия; читать из useRef"
        ds = [f"Покажет {n0 + m}; всё верно", "Покажет undefined: n вне области видимости", "Ошибка: alert внутри таймера запрещён"]
    return _review(q, options(ok, ds), ok)


@tpl("R03", "NULL в запросе", "SQL", ["data", "backend"], "разбор", 1.2, 0.0, ["SQL", "PostgreSQL"])
def _(r):
    table = pick(r, ["employees", "orders", "categories", "users"])
    col = pick(r, ["manager_id", "discount", "parent_id", "promo_code"])
    kind = pick(r, ["eq", "neq", "notin", "count"])
    if kind in ("eq", "neq"):
        want, op, fix = ("без значения", "= NULL", "IS NULL") if kind == "eq" else ("со значением", pick(r, ["!= NULL", "<> NULL"]), "IS NOT NULL")
        q = f"ИИ разрешён. Запрос должен вернуть строки {want} в {col}:\n\nSELECT * FROM {table} WHERE {col} {op};\n\nЧто вернёт запрос и почему?"
        ok = f"Ничего: сравнение с NULL даёт NULL; нужно {fix}"
        ds = [f"Строки, где {col} пустой", "Все строки", "Ошибку синтаксиса"]
    elif kind == "notin":
        q = ("ИИ разрешён. Запрос должен вернуть клиентов без заказов:\n\nSELECT * FROM clients\nWHERE id NOT IN (SELECT client_id FROM orders);\n\n"
             "В orders.client_id есть строки с NULL. Что вернёт запрос?")
        ok = "Ничего: NOT IN со списком, где есть NULL, не бывает истинным; нужно NOT EXISTS"
        ds = ["Клиентов без заказов, как задумано", "Все строки clients", "Ошибку: NULL в подзапросе"]
    else:
        vals = [pick(r, ["NULL", str(1 + int(r.random() * 9))]) for _ in range(pick(r, [5, 6, 7]))]
        if "NULL" not in vals:
            vals[int(r.random() * len(vals))] = "NULL"
        if all(v == "NULL" for v in vals):
            vals[0] = "4"
        n, nn = len(vals), sum(1 for v in vals if v != "NULL")
        q = f"ИИ разрешён. Ожидали, что оба числа совпадут:\n\nSELECT COUNT(*), COUNT({col}) FROM {table};\n\nВ колонке {col} значения: {', '.join(vals)}. Что вернёт запрос?"
        ok = f"{n} и {nn}: COUNT({col}) не считает NULL"
        ds = [f"{n} и {n}: оба считают строки", f"{nn} и {nn}: оба пропускают NULL", f"{n} и {n - nn}: COUNT({col}) считает только NULL"]
    return _review(q, options(ok, ds), ok)


@tpl("R04", "Кэш под нагрузкой", "Конкурентность", ["backend", "devops"], "разбор", 1.4, 1.1, ["Redis"])
def _(r):
    ttl = pick(r, [30, 60, 300])
    S = "Отдавать устаревшее и обновлять одним воркером (stale-while-revalidate, lock)"
    J = "Добавить к TTL случайный разброс"
    N = "Кэшировать и отсутствие записи на короткий срок"
    I = "Удалять ключ из кэша сразу после записи в базу"
    g = ["Убрать TTL", "Увеличить пул соединений базы", "Кэшировать на клиенте"]
    q, ok, ds = pick(r, [
        (f"Горячий ключ при промахе читается из базы и кладётся в Redis с TTL {ttl} с. Когда ключ истекает, база получает всплеск одинаковых запросов. Ответ может быть чуть устаревшим. Что исправить?", S, [J, N, I] + g),
        (f"{pick(r, [10, 50, 200])} тыс. ключей прогрели одним скриптом с TTL {ttl} с. Ровно через {ttl} с база ловит всплеск запросов. Что исправить?", J, [N, I] + g),
        (f"Боты запрашивают несуществующие id; каждый такой запрос проходит мимо кэша в базу. Что исправить?", N, [S, J, I] + g),
        (f"Цену в базе обновили, но пользователи ещё до {ttl} с видят старую из Redis, а нужно сразу. Что исправить?", I, [S, J, N] + g),
    ])
    return _review("ИИ разрешён. " + q, options(ok, ds, r, sample=True), ok)


@tpl("R05", "Проверка ответа модели", "Проектирование", ALL, "разбор", 1.2, 0.8)
def _(r):
    k = pick(r, [2, 3, 4, 6])
    inst = f"{k} {plural(k, 'экземпляр', 'экземпляра', 'экземпляров')} API за балансировщиком"
    kind = pick(r, ["sess", "disk", "cron", "lock"])
    if kind == "sess":
        q = f"Модель предложила хранить {pick(r, ['10 000', '250 000'])} сессий пользователей в памяти процесса API «для скорости». Работают {inst}. В чём главная проблема?"
        ok, ds = "Сессия есть только у одного экземпляра: запрос на другой её не найдёт", ["Память закончится", "Балансировщик не умеет HTTP", "Проблемы нет"]
    elif kind == "disk":
        q = f"Модель предложила сохранять загруженные пользователями файлы в папку /uploads внутри контейнера API. Работают {inst}. В чём главная проблема?"
        ok, ds = "Файл останется на одном экземпляре и пропадёт при пересоздании контейнера", ["Диск быстро закончится", "Файлы нельзя отдавать по HTTP", "Проблемы нет"]
    elif kind == "cron":
        q = f"Модель предложила запускать ежедневную рассылку планировщиком внутри процесса API. Работают {inst}. Что произойдёт?"
        ok = f"Рассылка уйдёт {k} {plural(k, 'раз', 'раза', 'раз')} вместо одного"
        ds = ["Рассылка уйдёт один раз, как задумано", "Рассылка не запустится ни разу", f"Рассылка уйдёт {k + 1} {plural(k + 1, 'раз', 'раза', 'раз')}"]
    else:
        q = f"Модель предложила защитить списание денег от двойного нажатия threading.Lock в коде API. Работают {inst}. В чём главная проблема?"
        ok, ds = "Блокировка действует внутри одного процесса: другой экземпляр спишет повторно", ["Lock замедлит API в разы", "threading.Lock не работает в Python", "Проблемы нет"]
    return _review(f"ИИ разрешён. {q}", options(ok, ds), ok, code=False)

# ── Трудные задания для верхних грейдов ─────────────────────────────


def _js_async(prog):
    """Исполняет мини-программу по правилам событийного цикла: await null и .then — микрозадачи, setTimeout — макрозадача."""
    out, micro, macro = [], deque(), []

    def chain(xs, i=0):
        out.append(xs[i])
        if i + 1 < len(xs):
            micro.append(lambda: chain(xs, i + 1))

    def body(segs, i=0):
        out.extend(segs[i])
        if i + 1 < len(segs):
            micro.append(lambda: body(segs, i + 1))

    for kind, x in prog:
        if kind == "log":
            out.append(x)
        elif kind == "timeout":
            macro.append(x)
        elif kind == "chain":
            micro.append(lambda xs=x: chain(xs))
        elif kind == "call":
            body(x)
    while micro:
        micro.popleft()()
    for x in macro:
        out.append(x)
        while micro:
            micro.popleft()()
    return out


@tpl("F07", "async/await и очередь микрозадач", "Язык и типы", ["frontend", "backend"], "вычисление", 1.4, 2.1, ["TypeScript"])
def _(r):
    fn = pick(r, ["load", "step", "task", "sync"])
    awaits = pick(r, [1, 2])
    kinds = ["log", "timeout", "chain", "call", pick(r, ["log", "timeout", "chain"])]
    n_logs = {"log": 1, "timeout": 1, "chain": 2, "call": awaits + 1}
    for _ in range(200):
        r.shuffle(kinds)
        labels = r.sample(range(1, sum(n_logs[k] for k in kinds) + 1), sum(n_logs[k] for k in kinds))
        it = iter(labels)
        prog, segs = [], None
        for k in kinds:
            if k == "call":
                segs = [[next(it)] for _ in range(awaits + 1)]
                prog.append(("call", segs))
            elif k == "chain":
                prog.append(("chain", [next(it), next(it)]))
            else:
                prog.append((k, next(it)))
        out = _js_async(prog)
        # порядок, в котором числа стоят в тексте программы: сначала тело функции, потом остальное
        flat = [y for s in segs for y in s] + [x for k, v in prog if k != "call" for x in ([v] if k in ("log", "timeout") else v)]
        if out != flat:
            break
    lines = [f"async function {fn}() {{"]
    for i, s in enumerate(segs):
        lines.append(f"  console.log({s[0]});")
        if i + 1 < len(segs):
            lines.append("  await null;")
    lines.append("}")
    for k, v in prog:
        if k == "log":
            lines.append(f"console.log({v});")
        elif k == "timeout":
            lines.append(f"setTimeout(() => console.log({v}));")
        elif k == "chain":
            lines.append(f"Promise.resolve()\n  .then(() => console.log({v[0]}))\n  .then(() => console.log({v[1]}));")
        else:
            lines.append(f"{fn}();")
    j = lambda xs: " ".join(map(str, xs))
    # Типичные ошибки: цепочка .then целиком за раз; await как макрозадача; порядок как в коде.
    def whole_chain(prog):
        o, m, rest = [], [], []
        for k, v in prog:
            if k == "log": o.append(v)
            elif k == "timeout": rest.append(v)
            elif k == "chain": m.extend(v)
            else:
                o.extend(v[0]); m.extend(y for s in v[1:] for y in s)
        return o + m + rest
    def await_macro(prog):
        o, m, rest = [], [], []
        for k, v in prog:
            if k == "log": o.append(v)
            elif k == "timeout": rest.append(v)
            elif k == "chain": m.extend(v)
            else:
                o.extend(v[0]); rest.extend(y for s in v[1:] for y in s)
        return o + m + rest
    ok = j(out)
    return _mc("\n".join(lines) + "\n\nВ каком порядке выведутся числа?",
               options(ok, [j(whole_chain(prog)), j(await_macro(prog)), j(flat)], r, gen=lambda r: j(shuffled(r, labels))), ok, code=True)


@tpl("F08", "Мемоизация и рендеры", "Рендеринг", ["frontend"], "вычисление", 1.3, 1.7, ["React"])
def _(r):
    clicks = pick(r, [3, 4, 5, 6, 8])
    child = pick(r, ["Row", "Chart", "Avatar", "Price"])
    prop = pick(r, ["options", "config", "style"])
    variants = [
        ("memo", f"{prop}={{42}}", "", 1),
        ("memo", f"{prop}={{{{ dense: true }}}}", "", 1 + clicks),
        ("memo", "onPick={() => setN(0)}", "", 1 + clicks),
        ("memo", f"{prop}={{{prop}}}", f"  const {prop} = useMemo(() => ({{ dense: true }}), []);\n", 1),
        ("memo", "onPick={onPick}", "  const onPick = useCallback(() => setN(0), []);\n", 1),
        ("memo", "onPick={onPick}", "  const onPick = useCallback(() => console.log(n), [n]);\n", 1 + clicks),
        ("memo", "big={n > 100}", "", 1),
        ("plain", f"{prop}={{42}}", "", 1 + clicks),
    ]
    kind, attr, decl, ok = pick(r, variants)
    head = f"const {child} = memo(function {child}(props) {{ /* … */ }});" if kind == "memo" else f"function {child}(props) {{ /* … */ }}"
    code = (f"{head}\n\nfunction Page() {{\n  const [n, setN] = useState(0);\n{decl}  return (\n    <>\n      <button onClick={{() => setN(n + 1)}}>+</button>\n"
            f"      <{child} {attr} />\n    </>\n  );\n}}")
    opts, ok_s = num_opts(r, ok, [1, clicks, clicks + 1, 2 * clicks + 1, 2], lo=1)
    return _mc(f"{code}\n\nПродакшен-сборка, без StrictMode. Пользователь нажал «+» {clicks} {plural(clicks, 'раз', 'раза', 'раз')}. Сколько всего раз отрендерится {child}, считая первый рендер?",
               opts, ok_s, code=True)


@tpl("M04", "Корутины и время выполнения", "Конкурентность", ["mobile"], "вычисление", 1.3, 1.9, ["Kotlin"])
def _(r):
    a, b = r.sample([200, 300, 400, 500, 700, 800, 1000], 2)
    fa, fb = pick(r, [("loadUser", "loadFeed"), ("loadCart", "loadPrices"), ("fetchProfile", "fetchOrders")])
    kind = pick(r, ["seq", "async", "lazy", "lazy_start"])
    if kind == "seq":
        body, ok = f"    val x = {fa}()\n    val y = {fb}()\n    println(x + y)", a + b
    elif kind == "async":
        body, ok = f"    val x = async {{ {fa}() }}\n    val y = async {{ {fb}() }}\n    println(x.await() + y.await())", max(a, b)
    elif kind == "lazy":
        body, ok = (f"    val x = async(start = CoroutineStart.LAZY) {{ {fa}() }}\n    val y = async(start = CoroutineStart.LAZY) {{ {fb}() }}\n"
                    "    println(x.await() + y.await())"), a + b
    else:
        body, ok = (f"    val x = async(start = CoroutineStart.LAZY) {{ {fa}() }}\n    val y = async(start = CoroutineStart.LAZY) {{ {fb}() }}\n"
                    "    x.start(); y.start()\n    println(x.await() + y.await())"), max(a, b)
    code = (f"suspend fun {fa}(): Int {{ delay({a}); return 1 }}\nsuspend fun {fb}(): Int {{ delay({b}); return 2 }}\n\n"
            f"fun main() = runBlocking {{\n  val ms = measureTimeMillis {{\n{body}\n  }}\n  println(ms)\n}}")
    fmt = lambda x: f"≈{NB}{x}{NB}мс"
    gen = lambda r: fmt(pick(r, [100, 200, 300, 400, 500, 600, 800, 900, 1100, 1200, 1500, 1800, 2000]))
    return _mc(f"{code}\n\nЧто примерно напечатает последняя строка?", options(fmt(ok), [fmt(a + b), fmt(max(a, b)), fmt(min(a, b)), fmt(abs(a - b))], r, gen=gen),
               fmt(ok), code=True)


from . import bank_code, bank_x1, bank_x2, bank_x3  # noqa: E402,F401 — дополнительные шаблоны регистрируются в T при импорте

TEMPLATES = sorted(T, key=lambda t: t.id)
BY_ID = {t.id: t for t in TEMPLATES}


def for_spec(spec_id: str) -> list[Template]:
    return [t for t in TEMPLATES if spec_id in t.specs]


def for_stack(stack: list[str], spec_id: str | None = None) -> list[Template]:
    """Задания под вакансию: по тегам стека; так же собираются регулярные задания."""
    s = {x.lower() for x in stack}
    out = [t for t in TEMPLATES if any(tag.lower() in s for tag in t.tags) and (spec_id is None or spec_id in t.specs)]
    return out or (for_spec(spec_id) if spec_id else TEMPLATES)


def instance(t: Template, seed: int) -> dict:
    """Экземпляр шаблона из зерна. Поле ok (эталон) клиенту не отдаётся.
    Варианты перемешиваются здесь, от того же зерна: шаблон кладёт эталон куда угодно,
    на экране он окажется на любом месте. ok — текст варианта, а не номер, поэтому после
    перемешивания он остаётся верным. Повтор вариантов — ошибка шаблона, не экземпляра."""
    r = random.Random(seed)
    d = t.make(r)
    if not d.get("open"):
        opts = d["opts"]
        if len(opts) < 2 or len(set(opts)) != len(opts):
            raise ValueError(f"{t.id}, зерно {seed}: варианты повторяются или их меньше двух: {opts}")
        if d["ok"] not in opts:
            raise ValueError(f"{t.id}, зерно {seed}: эталона {d['ok']!r} нет среди вариантов")
        d["opts"] = shuffled(r, opts)
    d.update({"tpl": t.id, "seed": seed, "title": t.title, "skill": t.skill, "format": t.fmt})
    return d


def public(inst: dict) -> dict:
    """Клиенту без эталона, ключей рубрики и зерна: по зерну и открытому банку экземпляр собирается вместе с ответом."""
    return {k: v for k, v in inst.items() if k not in ("ok", "keys", "seed", "sandbox")}  # sandbox — скрытые тесты задания с кодом


def grade_open(text: str, inst: dict) -> dict:
    """Открытый ответ: в заглушке — по ключевым словам рубрики; с моделью — по той же рубрике.
    Оценка с низкой уверенностью идёт эксперту."""
    t = text.lower()
    hits = [any(k in t for k in ks) for ks in inst["keys"]]
    score = sum(hits) / len(inst["rubric"])
    return {"score": score, "hits": hits, "confident": len(text.strip()) > 60}
