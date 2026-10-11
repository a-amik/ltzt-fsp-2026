/* Артефакты, которые видит человек: профиль кандидата глазами работодателя,
   профиль работодателя глазами кандидата, протокол переговоров агентов
   и статистика сторон. Все числа приходят с сервера. */
import { useEffect, useState } from 'react';
import { GRADES, spec, fmt, fmtRange, gradeName, cap, num } from './const.js';
import { Mark } from './ui.jsx';

const pct = (v) => `${Math.round(v * 100)} %`;

// ── Шкала навыка: точка с коридором погрешности поверх полос грейдов ──
function SkillRow({ s, need }) {
  const x = (t) => `${((Math.max(-2.8, Math.min(2.8, t)) + 2.8) / 5.6) * 100}%`;
  return (
    <div className="sk-row">
      <span className="sk-name">{s.name}</span>
      <div className="sk-track" aria-label={`${s.name}: ${s.theta} ± ${s.se}`}>
        {GRADES.map((g) => <i key={g.id} className="sk-band" style={{ left: x(g.from), width: `calc(${x(g.to)} - ${x(g.from)})` }} />)}
        {need != null && <i className="sk-need" style={{ left: x(GRADES[need].from) }} title="Нижняя граница грейда вакансии" />}
        <i className="sk-ci" style={{ left: x(s.theta - s.se), width: `calc(${x(s.theta + s.se)} - ${x(s.theta - s.se)})` }} />
        <i className="sk-dot" style={{ left: x(s.theta) }} />
      </div>
      <span className="sk-g r-num">{GRADES.find((g) => s.theta >= g.from && s.theta < g.to)?.name}</span>
    </div>
  );
}
const SkillAxis = () => <div className="sk-row sk-axis"><span /><div className="sk-ticks">{GRADES.map((g) => <span key={g.id}>{g.name}</span>)}</div><span /></div>;

// ── 1. Профиль кандидата — то, что видит работодатель ─────────────────
/* card — карточка из API работодателя (контакты закрыты до согласия) либо profile кандидата (свой кабинет). */
export function CandidateProfileDoc({ card, profile, tests, rank, need, score }) {
  const c = card || { ...profile, anon: 'Вы', confirmed: profile.grade != null, grade: profile.grade ?? profile.claimed_grade, fsp: (profile.fsp || []).filter((a) => !a.hidden), facts: profile.facts.filter((f) => f.approved) };
  const skills = tests?.[0]?.skills || null;
  const words = c.facts.filter((f) => f.src === 'word');
  const g = c.grade;
  const strong = skills ? [...skills].sort((a, b) => b.theta - a.theta)[0] : null, weak = skills ? [...skills].sort((a, b) => a.theta - b.theta)[0] : null;
  return (
    <article className="doc">
      <header className="doc-head">
        <div>
          <p className="r-micro">{c.contacts ? 'Контакты открыты' : c.display ? 'Контакты откроются после согласия кандидата' : 'Так вас видит работодатель: контакты — после вашего согласия'}</p>
          <h2 className="r-h1 doc-title">{c.display || c.name}</h2>
          <p className="doc-cat">{spec(c.spec).name} · {gradeName(g)} {!c.confirmed && <span className="r-mark r-mark--warn">грейд не подтверждён</span>}</p>
          {c.contacts && <p className="r-small">{c.contacts.email}{c.contacts.phone ? ` · ${c.contacts.phone}` : ''}</p>}
        </div>
        <div className="doc-kpis">
          {c.confirmed ? <div><b className="r-num">{num(c.theta, 2)}</b><span>оценка ± {num(c.se, 2)}</span></div> : <div><b className="r-num">—</b><span>тест не пройден</span></div>}
          {rank && <div><b className="r-num">{rank.pos} из {rank.total}</b><span>в выдаче категории</span></div>}
          {c.years != null && <div><b className="r-num">{c.years} лет</b><span>стажа <Mark src="word" /></span></div>}
        </div>
      </header>

      {skills && (
        <section>
          <h3 className="r-h3">Что подтвердил тест</h3>
          <p className="r-small r-mute">Оценка по каждому навыку отдельно. Точка — оценка, полоса — погрешность{need != null ? ', черта — нижняя граница вашего грейда' : ''}.</p>
          <div className="sk">{skills.map((s) => <SkillRow key={s.name} s={s} need={need} />)}<SkillAxis /></div>
          <p className="doc-note">Сильнее всего — <b>{strong.name.toLowerCase()}</b>, слабее — <b>{weak.name.toLowerCase()}</b>{weak.items < 2 ? ' (мало заданий, погрешность выше)' : ''}.</p>
        </section>
      )}

      {score && (
        <section>
          <h3 className="r-h3">Почему в вашей подборке</h3>
          <ul className="why">{score.why.map((w, i) => <li key={i}><Mark src={w.src}>{w.src === 'warn' ? '!' : undefined}</Mark> {w.text}</li>)}</ul>
        </section>
      )}

      <section>
        <h3 className="r-h3">Соревнования ФСП</h3>
        {c.fsp.length ? (
          <div className="tablewrap scroll-x"><table className="r-table">
            <thead><tr><th>Соревнование</th><th>Год</th><th>Место</th><th>Что значит</th></tr></thead>
            <tbody>{c.fsp.map((e, i) => <tr key={i}><td>{e.event} <Mark src="fsp" /></td><td className="r-num">{e.year}</td><td className="r-num">{e.place} из {e.participants}</td><td className="r-small">выше {Math.round((1 - e.place / e.participants) * 100)} % участников · {e.level} · {e.discipline}{e.rank ? ` · ${e.rank}` : ''}</td></tr>)}</tbody>
          </table></div>
        ) : <p className="r-small r-mute">Записей в реестре ФСП нет. На место в категории это не влияет: порядок решает тест.</p>}
      </section>

      <section className="grid2">
        <div>
          <h3 className="r-h3">Условия</h3>
          <dl className="dl">
            <dt>Ожидания</dt><dd className="r-num">{c.salary ? fmt(c.salary) : 'скрыты'}</dd>
            <dt>Формат</dt><dd>{cap(c.work_format)}</dd>
            {c.city && <><dt>Город</dt><dd>{c.city}</dd></>}
            <dt>Задания работодателей</dt><dd>{c.fresh_tasks ?? 0} за 90 дней</dd>
            {c.conduct && <><dt>Протокол теста</dt><dd className="r-small">{c.conduct.items} заданий{c.conduct.mode === 'express' ? ' (экспресс)' : ''}, с открытым ИИ {c.conduct.ai_items}, вставок {c.conduct.paste}, уходов со вкладки {c.conduct.blur}</dd></>}
          </dl>
        </div>
        <div>
          <h3 className="r-h3">Со слов кандидата</h3>
          <ul className="facts">{words.map((f) => <li key={f.k}><Mark src="word" /> <b>{f.k}:</b> {f.v}</li>)}</ul>
          <p className="r-small r-mute">Эти факты не проверены — их стоит уточнить на встрече.</p>
        </div>
      </section>
    </article>
  );
}

