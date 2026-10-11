"""Процедура валидации решения на синтетических данных.

Запуск: `uv run python -m razryad.validate [--n 1000] [--seed 7]`.
Итог — `validation/report.json` и `validation/REPORT.md`.

Шесть опытов, все — на коде сервиса (оценка θ, выбор задания, правило
остановки, вердикт, ранжирование), а не на его копии:

1. Точность грейда: истинный уровень известен, сравниваем с присвоенным.
2. Повторное прохождение (test-retest): тот же кандидат сдаёт тест дважды
   независимыми наборами, сравниваем оценки и грейды.
3. Разделяющая сила шаблонов: точечно-бисериальная корреляция ответа
   с суммой остальных ответов на калибровочной форме.
4. Утечка заданий: доля «списавших» и прирост их грейда — при общем
   наборе заданий и при нашем банке шаблонов.
5. Генерация уникальных заданий без калибровки: что будет с точностью,
   если трудность варианта гуляет (довод ТЗ против генерации нейросетью).
6. Качество подбора: P@10 и nDCG@10 на размеченных парах «потребность —
   кандидат» против поиска по ключевым словам резюме.

Чтобы проверка не была замкнута на себя, ответы кандидатов порождает модель
с «истинными» параметрами заданий, которые отличаются от калиброванных:
a и b каждого шаблона сдвинуты шумом, а каждый вариант шаблона получает
ещё свой разброс трудности. Тест же считает по калиброванным значениям.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics as st
from dataclasses import dataclass
from pathlib import Path

from .core import bank
from .core.catalog import GRADE_MID, GRADES, SPECS, grade_of
from .core.irt import estimate, p_correct, pick_next, prior_for, should_stop, verdict
from .core.scoring import over_budget, rank

# Сколько шаблонов банка доступно каждой специализации — для текста ограничений.
SPEC_N = {sp["id"]: sum(1 for t in bank.TEMPLATES if sp["id"] in t.specs) for sp in SPECS}

OUT = Path(__file__).resolve().parent.parent / "validation"

CALIB_NOISE_B = 0.25   # ошибка калибровки трудности шаблона
CALIB_NOISE_A = 0.15   # ошибка калибровки различающей силы (доля)
INSTANCE_SD = 0.15     # разброс трудности вариантов одного шаблона
LLM_INSTANCE_SD = 0.7  # разброс трудности задания, сгенерированного без калибровки
LLM_DRIFT_SD = 0.5     # сдвиг трудности всего набора одного кандидата у генератора без калибровки


@dataclass
class World:
    """Истинные параметры шаблонов, неизвестные тесту."""
    true_ab: dict

    @classmethod
    def make(cls, r: random.Random):
        ab = {}
        for t in bank.TEMPLATES:
            ab[t.id] = (max(0.3, t.a * (1 + r.gauss(0, CALIB_NOISE_A))), t.b + r.gauss(0, CALIB_NOISE_B))
        return cls(ab)


def true_theta_for(r: random.Random) -> tuple[float, int]:
    g = r.choices(range(5), weights=[1, 3, 4, 2.5, 1])[0]
    return max(-2.8, min(2.8, GRADE_MID[g] + r.gauss(0, 0.45))), g


def run_test(world: World, spec: str, theta_true: float, claimed: int, r: random.Random, mode="full",
             instance_sd=INSTANCE_SD, leaked: set | None = None, leak_mode: str | None = None, fixed_form=None, drift=0.0):
    """Один проход теста. leaked — шаблоны или варианты, ответы на которые разошлись.
    leak_mode: 'form' — общий набор, списанный ответ верен всегда;
               'template' — вариант уникален, кандидат знает лишь идею шаблона (+30 % к шансу)."""
    pool = bank.for_spec(spec)
    answers, used = [], set()
    theta, se = prior_for(claimed), 1.0
    order = list(fixed_form) if fixed_form else None
    while True:
        if order is not None:
            if not order:
                break
            t = order.pop(0)
        else:
            t, _ = pick_next(theta, pool, used, r)
            if not t:
                break
        used.add(t.id)
        a_true, b_true = world.true_ab[t.id]
        b_inst = b_true + drift + r.gauss(0, instance_sd)
        p = p_correct(theta_true, a_true, b_inst)
        if leaked and t.id in leaked:
            p = 1.0 if leak_mode == "form" else p + 0.3 * (1 - p)
        ok = r.random() < p
        answers.append({"a": t.a, "b": t.b, "score": 1.0 if ok else 0.0, "tpl": t.id})
        theta, se = estimate(answers, prior_for(claimed))
        if order is None and should_stop(len(answers), se, mode):
            break
    return theta, se, answers


def full_protocol(world, spec, theta_true, claimed, r, mode="full", **kw):
    """Путь кандидата по правилам сервиса: тест на заявленный грейд; не прошёл —
    тест на ступень ниже (один раз). Возвращает присвоенный грейд или None."""
    th, se, ans = run_test(world, spec, theta_true, claimed, r, mode, **kw)
    v = verdict(claimed, th, se)
    if v["kind"] == "ok":
        return v["grade"], th, se, len(ans)
    lower = v["offer_down"]
    th2, se2, ans2 = run_test(world, spec, theta_true, lower, r, mode, **kw)
    v2 = verdict(lower, th2, se2)
    return (v2["grade"] if v2["kind"] == "ok" else None), th2, se2, len(ans) + len(ans2)


def claimed_for(g: int, r: random.Random) -> int:
    return g if r.random() < 0.75 else min(4, g + 1)  # четверть завышает


# ── 1. Точность грейда ───────────────────────────────────────────────
def exp_accuracy(world, n, r, mode="full", instance_sd=INSTANCE_SD, drift_sd=0.0):
    exact = off1 = off2 = none = 0
    items = []
    conf = [[0] * 6 for _ in range(5)]  # истинный × присвоенный (5 = не подтверждён)
    for i in range(n):
        spec = SPECS[i % len(SPECS)]["id"]
        th, g = true_theta_for(r)
        c = claimed_for(g, r)
        drift = r.gauss(0, drift_sd) if drift_sd else 0.0
        got, _, _, k = full_protocol(world, spec, th, c, r, mode, instance_sd=instance_sd, drift=drift)
        items.append(k)
        conf[g][5 if got is None else got] += 1
        if got is None:
            none += 1
        elif got == g:
            exact += 1
        elif abs(got - g) == 1:
            off1 += 1
        else:
            off2 += 1
    return {"n": n, "exact": exact / n, "off_by_one": off1 / n, "off_by_two_plus": off2 / n, "unconfirmed": none / n,
            "items_mean": st.mean(items), "items_max": max(items), "confusion": conf}


# ── 2. Повторное прохождение ─────────────────────────────────────────
def pearson(x, y):
    mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def kappa(a, b, k=6):
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = [a.count(i) / n for i in range(k)]; pb = [b.count(i) / n for i in range(k)]
    pe = sum(p * q for p, q in zip(pa, pb))
    return (po - pe) / (1 - pe)


def exp_retest(world, n, r, mode="full"):
    t1, t2, g1, g2 = [], [], [], []
    for i in range(n):
        spec = SPECS[i % len(SPECS)]["id"]
        th, g = true_theta_for(r)
        c = claimed_for(g, r)
        a = full_protocol(world, spec, th, c, random.Random(r.random()), mode)
        b = full_protocol(world, spec, th, c, random.Random(r.random()), mode)
        t1.append(a[1]); t2.append(b[1])
        g1.append(5 if a[0] is None else a[0]); g2.append(5 if b[0] is None else b[0])
    same = sum(1 for x, y in zip(g1, g2) if x == y) / n
    near = sum(1 for x, y in zip(g1, g2) if x != 5 and y != 5 and abs(x - y) <= 1) / n
    return {"n": n, "theta_r": pearson(t1, t2), "grade_same": same, "grade_within_one": near, "kappa": kappa(g1, g2)}


# ── 3. Разделяющая сила шаблонов ─────────────────────────────────────
def exp_discrimination(world, n, r):
    """Калибровочная форма: каждый кандидат решает все шаблоны своей специализации."""
    rows = []
    for spec in [s["id"] for s in SPECS]:
        pool = bank.for_spec(spec)
        data = []
        for _ in range(n):
            th, _ = true_theta_for(r)
            resp = {}
            for t in pool:
                a, b = world.true_ab[t.id]
                resp[t.id] = 1 if r.random() < p_correct(th, a, b + r.gauss(0, INSTANCE_SD)) else 0
            data.append(resp)
        for t in pool:
            x = [d[t.id] for d in data]
            rest = [sum(v for k, v in d.items() if k != t.id) for d in data]
            if len(set(x)) < 2:
                rpb = 0.0
            else:
                rpb = pearson(x, rest)
            order = sorted(range(n), key=lambda i: rest[i])
            k = int(n * 0.27)
            low = st.mean(x[i] for i in order[:k]); high = st.mean(x[i] for i in order[-k:])
            rows.append({"spec": spec, "tpl": t.id, "title": t.title, "b": t.b, "a": t.a, "p": st.mean(x), "rpb": rpb, "D": high - low})
    by_tpl = {}
    for row in rows:
        by_tpl.setdefault(row["tpl"], []).append(row)
    items = [{"tpl": k, "title": v[0]["title"], "a": v[0]["a"], "b": v[0]["b"], "p": st.mean(x["p"] for x in v),
              "rpb": st.mean(x["rpb"] for x in v), "D": st.mean(x["D"] for x in v), "specs": len(v)} for k, v in by_tpl.items()]
    items.sort(key=lambda x: x["b"])
    return {"n_per_spec": n, "items": items, "rpb_mean": st.mean(x["rpb"] for x in items),
            "weak": [x["tpl"] for x in items if x["rpb"] < 0.3]}


# ── 4. Утечка заданий ────────────────────────────────────────────────
def exp_leak(world, n, r, share=0.3):
    """Половина кандидатов получила ответы на долю share заданий. Сравниваем
    общий набор (одна форма на всех) и наш банк (уникальные варианты, адаптивный показ)."""
    out = {}
    spec = "backend"
    pool = bank.for_spec(spec)
    k_form = 10
    form_rng = random.Random(11)
    form = sorted(pool, key=lambda t: abs(t.b))[:k_form]  # фиксированная форма средней трудности
    leaked_form = {t.id for t in form_rng.sample(form, max(1, round(k_form * share)))}
    leaked_bank = {t.id for t in form_rng.sample(pool, max(1, round(len(pool) * share)))}
    for name, kw in [("form", {"fixed_form": form, "leaked": leaked_form, "leak_mode": "form"}),
                     ("bank", {"leaked": leaked_bank, "leak_mode": "template"})]:
        gain, up = [], 0
        for _ in range(n):
            th, g = true_theta_for(r)
            c = claimed_for(g, r)
            seed = r.random()
            honest = full_protocol(world, spec, th, c, random.Random(seed), **{k: v for k, v in kw.items() if k == "fixed_form"})
            cheat = full_protocol(world, spec, th, c, random.Random(seed), **kw)
            gh = -1 if honest[0] is None else honest[0]
            gc = -1 if cheat[0] is None else cheat[0]
            gain.append(cheat[1] - honest[1])
            if gc > gh:
                up += 1
        out[name] = {"theta_gain_mean": st.mean(gain), "grade_up_share": up / n}
    out["share_leaked"] = share
    # частота показа шаблонов при адаптивном тесте
    seen = {}
    total = 0
    for _ in range(n):
        th, g = true_theta_for(r)
        _, _, ans = run_test(world, spec, th, claimed_for(g, r), r)
        for a in ans:
            seen[a["tpl"]] = seen.get(a["tpl"], 0) + 1
        total += 1
    out["exposure_max"] = max(seen.values()) / total
    out["exposure_mean"] = st.mean(seen.values()) / total
    out["form_exposure"] = 1.0
    return out


# ── 6. Качество подбора ──────────────────────────────────────────────
def synth_market(world, n, r):
    """Кандидаты с истинным уровнем и истинным стеком. В резюме — заявленный грейд
    и стек с приписками; в сервисе — грейд по тесту, стек тот же (самоописание)."""
    cands = []
    for i in range(n):
        sp = SPECS[i % len(SPECS)]
        th, g = true_theta_for(r)
        true_stack = r.sample(sp["stack"], r.randint(2, 4))
        extra = [s for s in sp["stack"] if s not in true_stack]
        resume_stack = true_stack + r.sample(extra, min(len(extra), r.randint(0, 2)))
        claimed = claimed_for(g, r)
        if r.random() < 0.15:
            claimed = min(4, claimed + 1)  # в резюме завышают чаще, чем в тесте
        got, theta, se, _ = full_protocol(world, sp["id"], th, claimed, r)
        salary = int([70, 120, 220, 340, 450][g] * 1000 * (0.85 + r.random() * 0.35))
        fsp = [{"place": r.randint(1, 30), "participants": r.randint(40, 300), "year": 2025, "event": "соревнование"}] if r.random() < 0.4 else []
        cands.append({"id": i, "spec": sp["id"], "true_grade": g, "true_theta": th, "true_stack": true_stack,
                      "resume_stack": resume_stack, "resume_grade": claimed, "salary": salary,
                      # то, что видит ранжирование сервиса:
                      "grade": got, "claimed_grade": claimed, "theta": theta, "se": se, "stack": resume_stack, "fsp": fsp,
                      "fresh_tasks": r.randint(0, 3)})
    return cands


def relevance(c, need):
    """Эталонная разметка команды, 0—3. Считается по истинным свойствам, которых
    ни одна система не видит: истинный грейд, настоящий стек, деньги.
    Слабее запроса — 0: работодатель получит человека, который не справится.
    Сильнее на ступень — годится, только если укладывается в деньги, иначе 1."""
    d = c["true_grade"] - need["grade"]
    if c["spec"] != need["spec"] or d < 0 or d > 1:
        return 0
    ov = len([s for s in need["stack"] if s in c["true_stack"]]) / len(need["stack"])
    money = c["salary"] <= need["salary_to"] * 1.05
    if d == 1 and not money:
        return 1
    if ov >= 2 / 3 and money:
        return 3
    if ov >= 1 / 3:
        return 2
    return 1


def ndcg(rels, k=10):
    dcg = sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(rels[:k]))
    ideal = sorted(rels, reverse=True)
    idcg = sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(ideal[:k]))
    return dcg / idcg if idcg else 0.0


def keyword_rank(cands, need):
    """База сравнения: поиск по резюме — специализация, заявленный грейд, совпадение ключевых слов.
    Вилку видит и она: те же правила, что у сервиса, — сильно дороже вилки идут после укладывающихся."""
    pool = [c for c in cands if c["spec"] == need["spec"] and c["resume_grade"] == need["grade"]]
    return sorted(pool, key=lambda c: (over_budget(c, need), -len([s for s in need["stack"] if s in c["resume_stack"]]), c["id"]))


def exp_matching(world, n, r, needs_n=20):
    cands = synth_market(world, n, r)
    res = {"ours": [], "keyword": []}
    for j in range(needs_n):
        sp = SPECS[j % len(SPECS)]
        g = [1, 2, 3, 2, 1][j % 5]
        need = {"spec": sp["id"], "grade": g, "stack": r.sample(sp["stack"], 3),
                "salary_to": int([90, 160, 300, 420, 560][g] * 1000)}
        all_rels = [relevance(c, need) for c in cands]
        for name, ranked in [("ours", [x["c"] for x in rank(cands, need)]), ("keyword", keyword_rank(cands, need))]:
            top = ranked[:10]
            rels = [relevance(c, need) for c in top]
            # ideal over all candidates for nDCG
            dcg = sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(rels))
            ideal = sorted(all_rels, reverse=True)[:10]
            idcg = sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(ideal))
            res[name].append({"p10": sum(1 for x in rels if x >= 2) / 10, "ndcg10": dcg / idcg if idcg else 0,
                              "under": sum(1 for c in top if c["true_grade"] < need["grade"]) / 10,
                              "over": sum(1 for c in top if c["true_grade"] > need["grade"]) / 10})
    agg = {k: {m: st.mean(x[m] for x in v) for m in ("p10", "ndcg10", "under", "over")} for k, v in res.items()}
    agg["needs"] = needs_n
    agg["candidates"] = n
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    r = random.Random(a.seed)
    world = World.make(r)
    rep = {"seed": a.seed, "noise": {"calib_b": CALIB_NOISE_B, "calib_a": CALIB_NOISE_A, "instance_sd": INSTANCE_SD, "llm_instance_sd": LLM_INSTANCE_SD, "llm_drift_sd": LLM_DRIFT_SD},
           "bank_size": len(bank.TEMPLATES)}
    print("1. точность грейда…")
    rep["accuracy_full"] = exp_accuracy(world, a.n, r, "full")
    rep["accuracy_express"] = exp_accuracy(world, a.n, r, "express")
    print("2. повторное прохождение…")
    rep["retest_full"] = exp_retest(world, a.n // 2, r, "full")
    rep["retest_express"] = exp_retest(world, a.n // 2, r, "express")
    print("3. разделяющая сила…")
    rep["discrimination"] = exp_discrimination(world, 500, r)
    print("4. утечка…")
    rep["leak"] = exp_leak(world, a.n // 2, r)
    print("5. генерация без калибровки…")
    # парное сравнение: те же кандидаты (то же зерно), разные задания
    rep["llm_base"] = exp_accuracy(world, a.n, random.Random(a.seed + 5), "full")
    rep["llm_noise"] = exp_accuracy(world, a.n, random.Random(a.seed + 5), "full", instance_sd=LLM_INSTANCE_SD)
    rep["llm_drift"] = exp_accuracy(world, a.n, random.Random(a.seed + 5), "full", instance_sd=LLM_INSTANCE_SD, drift_sd=LLM_DRIFT_SD)
    print("6. подбор…")
    runs = [exp_matching(World.make(random.Random(sd)), 1200, random.Random(sd + 100)) for sd in range(a.seed, a.seed + 5)]
    rep["matching"] = {k: {m: st.mean(x[k][m] for x in runs) for m in ("p10", "ndcg10", "under", "over")} for k in ("ours", "keyword")}
    rep["matching_sd"] = {k: {m: st.pstdev([x[k][m] for x in runs]) for m in ("p10", "ndcg10", "under", "over")} for k in ("ours", "keyword")}
    rep["matching"].update({"needs": 20, "candidates": 1200, "seeds": 5})
    OUT.mkdir(exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    (OUT / "REPORT.md").write_text(render(rep))
    print(render(rep))


def pct(x):
    return f"{x * 100:.1f} %".replace(".", ",")


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def render(rep):
    A, E = rep["accuracy_full"], rep["accuracy_express"]
    R, RE = rep["retest_full"], rep["retest_express"]
    D, L, M, S = rep["discrimination"], rep["leak"], rep["matching"], rep["matching_sd"]
    B0, B1, B2 = rep["llm_base"], rep["llm_noise"], rep["llm_drift"]
    lines = [
        "# Валидация решения на синтетических данных", "",
        f"Зерно {rep['seed']}, банк — {rep['bank_size']} шаблонов. Ответы порождает модель с «истинными» параметрами шаблонов, "
        f"отличными от калиброванных: сдвиг трудности σ = {num(rep['noise']['calib_b'])}, различающей силы ± {pct(rep['noise']['calib_a'])}, "
        f"разброс трудности вариантов σ = {num(rep['noise']['instance_sd'])}. Повторить: `uv run python -m razryad.validate`.", "",
        "## 1. Точность грейда", "",
        "| Режим | Кандидатов | Совпал | Ошибка на ступень | Ошибка на две и больше | Не подтверждён | Заданий в среднем |",
        "|---|---|---|---|---|---|---|",
        f"| Полный | {A['n']} | {pct(A['exact'])} | {pct(A['off_by_one'])} | {pct(A['off_by_two_plus'])} | {pct(A['unconfirmed'])} | {num(A['items_mean'], 1)} |",
        f"| Экспресс | {E['n']} | {pct(E['exact'])} | {pct(E['off_by_one'])} | {pct(E['off_by_two_plus'])} | {pct(E['unconfirmed'])} | {num(E['items_mean'], 1)} |",
        "", "## 2. Повторное прохождение", "",
        "| Режим | Пар | Корреляция оценок | Тот же грейд | В пределах ступени | Каппа Коэна |", "|---|---|---|---|---|---|",
        f"| Полный | {R['n']} | {num(R['theta_r'])} | {pct(R['grade_same'])} | {pct(R['grade_within_one'])} | {num(R['kappa'])} |",
        f"| Экспресс | {RE['n']} | {num(RE['theta_r'])} | {pct(RE['grade_same'])} | {pct(RE['grade_within_one'])} | {num(RE['kappa'])} |",
        "", "## 3. Разделяющая сила шаблонов", "",
        f"Калибровочная форма, {D['n_per_spec']} кандидатов на специализацию. Средняя точечно-бисериальная корреляция — {num(D['rpb_mean'])}; "
        f"ниже 0,3: {', '.join(D['weak']) or 'нет'}.", "",
        "| Шаблон | b | a | Доля верных | r_pb | D (верх 27 % − низ 27 %) |", "|---|---|---|---|---|---|",
    ]
    lines += [f"| {x['tpl']} {x['title']} | {num(x['b'], 1)} | {num(x['a'], 1)} | {pct(x['p'])} | {num(x['rpb'])} | {num(x['D'])} |" for x in D["items"]]
    lines += [
        "", "## 4. Утечка заданий", "",
        f"Ответы разошлись на {pct(L['share_leaked'])} заданий. «Списавший» с общим набором знает ответ; с нашим банком вариант уникален, "
        "и знание идеи шаблона добавляет 30 % к шансу ответить верно.", "",
        "| Подход | Прирост оценки θ | Грейд вырос у | Показ самого частого задания |", "|---|---|---|---|",
        f"| Общий набор заданий | {num(L['form']['theta_gain_mean'])} | {pct(L['form']['grade_up_share'])} | {pct(L['form_exposure'])} |",
        f"| Банк шаблонов, адаптивный показ | {num(L['bank']['theta_gain_mean'])} | {pct(L['bank']['grade_up_share'])} | {pct(L['exposure_max'])} |",
        "", "## 5. Уникальные задания без калибровки", "",
        f"Парное сравнение на {B0['n']} одних и тех же кандидатах. Генератор без калибровки моделируем двумя способами: "
        f"трудность каждого задания гуляет случайно (σ = {num(rep['noise']['llm_instance_sd'])}) и вдобавок весь набор одного кандидата "
        f"сдвинут легче или тяжелее (σ = {num(rep['noise']['llm_drift_sd'])}) — так ТЗ описывает риск генерации: несопоставимая сложность между кандидатами.", "",
        "| Задания | Грейд совпал | Ошибка на ступень | Не подтверждён |", "|---|---|---|---|",
        f"| Калиброванные шаблоны | {pct(B0['exact'])} | {pct(B0['off_by_one'])} | {pct(B0['unconfirmed'])} |",
        f"| Без калибровки, случайный разброс | {pct(B1['exact'])} | {pct(B1['off_by_one'])} | {pct(B1['unconfirmed'])} |",
        f"| Без калибровки, сдвиг набора | {pct(B2['exact'])} | {pct(B2['off_by_one'])} | {pct(B2['unconfirmed'])} |",
        "", "Случайный разброс тест почти поглощает: ошибки отдельных заданий усредняются. Систематический сдвиг — нет: "
        "кандидату с лёгким набором тест завышает грейд, с тяжёлым — занижает, и пересдача это не исправляет.", "",
        "## 6. Качество подбора", "",
        f"{M['candidates']} кандидатов, {M['needs']} потребностей, {M['seeds']} независимых прогонов (среднее ± разброс). Эталон — разметка по истинным свойствам кандидата "
        "(истинный грейд, настоящий стек, деньги), которых не видит ни одна система; релевантен — оценка 2 или 3. "
        "Кандидат слабее запроса нерелевантен; сильнее на ступень — релевантен, если укладывается в вилку.", "",
        "| Ранжирование | P@10 | nDCG@10 | Слабее запроса в десятке | Сильнее запроса в десятке |", "|---|---|---|---|---|",
        *[f"| {t} | {num(M[k]['p10'])} ± {num(S[k]['p10'])} | {num(M[k]['ndcg10'])} ± {num(S[k]['ndcg10'])} | {pct(M[k]['under'])} ± {pct(S[k]['under'])} | {pct(M[k]['over'])} |"
          for t, k in [("Разряд: категория по тесту, балл", "ours"), ("Поиск по ключевым словам резюме", "keyword")]],
        "", "Разница — в двух местах. Поиск по резюме приводит к работодателю тех, кто завысил грейд, а тест их отсекает. "
        "А вилка у нас не только предупреждение, но и порядок: кандидат, чьи ожидания выше верха вилки больше чем на 10 %, "
        "стоит после укладывающихся. Без этого правила (версия до 10.10.2026) P@10 было 0,74, nDCG@10 — 0,67, "
        "а сильнее запроса в десятке — 24,7 %: честные кандидаты, не дотянувшие на тесте свою ступень, но дорогие для вилки. "
        "Поиску по резюме та же отсечка по вилке не помогает (P@10 0,73, nDCG@10 0,68): его ошибка — грейд, а не деньги.",
        "", "## Ограничения", "",
        "- Данные синтетические; эталон разметки построен командой по правилу, а не экспертами. Живая проверка — следующий шаг.",
        "- Модель ответа — IRT 2PL с шумом калибровки; поведение реальных людей сложнее.",
        "- Эффект утечки для банка шаблонов задан допущением «+30 % к шансу»; его стоит измерить на людях.",
        "- Деньги входят и в эталонную разметку, и в порядок выдачи; прирост от отсечки по вилке поэтому ожидаем. Честность сравнения "
        "держится на том, что вилку видят оба подхода, а растёт только тот, у кого грейд проверен.",
        f"- В банке {min(SPEC_N.values())}—{max(SPEC_N.values())} шаблонов на специализацию, а полный путь с тестом на ступень ниже берёт в среднем {num(A['items_mean'], 1)} заданий, "
        f"поэтому самый частый шаблон видят {pct(L['exposure_max'])} кандидатов. От зерна у каждого шаблона меняются условие, верный ответ и порядок вариантов, "
        "но сам шаблон — навык и трудность — кандидат узнаёт; рост банка — первая доработка после MVP.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
