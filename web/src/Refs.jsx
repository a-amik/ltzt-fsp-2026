/* Отзывы и связи. Агент кандидата собирает сводку о компании в фоне; агент
   компании опрашивает бывших коллег кандидата, не называя компанию; кандидат
   видит, сколько отзывов о нём собрано и сколько агентов опрошено, но не сами
   отзывы. Открытые отзывы — только оценка и число (решения участника 11.10.2026). */
import { useEffect, useState } from 'react';
import { useStore } from './store.jsx';
import { get, patch, post } from './api.js';
import SignLoader from './SignLoader.jsx';

const n1 = (x) => (x == null ? '—' : x.toFixed(1).replace('.', ','));
const plural = (n, one, few, many) => { const m10 = n % 10, m100 = n % 100; return m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many; };

// ── Кандидату: сводка о компании в приглашении ─────────────────────────
export function CompanySummary({ s }) {
  if (!s) return null;
  const open = s.open || [];
  const cnt = open.reduce((a, x) => a + x.count, 0);
  const avg = cnt ? open.reduce((a, x) => a + x.rating * x.count, 0) / cnt : null;
  const rows = [
    { k: 'Сотрудники', n: s.staff.n, text: s.staff.notes.length ? s.staff.notes.map((x) => `«${x}»`).join(' ') : 'Отзывов пока нет', meta: `Опрошено ${s.staff.asked} ${plural(s.staff.asked, 'агент', 'агента', 'агентов')}${s.staff.avg ? ` · средняя ${n1(s.staff.avg)} из 5` : ''}`, mark: 'Со слов' },
    { k: 'Кандидаты', n: s.cands.n, text: s.cands.note || 'Компания ещё никого не приглашала', meta: `Приглашений ${s.cands.invites} · приняли ${s.cands.accepted}`, mark: 'Платформа' },
    { k: 'Открытые', n: cnt, text: avg ? `Средняя оценка ${n1(avg)} из 5` : 'Открытых оценок нет', meta: open.map((x) => `${x.src} ${n1(x.rating)} · ${x.count}`).join(' · '), mark: 'Открытый источник', tip: 'Берём оценку и число отзывов. Тексты открытых отзывов не забираем: неизвестно, зачем их писали' },
  ];
  return (
    <section className="rf-sum">
      <p className="r-micro">Сводка о&nbsp;компании · ваш агент собрал в&nbsp;фоне</p>
      <ul>{rows.map((r) => (
        <li key={r.k}>
          <b className="rf-sum__k">{r.k}&nbsp;· <span className="r-num">{r.n}</span></b>
          <div><span>{r.text}</span><span className="r-small r-mute">{r.meta}</span></div>
          <span className="r-mark" title={r.tip}>{r.mark}</span>
        </li>))}</ul>
    </section>
  );
}

