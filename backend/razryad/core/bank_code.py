"""Задания с кодом: кандидат пишет функцию на Python, сервер запускает её в песочнице на скрытых тестах (core/sandbox.py).
Условие и тесты собираются из зерна, эталон считается кодом здесь же; тесты клиенту не уходят (bank.public)."""
import operator

from .bank import pick, tpl


def _code(q: str, fn: str, tests: list) -> dict:
    return {"q": q, "open": True, "code": True, "sandbox": {"fn": fn, "tests": tests},
            "rubric": ["решение проходит скрытые тесты"], "keys": [[fn]]}


@tpl("C01", "Функция: счёт по условию", "Алгоритмы", ["backend", "data"], "код", 1.2, -0.4, ["Python"])
def _(r):
    op, word = pick(r, [(operator.gt, "больше"), (operator.lt, "меньше"), (operator.ge, "не меньше"), (operator.le, "не больше")])
    def ref(xs, k):
        return sum(1 for x in xs if op(x, k))
    tests = []
    for _ in range(8):
        xs = [r.randint(-20, 40) for _ in range(r.randint(0, 12))]
        k = r.randint(-5, 25)
        tests.append([[xs, k], ref(xs, k)])
    q = (f"Напишите на Python функцию solve(xs, k): она получает список целых чисел xs и число k "
         f"и возвращает, сколько элементов xs {word} k.\n\nПример: solve([1, 5, 3], 2) → {ref([1, 5, 3], 2)}.\n"
         "Решение проверят на скрытых тестах в песочнице.")
    return _code(q, "solve", tests)


@tpl("C02", "Функция: частые слова", "Структуры данных", ["backend", "data", "ml"], "код", 1.3, 0.6, ["Python"])
def _(r):
    k = r.randint(1, 3)
    def ref(words, k):
        cnt = {}
        for w in words:
            cnt[w] = cnt.get(w, 0) + 1
        return [w for w, _ in sorted(cnt.items(), key=lambda p: (-p[1], p[0]))[:k]]
    vocab = pick(r, [["api", "db", "cache", "queue", "log"], ["кот", "дом", "лес", "сад", "мир"], ["red", "green", "blue", "gray", "pink"]])
    tests = []
    for _ in range(8):
        words = [r.choice(vocab) for _ in range(r.randint(0, 15))]
        tests.append([[words, k], ref(words, k)])
    ex = [vocab[0], vocab[1], vocab[0], vocab[2], vocab[1], vocab[0]]
    q = (f"Напишите на Python функцию top_words(words, k): по списку слов верните {k} самых частых, "
         "по убыванию частоты, при равной частоте — по алфавиту. Слов меньше k — верните сколько есть.\n\n"
         f"Пример: top_words({ex}, {k}) → {ref(ex, k)}.\nРешение проверят на скрытых тестах в песочнице.")
    return _code(q, "top_words", tests)


@tpl("C03", "Функция: слияние интервалов", "Алгоритмы", ["backend", "devops", "data"], "код", 1.4, 1.6, ["Python"])
def _(r):
    def ref(iv):
        out = []
        for a, b in sorted(iv):
            if out and a <= out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out
    what = pick(r, ["окна обслуживания серверов", "занятые слоты переговорки", "периоды недоступности сервиса"])
    tests = []
    for _ in range(8):
        iv = []
        for _ in range(r.randint(0, 7)):
            a = r.randint(0, 30)
            iv.append([a, a + r.randint(0, 8)])
        tests.append([[iv], ref(iv)])
    q = (f"Даны {what} — список отрезков [начало, конец]. Напишите на Python функцию merge(iv), "
         "которая сливает пересекающиеся и касающиеся отрезки и возвращает список отрезков по возрастанию начала.\n\n"
         "Пример: merge([[1, 3], [2, 6], [8, 10]]) → [[1, 6], [8, 10]].\nРешение проверят на скрытых тестах в песочнице.")
    return _code(q, "merge", tests)
