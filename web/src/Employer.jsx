/* Кабинет работодателя: вход, компания, потребность и подборка, приглашения,
   вакансии с откликами, задания, статистика. Ранжирование и протоколы — с сервера. */
import { useEffect, useState } from 'react';
import { useStore } from './store.jsx';
import { get, post, patch, qs, setToken } from './api.js';
import { GRADES, SPECS, FORMATS, spec, gradeName, fmt, fmtRange } from './const.js';
import { Mark, Modal, Score, Empty, Tabs, Status } from './ui.jsx';
import { CandidateProfileDoc, Negotiation, EmployerProfileDoc, EmpStatsDoc } from './Artifacts.jsx';
import Mass from './Mass.jsx';
import { EmployerTasks } from './Tasks.jsx';

export default function Employer() {
  const { state, dispatch } = useStore();
  const e = state.emp;
  if (!e.authed) return <EmpStart />;
  if (!e.company) return <p className="page r-mute">Загружаем…</p>;
  if (!e.company.name) return <CompanyForm first />;
  const waiting = e.invites.filter((i) => ['отправлено', 'просмотрено'].includes(i.status)).length;
  return (
    <div className="page">
      <Tabs value={state.ui.empTab} onChange={(t) => dispatch({ type: 'ui', patch: { empTab: t } })} items={[['search', 'Подбор'], ['bank', 'Банк'], ['tasks', 'Задания'], ['invites', 'Приглашения', waiting], ['stats', 'Статистика'], ['company', 'Компания'], ['vac', 'Вакансии']]} />
      {state.ui.empTab === 'search' && <Search />}
      {state.ui.empTab === 'bank' && <Bank />}
      {state.ui.empTab === 'tasks' && <EmployerTasks />}
      {state.ui.empTab === 'invites' && <Sent />}
      {state.ui.empTab === 'vac' && <Vacs />}
      {state.ui.empTab === 'company' && <CompanyForm />}
      {state.ui.empTab === 'stats' && <EmpStatsDoc company={e.company} stats={e.stats} />}
    </div>
  );
}

function EmpStart() {
  const { act } = useStore();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(null);
  const start = () => act(async () => { const r = await post(null, '/auth/start', { email, role: 'employer' }); setSent(r); if (r.code) setCode(r.code); });
  const confirm = () => act(async () => { const r = await post(null, '/auth/confirm', { email, code, consent: true }); setToken('emp', r.token); }, 'emp');
  const demo = () => act(async () => { setToken('emp', 'demo-employer-token'); }, 'emp');
  return (
    <div className="page">
      <p className="r-micro">Работодатель</p>
      <h1 className="r-h1">Вы находите кандидата сами — и&nbsp;пишете первым, с&nbsp;вилкой</h1>
      <p className="r-mute">Опишите, кто нужен, получите категории с&nbsp;числом людей и&nbsp;ранжированный список с&nbsp;объяснением. Контакты откроются, когда кандидат примет приглашение.</p>
      <div className="grid2">
        <div className="r-card r-card--flat stack-sm">
          <h2 className="r-h3">Вход по&nbsp;почте компании</h2>
          <div className="r-field"><label className="r-label" htmlFor="ee">Почта</label><input id="ee" className="r-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="hr@company.ru" /></div>
          {!sent ? <button className="r-btn" disabled={!/.+@.+\..+/.test(email)} onClick={start}>Получить код</button> : (<>
            <p className="r-small">{sent.code ? <>Демо-режим: письмо не&nbsp;уходит, код&nbsp;— <b className="r-num">{sent.code}</b>.</> : <>Код ушёл на&nbsp;{email}.</>}</p>
            <div className="r-field"><label className="r-label" htmlFor="ec">Код</label><input id="ec" className="r-input r-num" value={code} onChange={(e) => setCode(e.target.value)} /></div>
            <button className="r-btn r-btn--main" disabled={code.length < 6} onClick={confirm}>Войти</button>
          </>)}
        </div>
        <div className="r-card stack-sm">
          <h2 className="r-h3">Демо-компания</h2>
          <p className="r-small r-mute">«ТрансКод» из&nbsp;синтетических данных: три вакансии, задание категории, история приглашений.</p>
          <button className="r-btn r-btn--main" onClick={demo}>Войти как ТрансКод</button>
        </div>
      </div>
    </div>
  );
}

