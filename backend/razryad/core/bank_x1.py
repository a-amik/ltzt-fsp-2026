"""Дополнительные шаблоны банка, часть 1. Регистрируются тем же декоратором tpl из bank.py."""
from .bank import NB, _mc, num_opts, options, pick, tpl  # noqa: F401

import math
from collections import OrderedDict

_RES = ["orders", "payments", "messages", "trips", "bookings", "invoices", "parcels"]


@tpl("X01", "Смещение при постраничной выдаче", "Базы данных", ["backend"], "вычисление", 0.9, -1.5, ["SQL", "PostgreSQL"])
def _(r):
    t = pick(r, _RES)
    k = pick(r, [10, 20, 25, 50])
    p = 2 + int(r.random() * 9)
    ok = (p - 1) * k
    opts, ok_s = num_opts(r, ok, [p * k, ok + 1, ok - 1, p * k - 1], lo=0)
    return _mc(f"Выдача {t} идёт страницами по {k} записей, страницы нумеруются с 1.\n"
               f"Какое значение OFFSET нужно в запросе SELECT * FROM {t} ORDER BY id LIMIT {k} OFFSET ?, чтобы получить страницу {p}?",
               opts, ok_s, code=True)


@tpl("X02", "Экспоненциальная задержка повторов", "Сети и API", ["backend"], "вычисление", 1.1, -0.3, ["REST"])
def _(r):
    d = pick(r, [50, 100, 200, 250, 500])
    n = 3 + int(r.random() * 3)
    ok = 2 ** n - 1  # в долях d
    opts, ok_s = num_opts(r, ok, [2 ** n, 2 ** (n - 1) - 1, n, 2 ** (n + 1) - 1], lo=1, spread=3, fmt=lambda x: f"{x * d}{NB}мс")
    return _mc(f"Клиент повторяет неудачный запрос до {n} раз. Перед первым повтором ждёт {d}{NB}мс, перед каждым следующим — вдвое дольше предыдущего. "
               f"Сколько всего клиент прождёт, если все повторы неудачны? Время самих запросов не считаем.", opts, ok_s)