// ── 2. Профиль работодателя — то, что видит кандидат ─────────────────
export function EmployerProfileDoc({ e, offer }) {
  const st = e.stats;
  const total = st.reasons.reduce((a, [, v]) => a + v, 0);
  return (
    <article className="doc">
      <header className="doc-head">
        <div>
          <p className="r-micro">Работодатель</p>
          <h2 className="r-h1 doc-title">{e.name}</h2>
          <p className="doc-cat">{e.field}</p>
          <p className="r-small">{e.verified ? <span className="r-mark r-mark--fsp">ИНН и корпоративная почта</span> : <span className="r-mark r-mark--word">компания не проверена</span>}</p>
        </div>
        <div className="doc-kpis">
          <div><b className="r-num">{st.invites}</b><span>приглашений отправлено</span></div>
          <div><b className="r-num">{st.accept_pct == null ? '—' : `${st.accept_pct} %`}</b><span>приглашений приняты</span></div>
          <div><b className="r-num">{st.vacancies}</b><span>открытых вакансий</span></div>
        </div>
      </header>
      <p>{e.about}</p>
      {offer && <section><h3 className="r-h3">Это предложение</h3><p className="r-vac__pay">{fmtRange(offer.from, offer.to)}</p><p className="r-small r-mute">Вилка зафиксирована в приглашении; итог — внутри неё по результатам встречи.</p></section>}
      <section>
        <h3 className="r-h3">Почему ей отказывают</h3>
        {total ? <div className="bars">{st.reasons.map(([k, v]) => <div key={k} className="bar-row"><span>{k}</span><i style={{ width: pct(v / total) }} /><b className="r-num">{v}</b></div>)}</div>
          : <p className="r-small r-mute">Отказов пока не было.</p>}
      </section>
    </article>
  );
}