function CompanyForm({ first }) {
  const { state, act } = useStore();
  const c = state.emp.company;
  const [f, setF] = useState({ name: c.name || '', about: c.about || '', field: c.field || '', contact: c.contact || '', inn: c.inn || '' });
  const save = () => act(() => patch('emp', '/employer/company', f), 'emp');
  return (
    <div className="page">
      {first && <><p className="r-micro">Работодатель · профиль компании</p><h1 className="r-h1">Расскажите о&nbsp;компании</h1></>}
      <div className="r-card r-card--flat stack">
        <div className="grid2 tight">
          <div className="r-field"><label className="r-label" htmlFor="cn">Название</label><input id="cn" className="r-input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
          <div className="r-field"><label className="r-label" htmlFor="cf">Направление</label><input id="cf" className="r-input" value={f.field} onChange={(e) => setF({ ...f, field: e.target.value })} /></div>
        </div>
        <div className="r-field wide"><label className="r-label" htmlFor="ca">О компании и команде</label><textarea id="ca" className="r-area" value={f.about} onChange={(e) => setF({ ...f, about: e.target.value })} /></div>
        <div className="grid2 tight">
          <div className="r-field"><label className="r-label" htmlFor="cc">Контакт для кандидатов</label><input id="cc" className="r-input" value={f.contact} onChange={(e) => setF({ ...f, contact: e.target.value })} /></div>
          <div className="r-field"><label className="r-label" htmlFor="ci">ИНН</label><input id="ci" className="r-input r-num" value={f.inn} onChange={(e) => setF({ ...f, inn: e.target.value.replace(/\D/g, '') })} /><span className="r-hint">ИНН и корпоративная почта дают метку доверия <Mark src="fsp">проверена</Mark>; без неё всё работает.</span></div>
        </div>
        <div className="acts"><button className="r-btn r-btn--main" disabled={!f.name} onClick={save}>Сохранить</button>{c.verified && <span className="r-mark r-mark--fsp">компания проверена</span>}</div>
      </div>
      {!first && <div className="acts"><button className="r-btn r-btn--sm r-btn--quiet" onClick={() => { setToken('emp', null); location.reload(); }}>Выйти</button></div>}
    </div>
  );
}

