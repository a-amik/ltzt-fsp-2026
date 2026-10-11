"""Дополнительные шаблоны банка, часть 2. Регистрируются тем же декоратором tpl из bank.py."""
from .bank import NB, _mc, num_opts, options, pick, tpl  # noqa: F401
from fractions import Fraction as _F
import math as _math

from .bank import pct as _pct


def _minus(x) -> str:
    return str(x).replace("-", "−")


def _rnd(x: _F) -> int:
    """Округление половины вверх, без плавающей точки."""
    return _math.floor(x + _F(1, 2))


# ── Аналитик данных ────────────────────────────────────────────────────

@tpl("Y01", "Число уникальных значений", "SQL", ["data"], "вычисление", 1.0, -1.5, ["SQL", "PostgreSQL", "ClickHouse"])
def _(r):
    table, col = pick(r, [("events", "user_id"), ("payments", "client_id"), ("sessions", "device_id"), ("orders", "shop_id")])
    pool = r.sample(range(101, 200), 3 + int(r.random() * 4))
    vals = [pick(r, pool) for _ in range(8 + int(r.random() * 4))]
    ok = len(set(vals))
    opts, ok_s = num_opts(r, ok, [len(vals), ok + 1, ok - 1], lo=1)
    return _mc(f"В таблице {table} колонка {col} содержит значения: {', '.join(map(str, vals))}.\n"
               f"Что вернёт SELECT COUNT(DISTINCT {col}) FROM {table}?", opts, ok_s)


@tpl("Y02", "Медиана выборки", "Статистика", ["data"], "вычисление", 1.1, -0.8)
def _(r):
    what = pick(r, ["время доставки заказов, мин", "сумма чеков, тыс. ₽", "длительность сессий, мин", "время ответа поддержки, мин"])
    vals = r.sample(range(10, 100), 7)
    s = sorted(vals)
    ok = s[3]
    opts, ok_s = num_opts(r, ok, [vals[3], round(sum(vals) / 7), s[2], s[4]], lo=1)
    return _mc(f"Выборка из семи наблюдений ({what}): {', '.join(map(str, vals))}.\nЧему равна медиана?", opts, ok_s)


