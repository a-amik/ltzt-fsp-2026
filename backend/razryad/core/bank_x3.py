"""Дополнительные шаблоны банка, часть 3. Регистрируются тем же декоратором tpl из bank.py."""
import math as _math
from itertools import pairwise

from .bank import NB, _mc, num_opts, options, pick, plural, times, tpl

OPS = ["devops"]
BE = ["backend"]


def _perm(d: int) -> str:
    return ("r" if d & 4 else "-") + ("w" if d & 2 else "-") + ("x" if d & 1 else "-")


@tpl("Z01", "Права доступа в Linux", "Linux", OPS, "вычисление", 0.9, -1.5, ["Linux"])
def _(r):
    u, g, o = pick(r, [7, 6]), pick(r, [5, 4, 6, 7, 0]), pick(r, [0, 4, 5, 1])
    s = _perm(u) + _perm(g) + _perm(o)
    f = pick(r, ["deploy.sh", "backup.sh", "app.conf", "id_rsa", "run.py"])
    ok = f"{u}{g}{o}"
    ds = [f"{u}{o}{g}", f"{g}{u}{o}", f"{7 - u}{7 - g}{7 - o}", f"{u}{g}{(o + 1) % 8}"]
    gen = lambda r: f"{pick(r, [4, 5, 6, 7])}{pick(r, range(8))}{pick(r, range(8))}"
    return _mc(f"ls -l показывает у файла {f} права -{s}. Какое восьмеричное число задаёт эти права в chmod?",
               options(ok, ds, r, gen=gen), ok)