// ── Кандидату: вкладка «Отзывы» ─────────────────────────────────────────
export function RefsTab() {
  const { state, act, loadCand } = useStore();
  const m = state.cand.profile;
  const [d, setD] = useState(null);
  const load = () => get('cand', '/candidate/references').then(setD).catch(() => {});
  useEffect(() => { load(); }, []); // eslint-disable-line
  if (!d) return <SignLoader small />;
  const priv = (k, v) => act(() => patch('cand', '/candidate/profile', { privacy: { ...m.privacy, [k]: v } }), 'cand').then(load);
  const a = d.about_me;
  return (
    <div className="stack">
      <section className="r-card r-card--flat stack-sm">
        <h2 className="r-h3">Отзывы обо мне</h2>
        <div className="rf-nums">
          <div><b className="r-num">{a.agents}</b><span>{plural(a.agents, 'агент коллеги опрошен', 'агента коллег опрошено', 'агентов коллег опрошено')}</span></div>
          <div><b className="r-num">{a.collected}</b><span>{plural(a.collected, 'отзыв собран', 'отзыва собрано', 'отзывов собрано')}</span></div>
          <div><b className="r-num">{a.companies}</b><span>{plural(a.companies, 'компания спрашивала', 'компании спрашивали', 'компаний спрашивали')}</span></div>
        </div>
        <p className="r-small r-mute">Сами отзывы видят компании; вам видно, сколько их. Коллег находит агент по&nbsp;местам работы, компанию в&nbsp;запросе не&nbsp;называют.</p>
        <label className="r-switch"><input type="checkbox" checked={d.settings.collect} onChange={(e) => priv('refs_collect', e.target.checked)} /><i />Разрешить сбор отзывов обо мне</label>
        <label className="r-switch"><input type="checkbox" checked={d.settings.agent} onChange={(e) => priv('refs_agent', e.target.checked)} /><i />Мой агент отвечает на&nbsp;запросы о&nbsp;коллегах готовым отзывом</label>
      </section>

      <section className="r-card r-card--flat stack-sm">
        <h2 className="r-h3">Рекомендации коллег</h2>
        <p className="r-small">Одобрено: <b>{d.recs.approved}</b>{d.recs.asked ? <> · ждём ответа: <b>{d.recs.asked}</b></> : null}. Одобренные видят компании, они поднимают вас в&nbsp;выдаче.</p>
        {d.recs.items.filter((r) => !r.approved).map((r) => (
          <div key={r.id} className="rf-q"><p className="r-small r-mute">Коллега по&nbsp;«{r.relation}»</p><p>«{r.answers?.strong}»</p>
            <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--sm r-btn--main" onClick={() => act(() => post('cand', `/candidate/recommendations/${r.id}?approved=true`)).then(load)}>Показывать в&nbsp;профиле</button></div></div>))}
        <div className="acts" style={{ marginTop: 0 }}>
          <button className="r-btn r-btn--sm" disabled={!d.colleagues} onClick={() => act(() => post('cand', '/candidate/recommendations/ask'), 'cand').then(load)}>Попросить рекомендацию у&nbsp;коллег</button>
          <span className="r-small r-mute">{d.colleagues ? `Агент нашёл ${d.colleagues} ${plural(d.colleagues, 'коллегу', 'коллег', 'коллег')} по местам работы` : 'Добавьте места работы в фактах — агент найдёт коллег'}</span>
        </div>
      </section>

      <section className="stack-sm">
        <h2 className="r-h3">Запросы о&nbsp;бывших коллегах</h2>
        {!d.inbox.length && <p className="r-small r-mute">Запросов нет. Когда компания заинтересуется вашим бывшим коллегой, её агент спросит вас о&nbsp;нём здесь.</p>}
        {d.inbox.map((r) => <Ask key={r.id} r={r} onDone={() => { load(); loadCand(); }} />)}
      </section>
    </div>
  );
}

function Ask({ r, onDone }) {
  const { act } = useStore();
  const [f, setF] = useState({ strong: '', grow: '', again: true });
  const send = (body) => act(() => post('cand', `/candidate/references/${r.id}`, body)).then(onDone);
  const done = r.status !== 'asked';
  return (
    <div className="r-card r-card--flat stack-sm rf-ask">
      <p className="r-micro">{r.kind === 'rec' ? 'Просьба о рекомендации' : r.asker}</p>
      <p><b>{r.about}</b> · работали вместе в&nbsp;«{r.relation}»</p>
      {done ? <p className="r-small">{r.status === 'declined' ? 'Вы отказались. Компания видит только, что ответа нет.' : `Вы ответили: «${r.answers?.strong}»`}</p> : (<>
        <div className="r-field wide"><label className="r-label" htmlFor={`s${r.id}`}>В&nbsp;чём сильный</label><input id={`s${r.id}`} className="r-input" value={f.strong} onChange={(e) => setF({ ...f, strong: e.target.value })} placeholder="Держит сроки, сильный в PostgreSQL" /></div>
        <div className="r-field wide"><label className="r-label" htmlFor={`g${r.id}`}>Над чем работать</label><input id={`g${r.id}`} className="r-input" value={f.grow} onChange={(e) => setF({ ...f, grow: e.target.value })} /></div>
        <div><p className="r-label">Взяли&nbsp;бы снова в&nbsp;команду?</p><div className="seg" role="group" aria-label="Взяли бы снова"><button aria-pressed={f.again} onClick={() => setF({ ...f, again: true })}>Да</button><button aria-pressed={!f.again} onClick={() => setF({ ...f, again: false })}>Нет</button></div></div>
        <div className="acts" style={{ marginTop: 0 }}>
          <button className="r-btn r-btn--main" disabled={f.strong.trim().length < 3} onClick={() => send(f)}>Отправить отзыв</button>
          <button className="r-btn r-btn--quiet" onClick={() => send({ decline: true })}>Отказаться</button>
        </div>
        <p className="r-small r-mute">Название компании не&nbsp;раскрывается. Отказаться можно без причины.</p>
      </>)}
    </div>
  );
}

// ── Компании: отзывы бывших коллег в профиле кандидата ──────────────────
export function ColleagueRefs({ id }) {
  const [d, setD] = useState(null);
  useEffect(() => { get('emp', `/employer/candidates/${id}/references`).then(setD).catch(() => setD({ error: true })); }, [id]);
  if (!d) return <p className="r-small r-mute">Агент опрашивает бывших коллег…</p>;
  if (d.error) return null;
  return (
    <section className="rf-refs">
      <p className="r-micro">Отзывы бывших коллег · агент собрал в&nbsp;фоне</p>
      {d.closed ? <p className="r-small">Кандидат закрыл сбор отзывов о&nbsp;себе.</p> : !d.asked ? <p className="r-small">Агент не&nbsp;нашёл коллег: в&nbsp;профиле нет общих мест работы с&nbsp;другими кандидатами.</p> : (<>
        <p><b className="r-num">Ответили {d.answered} из&nbsp;{d.asked}</b>{d.declined ? <span className="r-small r-mute"> · отказались {d.declined}</span> : null}{d.pending ? <span className="r-small r-mute"> · ждём {d.pending}</span> : null}</p>
        <ul className="rf-quotes">{d.quotes.map((q, i) => (
          <li key={i}><span className="r-small r-mute">Коллега по&nbsp;«{q.relation}»</span><span>«{q.strong}»</span>{q.grow && <span className="r-small">Над чем работать: {q.grow}</span>}
            <span className={`r-mark ${q.again ? 'r-mark--fsp' : ''}`}>{q.again ? 'Взял бы снова' : 'Не уверен'}</span></li>))}</ul>
      </>)}
      <p className="r-small r-mute">Анонимно: компанию в&nbsp;запросе не&nbsp;называют, коллега может отказаться.</p>
    </section>
  );
}