// ── Подбор ──────────────────────────────────────────────────────────
function Search() {
  const { state, dispatch, act } = useStore();
  const e = state.emp;
  const ui = state.ui;
  const [text, setText] = useState(e.needText || 'Нужен бэкенд-разработчик среднего уровня в команду тарифов: Python, PostgreSQL, Kafka. Гибрид, Москва. Вилка 220 000 – 300 000.');
  const sel = e.selection;
  const need = sel?.need;
  const [inv, setInv] = useState(null);
  const [talk, setTalk] = useState(null);
  const [prof, setProf] = useState(null);
  const [show, setShow] = useState(10);
  const f = ui.filters;
  const setF = (p) => dispatch({ type: 'ui', patch: { filters: { ...f, ...p } } });
  const load = (needId, filters = f) => act(async () => {
    const s = await get('emp', `/employer/needs/${needId}/selection${qs({ ...filters, talks: true, limit: 60 })}`);
    dispatch({ type: 'emp', patch: { selection: s } });
    dispatch({ type: 'ui', patch: { needId } });
  });
  useEffect(() => { if (ui.needId && !sel) load(ui.needId).catch(() => dispatch({ type: 'ui', patch: { needId: null } })); }, []); // eslint-disable-line
  const parse = () => act(async () => { const n = await post('emp', '/employer/needs', { text }); dispatch({ type: 'emp', patch: { needText: text } }); await load(n.id); });
  const setNeed = (p) => act(async () => { await patch('emp', `/employer/needs/${need.id}`, { text: need.text, ...p }); await load(need.id); });
  const changeF = (p) => { const nf = { ...f, ...p }; setF(p); if (need) load(need.id, nf); };
  const items = sel?.items || [];
  const shortlist = ui.shortlist;
  const toggleShort = (id) => dispatch({ type: 'ui', patch: { shortlist: shortlist.includes(id) ? shortlist.filter((x) => x !== id) : [...shortlist, id] } });
  return (
    <div className="stack">
      <div className="r-card r-card--flat">
        <div className="r-field wide"><label className="r-label" htmlFor="need">Кого ищете — своими словами</label>
          <textarea id="need" className="r-area" rows={3} value={text} onChange={(ev) => setText(ev.target.value)} />
          <span className="r-hint">Специализацию, грейд, стек и&nbsp;вилку разберёт ассистент; поправить можно ниже.</span></div>
        <button className="r-btn r-btn--main" onClick={parse}>Подобрать</button>
      </div>

      {need && (<>
        <div className="r-card r-card--flat stack-sm">
          <p className="r-micro">Как ассистент понял запрос</p>
          <div className="r-chips scroll-x nowrap">{SPECS.map((s) => <button key={s.id} className="r-chip" aria-pressed={need.spec === s.id} onClick={() => setNeed({ spec: s.id, stack: s.stack.slice(0, 2) })}>{s.name}</button>)}</div>
          <div className="r-chips scroll-x nowrap">{spec(need.spec).stack.map((s) => <button key={s} className="r-chip" aria-pressed={need.stack.includes(s)} onClick={() => setNeed({ stack: need.stack.includes(s) ? need.stack.filter((x) => x !== s) : [...need.stack, s] })}>{s}</button>)}</div>
          <p className="r-small">Вилка: <b className="r-num">{need.salary_from ? fmtRange(need.salary_from, need.salary_to || need.salary_from) : 'не указана — понадобится в приглашении'}</b>{need.work_format ? <> · формат: <b>{need.work_format}</b></> : null}</p>
        </div>
        <div>
          <p className="r-micro">Категории · {spec(need.spec).name}</p>
          <div className="cats scroll-x">{sel.categories.map((g) => (
            <button key={g.grade} className={`cat r-card ${need.grade === g.grade ? 'is-on' : ''}`} onClick={() => setNeed({ grade: g.grade })} aria-pressed={need.grade === g.grade}>
              <span className="r-micro">{GRADES[g.grade].short}</span><b>{g.name}</b><span className="r-num cat-n">{g.count}</span>
            </button>))}</div>
        </div>
        <div className="r-chips scroll-x nowrap filters">
          <button className="r-chip" aria-pressed={f.near} onClick={() => changeF({ near: !f.near })}>+ соседние грейды</button>
          <button className="r-chip" aria-pressed={f.fsp_only} onClick={() => changeF({ fsp_only: !f.fsp_only })}>Только с&nbsp;ФСП</button>
          <button className="r-chip" aria-pressed={f.confirmed_only} onClick={() => changeF({ confirmed_only: !f.confirmed_only })}>Только подтверждённые</button>
          <button className="r-chip" aria-pressed={f.must_stack} onClick={() => changeF({ must_stack: !f.must_stack })}>Весь стек обязателен</button>
          {FORMATS.map((x) => <button key={x} className="r-chip" aria-pressed={f.work_format === x} onClick={() => changeF({ work_format: f.work_format === x ? null : x })}>{x}</button>)}
        </div>
        {shortlist.length > 0 && (
          <div className="r-card r-card--sun short">
            <p className="r-micro">Отбор · сохраняется при&nbsp;смене фильтров</p>
            <div className="r-chips">{shortlist.map((id) => { const c = items.find((x) => x.id === id); return <button key={id} className="r-chip" onClick={() => c && setTalk(c)}>{c?.display || `Кандидат №${id}`}{c ? ` · ${gradeName(c.grade)}` : ''}</button>; })}</div>
          </div>
        )}
        <div className="view-seg"><div className="seg" role="group" aria-label="Вид выдачи">
          <button aria-pressed={ui.view === 'mass'} onClick={() => dispatch({ type: 'ui', patch: { view: 'mass' } })}>Переговоры с категорией</button>
          <button aria-pressed={ui.view === 'list'} onClick={() => dispatch({ type: 'ui', patch: { view: 'list' } })}>Профили списком</button>
        </div></div>
        {ui.view === 'mass' && items.length > 0 && <Mass items={items} company={e.company.name} salaryTo={need.salary_to} onInvite={(cs) => setInv(cs)} />}
        {ui.view === 'list' && <>
          <p className="r-small r-mute">{sel.total} кандидатов. Порядок: <span title="Тест 60 %, стек 20 %, ФСП 10 %, свежесть 10 %; неподтверждённые — после подтверждённых" className="tip">ⓘ из&nbsp;чего складывается</span></p>
          {!items.length && <Empty title="В категории никого">Снимите фильтр или добавьте соседние грейды — подборка не&nbsp;потеряется.</Empty>}
          {items.slice(0, show).map((c, k) => (
            <article key={c.id} className="r-card cand">
              <div className="r-cand">
                <div className="r-avatar">{k + 1}</div>
                <div>
                  <p className="r-cand__name">{c.display} {!c.confirmed && <span className="r-mark r-mark--warn">грейд не подтверждён</span>}</p>
                  <p className="r-cand__role">{spec(c.spec).name} · {gradeName(c.grade)} · {c.work_format}{c.salary ? ` · ожидает ${fmt(c.salary)}` : ''}</p>
                  <ul className="why">{c.score.why.map((w, i) => <li key={i}><Mark src={w.src}>{w.src === 'warn' ? '!' : undefined}</Mark> {w.text}</li>)}</ul>
                </div>
                <div className="r-cand__act">
                  <Score parts={c.score.parts} />
                  <button className="r-btn r-btn--main r-btn--sm" onClick={() => setInv([c])}>Пригласить…</button>
                  <button className="r-btn r-btn--sm" onClick={() => setProf(c)}>Профиль…</button>
                  <button className="r-btn r-btn--sm" onClick={() => setTalk(c)}>Переговоры агентов…</button>
                  <button className="r-btn r-btn--quiet r-btn--sm" onClick={() => toggleShort(c.id)}>{shortlist.includes(c.id) ? 'Убрать из отбора' : 'В отбор'}</button>
                </div>
              </div>
            </article>
          ))}
          {items.length > show && <button className="r-btn" onClick={() => setShow(show + 10)}>Ещё 10</button>}
        </>}
      </>)}
      {inv && <InviteForm list={inv} need={need} onClose={() => setInv(null)} />}
      {talk && <Modal title="Переговоры агентов" wide onClose={() => setTalk(null)}><Negotiation talk={talk.talk} company={e.company.name} who={talk.display} side="emp" /><div className="acts"><button className="r-btn r-btn--main" onClick={() => { setInv([talk]); setTalk(null); }}>Пригласить…</button></div></Modal>}
      {prof && <ProfileModal c={prof} need={need} onClose={() => setProf(null)} onInvite={() => { setInv([prof]); setProf(null); }} onTalk={() => { setTalk(prof); setProf(null); }} />}
    </div>
  );
}