@tpl("X03", "Пул соединений", "Конкурентность", ["backend"], "вычисление", 1.2, 0.8, ["PostgreSQL"])
def _(r):
    p = pick(r, [4, 5, 8, 10])
    n = p * (2 + int(r.random() * 4)) + 1 + int(r.random() * (p - 1))
    t = pick(r, [20, 30, 40, 50])
    ok = math.ceil(n / p)  # в долях t
    opts, ok_s = num_opts(r, ok, [n // p, n, ok + 1, 1], lo=1, spread=3, fmt=lambda x: f"{x * t}{NB}мс")
    return _mc(f"У сервиса пул из {p} соединений с базой. Одновременно пришло {n} запросов, каждый держит соединение ровно {t}{NB}мс, "
               f"остальные ждут в очереди свободного соединения. Через сколько завершится последний запрос?", opts, ok_s)


@tpl("X04", "Кворум реплик", "Проектирование", ["backend"], "вычисление", 1.3, 1.6, ["Cassandra"])
def _(r):
    n = pick(r, [3, 5, 7, 9])
    w = 1 + int(r.random() * n)
    ok = n - w + 1
    opts, ok_s = num_opts(r, ok, [n - w, n // 2 + 1, w, n - w + 2], lo=1, spread=4)
    return _mc(f"Данные хранятся на {n} репликах. Запись подтверждается, когда её приняли W = {w} из них. "
               f"Каким должно быть наименьшее R — число реплик, опрашиваемых при чтении, — чтобы чтение гарантированно видело последнюю подтверждённую запись?",
               opts, ok_s)


@tpl("X05", "Фильтрация массива", "Язык и типы", ["frontend"], "вычисление", 1.0, -1.0, ["TypeScript"])
def _(r):
    xs = [1 + int(r.random() * 30) for _ in range(7)]
    k = pick(r, xs)
    op = pick(r, [">", ">=", "<"])
    f = {">": lambda x: x > k, ">=": lambda x: x >= k, "<": lambda x: x < k}[op]
    ok = sum(1 for x in xs if f(x))
    opts, ok_s = num_opts(r, ok, [ok + 1, ok - 1, len(xs) - ok], lo=0, spread=3)
    return _mc(f"Что выведет код?\n\nconst xs = [{', '.join(map(str, xs))}];\nconsole.log(xs.filter(x => x {op} {k}).length);", opts, ok_s, code=True)


@tpl("X06", "Debounce обработчика", "Рендеринг", ["frontend"], "вычисление", 1.2, 0.4, ["React", "TypeScript"])
def _(r):
    d = pick(r, [200, 300, 500])
    ts, t = [], 0
    for _ in range(6 + int(r.random() * 4)):
        ts.append(t)
        t += pick(r, [d // 4, d // 2, d - 50, d + 50, 2 * d])
    ok = 1 + sum(1 for a, b in zip(ts, ts[1:]) if b - a > d)
    opts, ok_s = num_opts(r, ok, [len(ts), ok + 1, ok - 1], lo=1, spread=3)
    return _mc(f"Поле поиска вызывает обработчик через debounce с задержкой {d}{NB}мс: вызов происходит, только если после нажатия {d}{NB}мс не было новых нажатий. "
               f"Нажатия пришли в моменты (мс): {', '.join(map(str, ts))}. Сколько раз вызовется обработчик?", opts, ok_s)


@tpl("X07", "Запросы пачками", "Сети и API", ["frontend"], "вычисление", 1.4, 2.0, ["TypeScript", "REST"])
def _(r):
    k = pick(r, [2, 3])
    ds = [pick(r, [100, 150, 200, 250, 300, 400]) for _ in range(k * (2 + int(r.random() * 2)))]
    ok = sum(max(ds[i:i + k]) for i in range(0, len(ds), k)) // 50  # в долях 50 мс
    opts, ok_s = num_opts(r, ok, [sum(ds) // 50, max(ds) // 50, round(sum(ds) / k / 50), ok + 1], lo=1, spread=3, fmt=lambda x: f"{x * 50}{NB}мс")
    return _mc(f"Функция fetchOne(i) отвечает за ms[i] миллисекунд, ms = [{', '.join(map(str, ds))}]. Сколько займёт код? Прочими задержками пренебрегаем.\n\n"
               f"for (let i = 0; i < ms.length; i += {k}) {{\n  await Promise.all(ms.slice(i, i + {k}).map((_, j) => fetchOne(i + j)));\n}}",
               opts, ok_s, code=True)


_DENS = [(160, "mdpi", 1), (240, "hdpi", 1.5), (320, "xhdpi", 2), (480, "xxhdpi", 3), (640, "xxxhdpi", 4)]


@tpl("X08", "Плотность экрана", "Платформа", ["mobile"], "вычисление", 1.0, -0.6, ["Kotlin"])
def _(r):
    dpi, name, m = pick(r, _DENS)
    dp = pick(r, [8, 12, 16, 24, 32, 48, 56, 64])
    ok = int(dp * m)
    opts, ok_s = num_opts(r, ok, [dp, int(dp * dpi), dp * 2 if m != 2 else dp * 3, int(dp * m) + dp], lo=1, spread=4, fmt=lambda x: f"{x}{NB}px")
    return _mc(f"Отступ в разметке Android — {dp}{NB}dp. Сколько это физических пикселей на экране {name} ({dpi}{NB}dpi)?", opts, ok_s)


@tpl("X09", "Корутины и ожидание", "Конкурентность", ["mobile"], "вычисление", 1.3, 1.2, ["Kotlin"])
def _(r):
    a = pick(r, [300, 400, 500, 600])
    b = pick(r, [700, 800, 900, 1000])
    kind = pick(r, ["par", "seq", "fake"])
    if kind == "par":
        body = f"val x = async {{ load({a}) }}\n    val y = async {{ load({b}) }}\n    println(x.await() + y.await())"
        ok = max(a, b)
    elif kind == "seq":
        body = f"val x = load({a})\n    val y = load({b})\n    println(x + y)"
        ok = a + b
    else:
        body = f"val x = async {{ load({a}) }}.await()\n    val y = async {{ load({b}) }}.await()\n    println(x + y)"
        ok = a + b
    near = [(a + b) // 100, max(a, b) // 100, min(a, b) // 100]
    opts, ok_s = num_opts(r, ok // 100, near, lo=1, spread=3, fmt=lambda x: f"{x * 100}{NB}мс")
    return _mc(f"suspend fun load(ms: Long): Int {{ delay(ms); return 1 }} — других задержек нет. Сколько примерно пройдёт до печати?\n\n"
               f"coroutineScope {{\n    {body}\n}}", opts, ok_s, code=True)


@tpl("X10", "Кэш картинок LRU", "Алгоритмы", ["mobile"], "вычисление", 1.1, 0.6)
def _(r):
    c = pick(r, [2, 3])
    keys = "ABCDE"[: c + 2]
    seq = [pick(r, keys) for _ in range(9)]
    cache, hits = OrderedDict(), 0
    for k in seq:
        if k in cache:
            hits += 1
            cache.move_to_end(k)
        else:
            cache[k] = 1
            if len(cache) > c:
                cache.popitem(last=False)
    fifo, fh = [], 0
    for k in seq:
        if k in fifo:
            fh += 1
        else:
            fifo.append(k)
            if len(fifo) > c:
                fifo.pop(0)
    opts, ok_s = num_opts(r, hits, [fh, hits + 1, hits - 1, len(seq) - hits], lo=0, spread=3)
    return _mc(f"Приложение держит в памяти кэш картинок на {c} {'картинки' if c < 5 else 'картинок'} с вытеснением давно не использованной (LRU). "
               f"Кэш пуст, экран запрашивает картинки по порядку: {', '.join(seq)}. Сколько запросов будет обслужено из кэша?", opts, ok_s)