@tpl("Z02", "Адреса в подсети", "Сети", OPS, "вычисление", 1.0, -0.8, ["Linux"])
def _(r):
    p = pick(r, [22, 23, 24, 25, 26, 27, 28, 29])
    net = f"10.{int(r.random() * 250)}.{4 * int(r.random() * 60)}.0"
    total = 2 ** (32 - p)
    ok = total - 2
    opts, ok_s = num_opts(r, ok, [total, total - 1, total // 2 - 2, total * 2 - 2])
    return _mc(f"Подсеть {net}/{p}. Сколько адресов в ней можно назначить хостам (без адреса сети и широковещательного)?", opts, ok_s)


@tpl("Z03", "Поды на узле", "Контейнеры", OPS, "вычисление", 1.1, -0.2, ["Kubernetes"])
def _(r):
    cpu = pick(r, [3800, 3900, 7800, 7600, 15800])
    mem = pick(r, [14, 15, 30, 28, 60])
    rc = pick(r, [250, 300, 400, 500, 600])
    rm = pick(r, [1, 2, 3])
    ok = min(cpu // rc, mem // rm)
    opts, ok_s = num_opts(r, ok, [cpu // rc, mem // rm, _math.ceil(cpu / rc), ok + 1], lo=1)
    return _mc(f"У узла Kubernetes доступно для подов {cpu}m CPU и {mem}{NB}ГиБ памяти. Каждый под запрашивает "
               f"requests: cpu {rc}m, memory {rm}Gi. Других подов на узле нет. Сколько таких подов планировщик разместит на узле?",
               opts, ok_s)


@tpl("Z04", "Бюджет ошибок", "Наблюдаемость", OPS, "вычисление", 1.2, 0.4, ["Prometheus"])
def _(r):
    slo, days = pick(r, [("99,9", 0.999), ("99,5", 0.995), ("99,95", 0.9995), ("99", 0.99)]), pick(r, [28, 30])
    budget = round(days * 24 * 60 * (1 - slo[1]))
    spent = int(budget * (0.2 + 0.6 * r.random()))
    ok = budget - spent
    opts, ok_s = num_opts(r, ok, [budget, spent, budget + spent, round(days * 24 * 60 * (1 - slo[1]) / 10)], spread=7)
    return _mc(f"SLO доступности сервиса — {slo[0]}{NB}% за скользящие {days}{NB}дней. В этом окне сервис уже был недоступен "
               f"{spent}{NB}мин. Сколько минут недоступности ещё осталось в бюджете ошибок (с округлением до минуты)?", opts, ok_s)


@tpl("Z05", "Счётчик со сбросом", "Наблюдаемость", OPS, "вычисление", 1.3, 1.2, ["Prometheus"])
def _(r):
    n = 5
    vals, v = [], 1000 + int(r.random() * 4000)
    k = 2 + int(r.random() * 2)  # перед k-м замером процесс перезапустился
    for i in range(n):
        if i == k:
            v = 10 + int(r.random() * 200)
        elif i:
            v += 50 + int(r.random() * 400)
        vals.append(v)
    ok = sum((b - a) if b >= a else b for a, b in pairwise(vals))
    naive = vals[-1] - vals[0]
    opts, ok_s = num_opts(r, ok, [abs(naive), vals[k - 1] - vals[0], ok - vals[k], vals[-1] - vals[k]], lo=1, spread=9)
    return _mc(f"Счётчик http_requests_total снят пять раз подряд: {', '.join(map(str, vals))}. Между замерами процесс "
               f"один раз перезапустился, и счётчик начал с нуля. Сколько запросов обработано между первым и последним замером "
               f"(как считает increase() без экстраполяции)?", opts, ok_s)


@tpl("Z06", "Сдвиг индексов count", "Инфраструктура как код", OPS, "вычисление", 1.4, 2.0, ["Terraform"])
def _(r):
    n = 4 + int(r.random() * 5)
    k = int(r.random() * (n - 1))
    pool = ["logs", "media", "backup", "assets", "reports", "dumps", "cache", "exports", "tmp"]
    r.shuffle(pool)
    names = pool[:n]
    ok = n - k
    opts, ok_s = num_opts(r, ok, [1, n - k - 1, n, k + 1], lo=1)
    return _mc(f"Бакеты созданы так: count = length(var.names), bucket = var.names[count.index]; var.names = "
               f"[{', '.join(chr(34) + x + chr(34) for x in names)}]. Смена имени бакета пересоздаёт ресурс. Из списка убрали "
               f"«{names[k]}», порядок остальных не меняли. Сколько бакетов уничтожит terraform apply?", opts, ok_s, code=False)


@tpl("Z07", "Смещение страницы", "Базы данных", BE, "вычисление", 0.9, -1.0, ["PostgreSQL", "SQL"])
def _(r):
    size, page = pick(r, [10, 20, 25, 50]), 2 + int(r.random() * 30)
    ok = (page - 1) * size
    opts, ok_s = num_opts(r, ok, [page * size, (page - 2) * size, ok + 1, ok - 1])
    return _mc(f"Список выводится по {size} строк на странице, страницы нумеруются с 1. Какое значение OFFSET нужно в запросе "
               f"SELECT … ORDER BY id LIMIT {size} OFFSET ?, чтобы получить страницу {page}?", opts, ok_s)


@tpl("Z08", "Экспоненциальная задержка", "Сети и API", BE, "вычисление", 1.1, 0.2, ["REST"])
def _(r):
    d, f, n = pick(r, [100, 200, 250, 500]), pick(r, [2, 3]), 3 + int(r.random() * 3)
    ok = sum(d * f ** i for i in range(n - 1))
    opts, ok_s = num_opts(r, ok, [sum(d * f ** i for i in range(n)), d * f ** (n - 2), d * f ** (n - 1), d * (n - 1)],
                          spread=3, fmt=lambda x: f"{x}{NB}мс")
    return _mc(f"Клиент повторяет неудачный запрос: перед первым повтором ждёт {d}{NB}мс, перед каждым следующим — "
               f"{times(f)} дольше. Всего {n} {plural(n, 'попытка', 'попытки', 'попыток')}, включая первую. Сколько клиент суммарно "
               f"прождал до начала последней попытки (без учёта времени самих запросов)?", opts, ok_s)


@tpl("Z09", "Кворум реплик", "Базы данных", BE, "вычисление", 1.2, 0.8, ["Cassandra"])
def _(r):
    n = pick(r, [3, 5, 7, 9])
    w = 1 + int(r.random() * n)
    ok = n - w + 1
    opts, ok_s = num_opts(r, ok, [n - w, n // 2 + 1, n, w], lo=1, spread=4)
    return _mc(f"Данные хранятся на {n} репликах. Запись подтверждается, когда её приняли W = {w}. Какое наименьшее число "
               f"реплик R нужно опрашивать при чтении, чтобы чтение гарантированно увидело последнюю подтверждённую запись?",
               opts, ok_s)


@tpl("Z10", "Размер пула соединений", "Сети и API", BE, "вычисление", 1.4, 1.5, ["PostgreSQL"])
def _(r):
    rps, lat = pick(r, [200, 400, 600, 800, 1200, 1500]), pick(r, [15, 20, 30, 45, 60, 80])
    ok = _math.ceil(rps * lat / 1000)
    opts, ok_s = num_opts(r, ok, [_math.ceil(rps / lat), rps * lat // 100, ok * 2, _math.ceil(1000 / lat)], lo=1, spread=3)
    return _mc(f"Сервис должен выдерживать {rps} запросов в секунду, каждый держит соединение с базой {lat}{NB}мс. Запросы "
               f"приходят равномерно. Какой наименьший размер пула соединений это обеспечит (по закону Литтла, с округлением вверх)?",
               opts, ok_s)