function ProfileModal({ c, need, onClose, onInvite, onTalk }) {
  const [card, setCard] = useState(null);
  useEffect(() => { get('emp', `/employer/candidates/${c.id}`).then(setCard).catch(() => setCard(c)); }, [c.id]); // eslint-disable-line
  return (
    <Modal title="Профиль кандидата" wide onClose={onClose}>
      {card ? <CandidateProfileDoc card={card} need={need?.grade} score={c.score} /> : <p className="r-mute">Загружаем…</p>}
      <div className="acts"><button className="r-btn r-btn--main" onClick={onInvite}>Пригласить…</button>{c.talk && <button className="r-btn" onClick={onTalk}>Переговоры агентов…</button>}</div>
    </Modal>
  );
}

// ── Банк кандидатов с фильтрами ─────────────────────────────────────
function Bank() {
  const { act } = useStore();
  const [f, setF] = useState({ spec: 'backend', grade: null, fsp_only: false, confirmed_only: false, work_format: null });
  const [res, setRes] = useState(null);
  const [prof, setProf] = useState(null);
  useEffect(() => { act(() => get('emp', `/employer/candidates${qs({ ...f, limit: 30 })}`)).then(setRes).catch(() => {}); }, [f]); // eslint-disable-line
  return (
    <div className="stack">
      <div className="r-chips scroll-x nowrap">{SPECS.map((s) => <button key={s.id} className="r-chip" aria-pressed={f.spec === s.id} onClick={() => setF({ ...f, spec: s.id })}>{s.name}</button>)}</div>
      <div className="r-chips scroll-x nowrap">{GRADES.map((g) => <button key={g.id} className="r-chip" aria-pressed={f.grade === g.id} onClick={() => setF({ ...f, grade: f.grade === g.id ? null : g.id })}>{g.name}</button>)}
        <button className="r-chip" aria-pressed={f.fsp_only} onClick={() => setF({ ...f, fsp_only: !f.fsp_only })}>Только с&nbsp;ФСП</button>
        <button className="r-chip" aria-pressed={f.confirmed_only} onClick={() => setF({ ...f, confirmed_only: !f.confirmed_only })}>Только подтверждённые</button>
        {FORMATS.map((x) => <button key={x} className="r-chip" aria-pressed={f.work_format === x} onClick={() => setF({ ...f, work_format: f.work_format === x ? null : x })}>{x}</button>)}</div>
      {res && <p className="r-small r-mute">{res.total} кандидатов. Порядок: подтверждённые по оценке теста, затем неподтверждённые.</p>}
      <div className="tablewrap scroll-x"><table className="r-table">
        <thead><tr><th>Кандидат</th><th>Грейд</th><th>Оценка</th><th>Стек</th><th>Формат</th><th>ФСП</th><th>Ожидания</th></tr></thead>
        <tbody>{(res?.items || []).map((c) => <tr key={c.id}><td><button className="linkish" onClick={() => setProf(c)}>{c.display}</button></td><td>{gradeName(c.grade)}{!c.confirmed && <> <span className="r-mark r-mark--warn">не подтв.</span></>}</td><td className="r-num">{c.confirmed ? `${c.theta.toFixed(2)} ± ${c.se.toFixed(2)}` : '—'}</td><td className="r-small">{c.stack.join(', ')}</td><td>{c.work_format}</td><td>{c.fsp.length ? <Mark src="fsp">{c.fsp.length}</Mark> : <span className="r-mute">—</span>}</td><td className="r-num">{c.salary ? fmt(c.salary) : 'скрыты'}</td></tr>)}</tbody>
      </table></div>
      {prof && <ProfileModal c={{ ...prof, score: null, talk: null }} onClose={() => setProf(null)} onInvite={() => setProf(null)} />}
    </div>
  );
}