// ── 3. Переговоры агентов: ход и протокол ────────────────────────────
const CRIT_LABEL = { ok: 'Совпадает', part: 'С оговоркой', no: 'Расхождение', nodata: 'Нет данных' };
export function Negotiation({ talk: n, company, who, side, instant }) {
  const [k, setK] = useState(instant ? 999 : 0);
  const [auto, setAuto] = useState(!instant);
  useEffect(() => { if (!auto || k >= n.steps.length) return; const t = setTimeout(() => setK(k + 1), 650); return () => clearTimeout(t); }, [auto, k, n.steps.length]);
  const done = k >= n.steps.length;
  const closed = Math.min(n.crit.length, Math.floor((k / n.steps.length) * (n.crit.length + 1)));
  return (
    <div className="nego">
      <div className="nego-talk">
        <p className="r-micro">Переговоры агентов · {company} ↔ {who}</p>
        <div className="r-talk">{n.steps.slice(0, k).map((s, i) => (
          <div key={i} className={`r-turn ${s.who === 'emp' ? 'r-turn--emp' : 'r-turn--cand'}`}>
            <span className="r-turn__who">{s.who === 'emp' ? `Агент · ${company}` : 'Агент кандидата'}</span>
            {s.nodata ? <div className="r-nodata">{s.text}</div> : <div className="r-turn__body">{s.text}{s.cite && <div className="r-cite">{s.cite.map((ci, j) => <span key={j}><Mark src={ci.src} /> {ci.text}</span>)}</div>}</div>}
          </div>))}
          {!done && <div className="typing r-micro">агент пишет…</div>}
        </div>
        <div className="acts">
          {!done && <button className="r-btn r-btn--sm" onClick={() => setAuto(!auto)}>{auto ? 'Пауза' : 'Дальше сам'}</button>}
          {!done && !auto && <button className="r-btn r-btn--sm" onClick={() => setK(k + 1)}>Следующая реплика</button>}
          {!done && <button className="r-btn r-btn--quiet r-btn--sm" onClick={() => setK(n.steps.length)}>К протоколу</button>}
        </div>
      </div>
      <aside className="nego-proto r-card r-card--flat">
        <p className="r-micro">Протокол · одинаковый у обеих сторон</p>
        <table className="crit"><tbody>{n.crit.map((x, i) => (
          <tr key={x.name} className={i < closed || done ? `c-${x.state}` : 'c-wait'}><td>{x.name}</td><td>{i < closed || done ? CRIT_LABEL[x.state] : '…'}</td><td className="r-small r-mute">{i < closed || done ? x.note : ''}</td></tr>))}</tbody></table>
        {done && <>
          <p className={`verdict v-${n.verdict.kind}`}>{n.verdict.text}</p>
          {n.open.length > 0 && <p className="r-small"><b>Уточнить людям:</b> {n.open.join(', ').toLowerCase()}.</p>}
          <p className="r-small r-mute">{side === 'emp' ? 'Решение о приглашении — за вами. Кандидат увидит этот же протокол вместе с приглашением.' : 'Решение — за вами. Компания видит этот же протокол; контакты откроются, только если вы примете приглашение.'}</p>
        </>}
      </aside>
    </div>
  );
}

// ── Почему я на этом месте: с сервера, тем же ранжированием ──────────
const NAMES = { test: 'выше тест', stack: 'стек ближе к запросу', fsp: 'сильнее ФСП', fresh: 'свежее задания' };
export function RankWhy({ rank: r, profile }) {
  if (!r) return null;
  const above = r.pos - 1;
  return (
    <section>
      <h3 className="r-h3">Почему вы на {r.pos} месте из {r.total}</h3>
      <p className="r-small r-mute">Типичный запрос к вашей категории: {spec(r.need.spec).name.toLowerCase()}, {gradeName(r.need.grade).toLowerCase()}, {r.need.stack.join(', ')}. Порядок тот же, что видит работодатель.</p>
      {!r.confirmed && <p className="doc-note">Грейд не подтверждён, поэтому вы ниже всех, кто прошёл тест. Первое действие — подтвердить грейд.</p>}
      {above ? (
        <div className="bars">{Object.entries(r.above_by).filter(([, v]) => v).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
          <div key={k} className="bar-row"><span>{NAMES[k]}</span><i style={{ width: pct(v / above) }} /><b className="r-num">{v}</b></div>))}</div>
      ) : <p className="doc-note">Вы первый в выдаче своей категории.</p>}
      {above > 0 && <p className="r-small r-mute">Сколько из {above} кандидатов выше вас обходят вас главным образом за счёт этого.</p>}
      <div className="tablewrap scroll-x"><table className="r-table">
        <thead><tr><th>Если сделать</th><th>Место</th></tr></thead>
        <tbody>{r.moves.map((m) => <tr key={m.text}><td>{m.text}</td><td className="r-num">{r.pos} → <b>{m.pos}</b></td></tr>)}</tbody>
      </table></div>
    </section>
  );
}