@tpl("Y03", "Число запусков догрузки", "Пайплайны", ["data"], "вычисление", 1.2, 0.0, ["Airflow"])
def _(r):
    h = pick(r, [1, 2, 3, 4, 6, 8, 12, 24])
    d = 2 + int(r.random() * 9)
    month = pick(r, ["марта", "апреля", "мая", "июня", "сентября"])
    dag = pick(r, ["load_orders", "sync_payments", "build_marts", "import_events"])
    ok = d * 24 // h
    opts, ok_s = num_opts(r, ok, [(d - 1) * 24 // h, (d + 1) * 24 // h, d, ok + 1], lo=1)
    q = (f"DAG {dag} запускается каждые {h}{NB}ч, и каждый запуск обрабатывает ровно свой интервал в {h}{NB}ч. "
         f"Нужно догрузить (backfill) данные с 00:00 1 {month} по 24:00 {d} {month}. Сколько запусков выполнит догрузка?")
    return _mc(q, opts, ok_s)


@tpl("Y04", "Строки после LEFT JOIN", "Моделирование данных", ["data"], "вычисление", 1.3, 0.8, ["SQL"])
def _(r):
    n = 4 + int(r.random() * 3)
    active = r.sample(range(1, n + 1), n - 1 - int(r.random() * 2))
    orders = sorted(pick(r, active) for _ in range(5 + int(r.random() * 4)))
    ok = sum(max(1, orders.count(c)) for c in range(1, n + 1))
    opts, ok_s = num_opts(r, ok, [len(orders), n, ok + 1, len(orders) + 1], lo=1)
    q = (f"Таблица customers: id = {', '.join(map(str, range(1, n + 1)))}.\n"
         f"Таблица orders, колонка customer_id: {', '.join(map(str, orders))}.\n"
         "Что вернёт SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON o.customer_id = c.id?")
    return _mc(q, opts, ok_s)


CHARTS = ["Линейный график", "Диаграмма рассеяния", "Гистограмма", "Столбчатая диаграмма", "Ящик с усами"]


@tpl("Y05", "Тип графика под вопрос", "Визуализация", ["data"], "выбор", 0.9, -0.3)
def _(r):
    what = pick(r, ["заказов", "платежей", "поездок", "бронирований", "посылок"])
    q, ok = pick(r, [
        (f"Показать, как менялось число {what} по дням за последний год.", "Линейный график"),
        (f"Проверить, связаны ли сумма и время обработки у 5000 {what}: каждая точка — одна запись.", "Диаграмма рассеяния"),
        (f"Показать распределение суммы {what}: где основная масса значений и есть ли длинный хвост.", "Гистограмма"),
        (f"Сравнить число {what} за месяц в пяти регионах.", "Столбчатая диаграмма"),
        (f"Сравнить медиану, разброс и выбросы времени обработки {what} в четырёх городах на одном графике.", "Ящик с усами"),
    ])
    return _mc(f"{q} Какой тип графика подходит лучше всего?", options(ok, CHARTS, r, sample=True), ok)


# ── ML-инженер ─────────────────────────────────────────────────────────

@tpl("Y06", "Скалярное произведение", "Математика", ["ml"], "вычисление", 0.9, -1.0)
def _(r):
    u = [r.choice([x for x in range(-5, 6) if x]) for _ in range(3)]
    v = [r.choice([x for x in range(-5, 6) if x]) for _ in range(3)]
    ok = sum(a * b for a, b in zip(u, v))
    near = [sum(u) + sum(v), sum(abs(a * b) for a, b in zip(u, v)), -ok, ok + 1]
    opts, ok_s = num_opts(r, ok, near, lo=None, fmt=_minus)
    return _mc(f"Векторы u = ({'; '.join(map(_minus, u))}) и v = ({'; '.join(map(_minus, v))}).\n"
               "Чему равно скалярное произведение u · v?", opts, ok_s)


@tpl("Y07", "Точность и полнота", "Классический ML", ["ml"], "вычисление", 1.1, 0.3, ["scikit-learn"])
def _(r):
    task = pick(r, ["антифрода", "спам-фильтра", "оттока клиентов", "поиска брака"])
    tp = 20 + int(r.random() * 70)
    fp = 3 + int(r.random() * 28)
    fn = pick(r, [x for x in range(3, 31) if x != fp])
    prec, rec = _rnd(_F(100 * tp, tp + fp)), _rnd(_F(100 * tp, tp + fn))
    name, ok, other = pick(r, [("точность (precision)", prec, rec), ("полнота (recall)", rec, prec)])
    near = [other, _rnd(_F(100 * tp, tp + fp + fn)), _rnd(_F(200 * tp, 2 * tp + fp + fn))]
    opts, ok_s = num_opts(r, ok, near, lo=1, spread=5, fmt=_pct)
    return _mc(f"Модель {task} на тесте: TP = {tp}, FP = {fp}, FN = {fn}. Какова её {name}? Округлите до процента.", opts, ok_s)


@tpl("Y08", "Параметры свёрточного слоя", "Глубокое обучение", ["ml"], "вычисление", 1.2, 1.0, ["PyTorch"])
def _(r):
    c_in = pick(r, [1, 3, 8, 16, 32])
    c_out = pick(r, [8, 16, 32, 64])
    k = pick(r, [3, 5, 7])
    side = pick(r, [28, 32, 64, 128, 224])
    ok = c_out * (c_in * k * k + 1)
    near = [c_out * c_in * k * k, c_out * (c_in * k + 1), (c_out + 1) * c_in * k * k, c_out * (k * k + 1)]
    opts, ok_s = num_opts(r, ok, near, lo=1)
    q = (f"Слой nn.Conv2d(in_channels={c_in}, out_channels={c_out}, kernel_size={k}, bias=True) "
         f"применяют к изображениям {side}×{side}. Сколько у слоя обучаемых параметров?")
    return _mc(q, opts, ok_s)


@tpl("Y09", "Сглаженное target-кодирование", "Данные", ["ml"], "вычисление", 1.3, 1.5)
def _(r):
    feat, val = pick(r, [("город", "Казань"), ("модель телефона", "X12"), ("канал привлечения", "Реферал"), ("тариф", "Базовый")])
    n = 10 + int(r.random() * 51)
    pos = 1 + int(r.random() * (n - 1))
    prior = pick(r, [10, 20, 25, 40])
    m = pick(r, [5, 10, 20])
    ok = _rnd(_F(100 * pos + m * prior, n + m))
    near = [_rnd(_F(100 * pos, n)), prior, _rnd(_F(100 * (pos + m), n + m)), _rnd(_F(100 * pos + prior, n + 1))]
    opts, ok_s = num_opts(r, ok, near, lo=0, fmt=_pct)
    q = (f"Признак «{feat}» кодируют средним таргетом со сглаживанием: (число единиц + m · p) / (n + m), "
         f"где p — доля класса 1 по всей выборке, m = {m}. У значения «{val}» n = {n} объектов, из них {pos} с классом 1; "
         f"p = {prior}{NB}%. Каково закодированное значение? Округлите до процента.")
    return _mc(q, opts, ok_s)


@tpl("Y10", "Экземпляры сервиса модели", "Продакшен ML", ["ml"], "вычисление", 1.4, 2.0, ["Triton", "Docker"])
def _(r):
    b = pick(r, [8, 16, 32])
    f = pick(r, [20, 40, 60])
    g = pick(r, [1, 2, 3])
    load = pick(r, [1200, 1500, 2000, 2500, 3000, 4000, 5000])
    num, den = load * (f + g * b), 1000 * b
    ok = -(-num // den)
    near = [max(1, num // den), -(-load * g // 1000), -(-load * (f + g) // 1000), ok + 1]
    opts, ok_s = num_opts(r, ok, near, lo=1, spread=3)
    q = (f"Модель отвечает батчами по {b} запросов. Батч обрабатывается за {f} + {g}·B{NB}мс, где B — размер батча; "
         f"батчи идут подряд без простоя и всегда полные. Пиковая нагрузка — {load} запросов в секунду. "
         "Сколько экземпляров сервиса нужно как минимум?")
    return _mc(q, opts, ok_s)