function InviteForm({ list, need, onClose }) {
  const c = list[0];
  const { state, act, dispatch } = useStore();
  const own = state.emp.vacancies;
  const [f, setF] = useState({ vacancy_id: null, title: `${spec(c.spec).name}, ${gradeName(c.grade).toLowerCase()}`, text: 'Увидели ваш тест и стек. Хотим познакомиться: 30 минут с техлидом.', salary_from: need?.salary_from || '', salary_to: need?.salary_to || '', contact: state.emp.company.contact || 'Телеграм рекрутера', work_format: need?.work_format || 'гибрид' });
  const lowN = f.salary_to ? list.filter((x) => x.salary && +f.salary_to < x.salary).length : 0;
  const ok = f.title && f.text && +f.salary_from > 0 && +f.salary_to >= +f.salary_from && f.contact;
  const [result, setResult] = useState(null);
  const send = () => act(async () => {
    const out = [];
    for (const x of list) {
      try { out.push(await post('emp', '/employer/invites', { ...f, candidate_id: x.id, salary_from: +f.salary_from, salary_to: +f.salary_to, need_id: need?.id })); } catch (err) { out.push({ error: err.message, anon: x.display }); }
    }
    setResult(out);
  }, 'emp');
  if (result) {
    const okN = result.filter((r) => !r.error).length;
    return <Modal title="Приглашения отправлены" onClose={onClose}><p>Отправлено {okN} из {result.length}.</p>{result.filter((r) => r.error).map((r, i) => <p key={i} className="r-small">{r.display}: {r.error}</p>)}<div className="acts"><button className="r-btn r-btn--main" onClick={() => { dispatch({ type: 'ui', patch: { empTab: 'invites' } }); onClose(); }}>К приглашениям</button></div></Modal>;
  }
  return (
    <Modal title={list.length > 1 ? `Приглашение · ${list.length} кандидатам` : `Приглашение · ${c.display}`} onClose={onClose}>
      <div className="r-field wide"><label className="r-label">Вакансия (необязательно)</label>
        <div className="r-chips"><button className="r-chip" aria-pressed={!f.vacancy_id} onClick={() => setF({ ...f, vacancy_id: null })}>Без вакансии</button>{own.map((v) => <button key={v.id} className="r-chip" aria-pressed={f.vacancy_id === v.id} onClick={() => setF({ ...f, vacancy_id: v.id, title: v.title, salary_from: v.salary_from, salary_to: v.salary_to, work_format: v.work_format })}>{v.title}</button>)}</div></div>
      <div className="r-field wide"><label className="r-label" htmlFor="it">Что предлагаете</label><input id="it" className="r-input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
      <div className="r-field wide"><label className="r-label" htmlFor="ix">Сообщение</label><textarea id="ix" className="r-area" value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} /></div>
      <div className="grid2 tight">
        <div className="r-field" data-state={lowN ? 'bad' : undefined}><label className="r-label" htmlFor="if">Зарплата от, ₽</label><input id="if" className="r-input r-num" inputMode="numeric" value={f.salary_from} onChange={(e) => setF({ ...f, salary_from: e.target.value.replace(/\D/g, '') })} /></div>
        <div className="r-field" data-state={lowN ? 'bad' : undefined}><label className="r-label" htmlFor="io">до, ₽</label><input id="io" className="r-input r-num" inputMode="numeric" value={f.salary_to} onChange={(e) => setF({ ...f, salary_to: e.target.value.replace(/\D/g, '') })} />{lowN > 0 && <span className="r-hint">{list.length > 1 ? `Ниже ожиданий у ${lowN} из ${list.length} — вероятны отказы` : `Ниже ожиданий кандидата (${fmt(c.salary)}) — вероятен отказ`}</span>}</div>
      </div>
      <div className="grid2 tight">
        <div className="r-field"><label className="r-label" htmlFor="ic">Способ связи</label><input id="ic" className="r-input" value={f.contact} onChange={(e) => setF({ ...f, contact: e.target.value })} /></div>
        <div><p className="r-label">Формат</p><div className="r-chips">{FORMATS.map((x) => <button key={x} className="r-chip" aria-pressed={f.work_format === x} onClick={() => setF({ ...f, work_format: x })}>{x}</button>)}</div></div>
      </div>
      <p className="r-small r-mute">Кандидат увидит компанию, предложение и&nbsp;вилку. Его имя и&nbsp;контакты откроются, когда он примет приглашение.</p>
      <div className="acts"><button className="r-btn r-btn--main" disabled={!ok} onClick={send}>Отправить приглашение</button></div>
    </Modal>
  );
}