// ── 4. Статистика кандидата ─────────────────────────────────────────
export function CandStatsDoc({ profile, rank, stats: s }) {
  if (!s) return <p className="r-mute">Статистика появится после опроса.</p>;
  const exp = profile.salary;
  return (
    <article className="doc">
      <header className="doc-head"><div><p className="r-micro">Статистика</p><h2 className="r-h2">Как работодатели видят вас</h2></div>
        <div className="doc-kpis">{rank && <div><b className="r-num">{rank.pos} из {rank.total}</b><span>место в выдаче категории</span></div>}<div><b className="r-num">{s.invites}</b><span>приглашений</span></div><div><b className="r-num">{s.accepted}</b><span>приняли</span></div></div></header>
      <RankWhy rank={rank} profile={profile} />
      <section>
        <h3 className="r-h3">Вилки приглашений против ваших ожиданий</h3>
        {s.offers.length ? <>
          <div className="dots">{s.offers.map((o, i) => <i key={i} className={exp && o >= exp ? 'd-ok' : 'd-low'} style={{ left: `${Math.min(96, Math.max(2, (o / ((exp || o) * 1.6)) * 100))}%` }} title={fmt(o)} />)}
            {exp && <span className="dots-exp" style={{ left: `${100 / 1.6}%` }}>ваши {Math.round(exp / 1000)}</span>}</div>
          <p className="r-small r-mute">{s.not_below} из {s.offers.length} вилок не ниже ожиданий (по середине вилки).</p>
        </> : <p className="r-small r-mute">Приглашений пока не было.</p>}
      </section>
    </article>
  );
}

// ── 5. Статистика работодателя ──────────────────────────────────────
export function EmpStatsDoc({ company, stats: st }) {
  if (!st) return null;
  const funnel = [['Приглашений', st.invites], ['Просмотрено', st.viewed], ['Принято', st.accepted]];
  const total = st.reasons.reduce((a, [, v]) => a + v, 0);
  const m = st.market;
  return (
    <article className="doc">
      <header className="doc-head"><div><p className="r-micro">Статистика найма · {company.name}</p><h2 className="r-h2">Что происходит с вашими приглашениями</h2></div>
        <div className="doc-kpis"><div><b className="r-num">{st.accept_pct == null ? '—' : `${st.accept_pct} %`}</b><span>приглашений принято</span></div><div><b className="r-num">{st.responses}</b><span>откликов на вакансии</span></div></div></header>
      <section><h3 className="r-h3">Воронка</h3><Funnel rows={funnel} /></section>
      <section className="grid2">
        <div><h3 className="r-h3">Причины отказов</h3>
          {total ? <><div className="bars">{st.reasons.map(([k, v]) => <div key={k} className="bar-row"><span>{k}</span><i style={{ width: pct(v / total) }} /><b className="r-num">{v}</b></div>)}</div>
            {st.reasons[0]?.[0] === 'мало денег' && <p className="doc-note">Чаще всего отказывают из-за денег. Поднять верх вилки — плюс к принятию в этой категории.</p>}</> : <p className="r-small r-mute">Отказов пока нет.</p>}
        </div>
        <div>{m ? <><h3 className="r-h3">Рынок категории «{spec(m.need.spec).name} · {gradeName(m.need.grade)}»</h3>
          <Hist vals={m.salaries} from={m.need.salary_from} to={m.need.salary_to} />
          <p className="r-small r-mute">{m.count} кандидатов; {m.within != null ? `${m.within} из них ждут не больше вашей верхней границы` : 'укажите вилку в запросе'}.</p></> : <p className="r-small r-mute">Сделайте подбор — здесь появится рынок вашей категории.</p>}</div>
      </section>
    </article>
  );
}

function Funnel({ rows }) {
  const max = rows[0][1] || 1;
  return <div className="funnel">{rows.map(([k, v], i) => (
    <div key={k} className="fn-row"><span>{k}</span><i style={{ width: `${Math.max(2, (v / max) * 100)}%` }} /><b className="r-num">{v}</b><span className="r-small r-mute">{i && rows[i - 1][1] ? pct(v / rows[i - 1][1]) : ''}</span></div>))}</div>;
}
function Hist({ vals, from, to }) {
  if (!vals.length) return null;
  const lo = Math.min(...vals) * 0.9, hi = Math.max(...vals) * 1.05, N = 12;
  const bins = Array(N).fill(0); vals.forEach((v) => bins[Math.min(N - 1, Math.floor(((v - lo) / (hi - lo || 1)) * N))]++);
  const m = Math.max(...bins); const x = (v) => `${Math.max(0, Math.min(100, ((v - lo) / (hi - lo || 1)) * 100))}%`;
  return (
    <div className="hist">
      <div className="hist-bars">{bins.map((b, i) => <i key={i} style={{ height: `${(b / m) * 100}%` }} />)}</div>
      {from && to && <i className="hist-range" style={{ left: x(from), width: `calc(${x(to)} - ${x(from)})` }} />}
      <div className="hist-ax r-small r-mute"><span>{Math.round(lo / 1000)} тыс.</span><span>ожидания кандидатов</span><span>{Math.round(hi / 1000)} тыс.</span></div>
    </div>
  );
}