// ── Приглашения: статусы ───────────────────────────────────────────
function Sent() {
  const { state, act } = useStore();
  const [fb, setFb] = useState(null);
  const [note, setNote] = useState('');
  const sendFb = (ok) => act(() => post('emp', `/employer/invites/${fb.id}/feedback`, { grade_ok: ok, note }), 'emp').then(() => { setFb(null); setNote(''); });
  const list = state.emp.invites;
  const [open, setOpen] = useState(null);
  if (!list.length) return <Empty img="./empty-invite.svg" title="Вы ещё никого не пригласили">Найдите категорию во&nbsp;вкладке «Подбор» и&nbsp;отправьте приглашение с&nbsp;вилкой.</Empty>;
  return (<>
    <div className="tablewrap scroll-x"><table className="r-table">
      <thead><tr><th>Кандидат</th><th>Предложение</th><th>Вилка</th><th>Статус</th><th>Контакты</th></tr></thead>
      <tbody>{list.map((i) => (
        <tr key={i.id}><td><button className="linkish" onClick={() => setOpen(i)}>{i.candidate_name || `Кандидат №${i.candidate_id}`}</button></td><td>{i.title}</td><td className="r-num">{fmtRange(i.salary_from, i.salary_to)}</td><td><Status s={i.status} />{i.reason ? <span className="r-small r-mute"> · {i.reason}</span> : null}</td>
          <td>{i.status === 'принято' ? <><ContactCell id={i.candidate_id} /> <button className="r-btn r-btn--sm" onClick={() => setFb(i)}>{i.feedback ? (i.feedback.grade_ok ? 'Грейд подтверждён' : 'Грейд завышен') : 'Итог встречи…'}</button></> : <span className="r-small r-mute">скрыты</span>}</td></tr>))}</tbody>
    </table></div>
    {fb && <Modal title="Итог встречи" onClose={() => setFb(null)}><p className="r-small r-mute">Подтвердился ли грейд кандидата на встрече? Ответ станет фактом его профиля с меткой <Mark src="interview" /> и калибрует тест. Это второе подтверждение, которого онлайн-тест дать не может.</p><div className="r-field wide"><label className="r-label" htmlFor="fbn">Коротко, необязательно</label><input id="fbn" className="r-input" value={note} onChange={(e) => setNote(e.target.value)} /></div><div className="acts"><button className="r-btn r-btn--main" onClick={() => sendFb(true)}>Грейд подтвердился</button><button className="r-btn" onClick={() => sendFb(false)}>Грейд завышен</button></div></Modal>}
    {open && <Modal title={open.title} wide onClose={() => setOpen(null)}><p className="r-small">Статус: <Status s={open.status} /> · {open.log.map((l) => `${l.s} ${new Date(l.t).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })}`).join(' → ')}</p>{open.talk && <Negotiation talk={open.talk} company={state.emp.company.name} who={`Кандидат №${String(open.candidate_id).padStart(3, '0')}`} side="emp" instant />}</Modal>}
  </>);
}

function ContactCell({ id }) {
  const [c, setC] = useState(null);
  useEffect(() => { get('emp', `/employer/candidates/${id}`).then(setC).catch(() => {}); }, [id]);
  return c?.contacts ? <span className="r-small">{c.contacts.name} · {c.contacts.email}{c.contacts.phone ? ` · ${c.contacts.phone}` : ''}</span> : <span className="r-small r-mute">…</span>;
}

function Vacs() {
  const { state, act } = useStore();
  const [form, setForm] = useState(false);
  const [resp, setResp] = useState({});
  const loadResp = (id) => get('emp', `/employer/vacancies/${id}/responses`).then((r) => setResp((p) => ({ ...p, [id]: r }))).catch(() => {});
  useEffect(() => { state.emp.vacancies.forEach((v) => loadResp(v.id)); }, [state.emp.vacancies]);
  const setStatus = (v, r, status) => act(() => post('emp', `/employer/responses/${r.id}?status=${encodeURIComponent(status)}`)).then(() => loadResp(v.id));
  return (
    <div className="stack">
      {state.emp.vacancies.map((v) => (
        <div key={v.id} className="r-card r-card--flat">
          <p className="r-micro">{spec(v.spec).name} · {gradeName(v.grade)} · {v.work_format}</p>
          <p className="r-h3">{v.title}</p>
          <p className="r-vac__pay">{fmtRange(v.salary_from, v.salary_to)}</p>
          <p className="r-small">{v.team}</p>
          <p className="r-label mt-s">Отклики · {(resp[v.id] || []).length}</p>
          {(resp[v.id] || []).length ? resp[v.id].map((r) => <div key={r.id} className="resp"><span>{r.contacts ? `${r.contacts.name} · ${r.contacts.email}` : r.candidate?.display}{r.candidate ? ` · ${gradeName(r.candidate.grade)}` : ''}</span><Status s={r.status} />{['отправлено', 'просмотрено'].includes(r.status) && <><button className="r-btn r-btn--sm" onClick={() => setStatus(v, r, 'принято')}>Пригласить на&nbsp;встречу</button><button className="r-btn r-btn--sm r-btn--quiet" onClick={() => setStatus(v, r, 'отклонено')}>Отказать</button></>}</div>) : <p className="r-small r-mute">Пока нет. Откликнуться можно из&nbsp;кабинета кандидата.</p>}
        </div>))}
      <button className="r-btn" onClick={() => setForm(true)}>Новая вакансия…</button>
      {form && <VacancyForm onClose={() => setForm(false)} />}
    </div>
  );
}

function VacancyForm({ onClose }) {
  const { act } = useStore();
  const [f, setF] = useState({ title: '', spec: 'backend', grade: 2, stack: ['Python'], salary_from: '', salary_to: '', work_format: 'гибрид', team: '', tasks: '' });
  const ok = f.title && +f.salary_from > 0 && +f.salary_to >= +f.salary_from;
  const save = () => act(() => post('emp', '/employer/vacancies', { ...f, salary_from: +f.salary_from, salary_to: +f.salary_to, tasks: f.tasks.split('\n').map((s) => s.trim()).filter(Boolean) }), 'emp').then(onClose);
  return (
    <Modal title="Новая вакансия" onClose={onClose}>
      <div className="r-field wide"><label className="r-label" htmlFor="vt">Название</label><input id="vt" className="r-input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
      <div className="r-chips scroll-x nowrap">{SPECS.map((s) => <button key={s.id} className="r-chip" aria-pressed={f.spec === s.id} onClick={() => setF({ ...f, spec: s.id, stack: s.stack.slice(0, 2) })}>{s.name}</button>)}</div>
      <div className="r-chips scroll-x nowrap mt-s">{GRADES.map((g) => <button key={g.id} className="r-chip" aria-pressed={f.grade === g.id} onClick={() => setF({ ...f, grade: g.id })}>{g.name}</button>)}</div>
      <div className="r-chips mt-s">{spec(f.spec).stack.map((s) => <button key={s} className="r-chip" aria-pressed={f.stack.includes(s)} onClick={() => setF({ ...f, stack: f.stack.includes(s) ? f.stack.filter((x) => x !== s) : [...f.stack, s] })}>{s}</button>)}</div>
      <div className="grid2 tight">
        <div className="r-field"><label className="r-label" htmlFor="vf">Зарплата от, ₽</label><input id="vf" className="r-input r-num" inputMode="numeric" value={f.salary_from} onChange={(e) => setF({ ...f, salary_from: e.target.value.replace(/\D/g, '') })} /></div>
        <div className="r-field"><label className="r-label" htmlFor="vo">до, ₽</label><input id="vo" className="r-input r-num" inputMode="numeric" value={f.salary_to} onChange={(e) => setF({ ...f, salary_to: e.target.value.replace(/\D/g, '') })} /><span className="r-hint">Без вилки вакансия не сохранится.</span></div>
      </div>
      <div className="r-chips">{FORMATS.map((x) => <button key={x} className="r-chip" aria-pressed={f.work_format === x} onClick={() => setF({ ...f, work_format: x })}>{x}</button>)}</div>
      <div className="r-field wide"><label className="r-label" htmlFor="vm">Команда</label><textarea id="vm" className="r-area" rows={2} value={f.team} onChange={(e) => setF({ ...f, team: e.target.value })} /></div>
      <div className="r-field wide"><label className="r-label" htmlFor="vk">Задачи на первые месяцы, по строке</label><textarea id="vk" className="r-area" rows={3} value={f.tasks} onChange={(e) => setF({ ...f, tasks: e.target.value })} /></div>
      <div className="acts"><button className="r-btn r-btn--main" disabled={!ok} onClick={save}>Опубликовать</button></div>
    </Modal>
  );
}
