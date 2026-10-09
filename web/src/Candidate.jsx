/* Кабинет кандидата. Три шага до категории: вход, опрос с выбором грейда,
   адаптивный тест. Дальше — кабинет: приглашения, как меня видят, грейд,
   факты, задания, вакансии, настройки. Все данные — с сервера. */
import { useEffect, useState } from 'react';
import { useStore } from './store.jsx';
import { get, post, patch, del, setToken } from './api.js';
import { GRADES, GRADE_HINT, SPECS, FORMATS, REASONS, COOLDOWN_DAYS, spec, fmt, fmtRange, dateRu } from './const.js';
import { Mark, Modal, Trace, Empty, Tabs, Status } from './ui.jsx';
import { CandidateProfileDoc, CandStatsDoc, EmployerProfileDoc, Negotiation } from './Artifacts.jsx';
import { CandidateTasks } from './Tasks.jsx';

export default function Candidate() {
  const { state } = useStore();
  const c = state.cand;
  if (!c.authed) return <Start />;
  if (!c.profile) return <p className="page r-mute">Загружаем…</p>;
  if (c.session && !c.session.finished) return <TestRun />;
  if (!c.profile.spec || c.profile.claimed_grade == null) return <Quiz />;
  return <Cabinet />;
}

// ── 1. Вход ─────────────────────────────────────────────────────────
function Start() {
  const { loadCand, act } = useStore();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [sent, setSent] = useState(null);
  const [fspPick, setFspPick] = useState(false);
  const [accounts, setAccounts] = useState([]);
  useEffect(() => { if (fspPick && !accounts.length) get(null, '/fsp-id/accounts').then(setAccounts).catch(() => {}); }, [fspPick, accounts.length]);
  const start = () => act(async () => { const r = await post(null, '/auth/start', { email, role: 'candidate' }); setSent(r); if (r.code) setCode(r.code); });
  const confirm = (fspSub) => act(async () => {
    const r = await post(null, '/auth/confirm', { email, code, consent: true });
    setToken('cand', r.token);
    if (fspSub) {
      // Мок ФСП ID: authorize отдаёт code редиректом; здесь берём его из адреса.
      const u = `/api/fsp-id/authorize?sub=${fspSub}&redirect_uri=${encodeURIComponent(location.origin + '/cb')}`;
      const resp = await fetch(u, { redirect: 'manual' });
      const loc = resp.headers.get('location') || resp.url || '';
      const m = /code=([^&]+)/.exec(loc) || /code=([^&]+)/.exec(await resp.text().catch(() => ''));
      if (m) await post('cand', '/candidate/fsp/link', { code: m[1] });
    }
  }, 'cand');
  const fspLogin = (a) => { setEmail(a.email || `${a.sub}@fsp.example`); setFspPick(a.sub); };
  useEffect(() => { if (typeof fspPick === 'string' && email) act(async () => { const r = await post(null, '/auth/start', { email, role: 'candidate' }); setCode(r.code); setSent(r); }); }, [fspPick]); // eslint-disable-line
  const okMail = /.+@.+\..+/.test(email);
  return (
    <div className="page">
      <div className="hero-row">
        <div>
          <p className="r-micro">Кандидат · шаг 1 из 3</p>
          <h1 className="r-h1">Работодатель придёт к&nbsp;вам сам — с&nbsp;вилкой зарплаты в&nbsp;первом сообщении</h1>
          <p className="r-mute">Резюме не&nbsp;рассылаете. Проходите опрос и&nbsp;тест на&nbsp;свой грейд, попадаете в&nbsp;категорию, и&nbsp;компании пишут вам первыми. Контакты видят только те, чьё приглашение вы&nbsp;приняли.</p>
        </div>
        <img src="./sign-master.svg" alt="" className="hero-sign" />
      </div>
      <div className="grid2">
        <div className="r-card">
          <h2 className="r-h3">Войти через ФСП&nbsp;ID</h2>
          <p className="r-small r-mute">Если вы&nbsp;участвовали в&nbsp;соревнованиях федерации, результаты сами встанут в&nbsp;профиль с&nbsp;меткой <Mark src="fsp" />.</p>
          {!fspPick ? <button className="r-btn r-btn--main" onClick={() => setFspPick(true)}>Войти через ФСП&nbsp;ID</button> : typeof fspPick === 'string' ? (
            <div className="stack-sm">
              <p className="r-small">Учётная запись ФСП&nbsp;ID выбрана, почта <b>{email}</b>. Код подтверждения{sent?.code ? <> (демо-режим, письмо не&nbsp;уходит): <b className="r-num">{sent.code}</b></> : ' отправлен'}.</p>
              <button className="r-btn r-btn--main" disabled={!code} onClick={() => confirm(fspPick)}>Подтвердить и&nbsp;привязать ФСП&nbsp;ID</button>
            </div>
          ) : (
            <div className="stack-sm">
              <p className="r-small"><b>Демо:</b> тестовый стенд ФСП&nbsp;ID. Выберите учётную запись</p>
              {accounts.map((a) => <button key={a.sub} className="r-btn" onClick={() => fspLogin(a)}>{a.name} · {a.history ? 'с историей соревнований' : 'без истории'}</button>)}
            </div>
          )}
        </div>
        <div className="r-card r-card--flat">
          <h2 className="r-h3">Или по&nbsp;почте</h2>
          <div className="r-field"><label className="r-label" htmlFor="em">Почта</label><input id="em" className="r-input" type="email" value={email} placeholder="name@mail.ru" onChange={(e) => setEmail(e.target.value)} disabled={typeof fspPick === 'string'} /></div>
          {!sent || typeof fspPick === 'string' ? (typeof fspPick !== 'string' && <button className="r-btn" disabled={!okMail} onClick={start}>Получить код</button>) : (
            <div className="stack-sm">
              <p className="r-small">{sent.code ? <>Демо-режим: письмо не&nbsp;уходит, код&nbsp;— <b className="r-num">{sent.code}</b>.</> : <>Код ушёл на&nbsp;<b>{email}</b>.</>} ФСП&nbsp;ID можно привязать позже в&nbsp;настройках.</p>
              <div className="r-field"><label className="r-label" htmlFor="cd">Код из письма</label><input id="cd" className="r-input r-num" value={code} onChange={(e) => setCode(e.target.value)} /></div>
              <label className="r-switch"><input type="checkbox" defaultChecked /><i />Согласен на&nbsp;обработку и&nbsp;публикацию данных профиля (152-ФЗ)</label>
              <button className="r-btn r-btn--main" disabled={code.length < 6} onClick={() => confirm(null)}>Подтвердить почту</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 2. Опрос и заявленный грейд ─────────────────────────────────────
function Quiz() {
  const { state, act } = useStore();
  const m = state.cand.profile;
  const [f, setF] = useState({ spec: m.spec || 'backend', stack: m.stack?.length ? m.stack : ['Python', 'PostgreSQL'], work_format: m.work_format || 'гибрид', salary: m.salary || 250000, years: m.years || 3, claimed: m.claimed_grade ?? 2, name: m.name || '' });
  const [pdf, setPdf] = useState(null);
  const [mode, setMode] = useState('full');
  const sp = spec(f.spec);
  const toggle = (s) => setF({ ...f, stack: f.stack.includes(s) ? f.stack.filter((x) => x !== s) : [...f.stack, s] });
  const upload = (file) => act(async () => {
    const fd = new FormData(); fd.append('file', file);
    const r = await fetch('/api/candidate/resume', { method: 'POST', headers: { Authorization: `Bearer ${JSON.parse(localStorage.getItem('razryad-tokens')).cand}` }, body: fd }).then((x) => x.json());
    setPdf(r.parsed); if (r.parsed.stack?.length) setF((v) => ({ ...v, stack: r.parsed.stack, years: r.parsed.years || v.years }));
  });
  const start = () => act(async () => {
    await patch('cand', '/candidate/profile', { name: f.name, spec: f.spec, stack: f.stack, work_format: f.work_format, salary: +f.salary, years: +f.years, claimed_grade: f.claimed });
    await post('cand', '/test/start', { claimed: f.claimed, mode });
  }, 'cand');
  return (
    <div className="page">
      <p className="r-micro">Кандидат · шаг 2 из 3</p>
      <h1 className="r-h1">Опрос: кто вы&nbsp;в&nbsp;ИТ</h1>
      <div className="r-card r-card--flat stack">
        <div className="pdf-row">
          <label className="r-btn r-btn--sm">Заполнить из&nbsp;резюме…<input type="file" accept=".pdf,.txt,.md" hidden onChange={(e) => e.target.files[0] && upload(e.target.files[0])} /></label>
          {pdf && <span className="r-small">Распознано: стек {pdf.stack.join(', ') || '—'}, стаж {pdf.years || '—'} — всё с&nbsp;меткой <Mark src="word" />, пока не&nbsp;подтвердит тест</span>}
        </div>
        <div className="grid2 tight">
          <div className="r-field"><label className="r-label" htmlFor="nm">Имя</label><input id="nm" className="r-input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Видно только после вашего согласия" /></div>
          <div className="r-field"><label className="r-label" htmlFor="yr">Стаж, лет</label><input id="yr" className="r-input r-num" inputMode="numeric" value={f.years} onChange={(e) => setF({ ...f, years: e.target.value.replace(/\D/g, '') })} /></div>
        </div>
        <div><p className="r-label">Отрасль</p><div className="r-chips"><button className="r-chip" aria-pressed="true">Информационные технологии</button></div></div>
        <div><p className="r-label">Специализация</p><div className="r-chips">{SPECS.map((s) => <button key={s.id} className="r-chip" aria-pressed={f.spec === s.id} onClick={() => setF({ ...f, spec: s.id, stack: s.stack.slice(0, 2) })}>{s.name}</button>)}</div></div>
        <div><p className="r-label">Стек</p><div className="r-chips">{sp.stack.map((s) => <button key={s} className="r-chip" aria-pressed={f.stack.includes(s)} onClick={() => toggle(s)}>{s}</button>)}</div></div>
        <div className="grid2 tight">
          <div><p className="r-label">Формат</p><div className="r-chips">{FORMATS.map((x) => <button key={x} className="r-chip" aria-pressed={f.work_format === x} onClick={() => setF({ ...f, work_format: x })}>{x}</button>)}</div></div>
          <div className="r-field"><label className="r-label" htmlFor="sal">Ожидания, ₽ на&nbsp;руки</label><input id="sal" className="r-input r-num" inputMode="numeric" value={f.salary} onChange={(e) => setF({ ...f, salary: e.target.value.replace(/\D/g, '') })} /></div>
        </div>
      </div>

      <h2 className="r-h2 mt">Ваш грейд — как вы&nbsp;его видите</h2>
      <p className="r-mute">Тест проверит именно его. Не&nbsp;пройдёте — сразу предложим тест на&nbsp;ступень ниже, грейд сам не&nbsp;понизится. Пройдёте уверенно — предложим отдельный тест на&nbsp;ступень выше.</p>
      <div className="grades scroll-x">
        {GRADES.map((g) => (
          <button key={g.id} className={`grade-card r-card ${f.claimed === g.id ? 'is-on' : ''}`} onClick={() => setF({ ...f, claimed: g.id })} aria-pressed={f.claimed === g.id}>
            <span className="r-micro">{g.short}</span><b>{g.name}</b><span className="r-small">{GRADE_HINT[g.id]}</span>
          </button>
        ))}
      </div>
      <div className="acts">
        <button className="r-btn r-btn--main r-btn--lg" onClick={start} disabled={!f.stack.length}>Начать тест · {mode === 'full' ? '20–30 минут' : '3–5 минут'}</button>
        <div className="seg" role="group" aria-label="Режим теста"><button aria-pressed={mode === 'full'} onClick={() => setMode('full')}>Полный</button><button aria-pressed={mode === 'express'} onClick={() => setMode('express')} title="Для показа жюри: 3–4 задания, погрешность выше">Экспресс</button></div>
      </div>
    </div>
  );
}

// ── 3. Адаптивный тест ──────────────────────────────────────────────
function TestRun() {
  const { state, act, dispatch } = useStore();
  const s = state.cand.session;
  const m = state.cand.profile;
  const [pick, setPick] = useState(null);
  const [text, setText] = useState('');
  const [hood, setHood] = useState(true);
  const [last, setLast] = useState(null);
  const [events, setEvents] = useState([]);
  useEffect(() => { const b = () => setEvents((e) => [...e, { t: Date.now(), e: 'blur' }]); window.addEventListener('blur', b); return () => window.removeEventListener('blur', b); }, []);
  const cur = s.current;
  const est = s.trace[s.trace.length - 1];
  const answer = () => act(async () => {
    const r = await post('cand', '/test/answer', cur.open ? { text, events } : { pick, events });
    setLast(r.last); setPick(null); setText(''); setEvents([]);
    if (r.finished) dispatch({ type: 'ui', patch: { candTab: 'grade' } });
    dispatch({ type: 'cand', patch: { session: r } });
  }, 'cand');
  return (
    <div className="page">
      <div className="test-top">
        <div>
          <p className="r-micro">Тест · {spec(m.spec).name} · заявлено: {GRADES[s.claimed].name}{s.mode === 'express' ? ' · экспресс' : ''}</p>
          <p className="r-small r-mute">Задание {s.n + 1}. Тест закончится раньше, когда оценка станет достаточно точной.</p>
        </div>
        <label className="r-switch"><input type="checkbox" checked={hood} onChange={(e) => setHood(e.target.checked)} /><i />Под капотом</label>
      </div>
      <div className={hood ? 'test-grid' : ''}>
        <div className="r-card">
          <div className="task-head"><span className="r-micro">{cur.skill} · {cur.format}{cur.ai && <> · <span className="r-mark r-mark--code" title="Модель использовать можно: оценивается ваше решение, а не память">ИИ разрешён</span></>}</span><span className="r-micro">шаблон {cur.tpl}</span></div>
          <p className={cur.code ? 'task-q task-code' : 'task-q'}>{cur.q}</p>
          {cur.open ? (
            <div className="r-field wide"><label className="r-label" htmlFor="ans">Ваш подход</label><textarea id="ans" className="r-area" rows={6} value={text} onPaste={() => setEvents((e) => [...e, { t: Date.now(), e: 'paste' }])} onChange={(e) => setText(e.target.value)} placeholder="Что храним, где, как считаем, что отвечаем клиенту…" /><span className="r-hint">Оценивается по&nbsp;рубрике; неуверенную оценку проверяет эксперт.</span></div>
          ) : (
            <div className="opts">{cur.opts.map((o) => <button key={o} className="r-chip opt" aria-pressed={pick === o} onClick={() => setPick(o)}>{o}</button>)}</div>
          )}
          <div className="acts"><button className="r-btn r-btn--main" disabled={cur.open ? text.trim().length < 20 : pick == null} onClick={answer}>Ответить</button></div>
        </div>
        {hood && (
          <aside className="hood r-card r-card--flat">
            <p className="r-micro">Оценка навыка θ</p>
            <p className="hood-num r-num">{est.theta.toFixed(2)} <span className="r-mute">± {est.se.toFixed(2)}</span></p>
            <Trace trace={s.trace} claimed={s.claimed} height={200} />
            <p className="r-small"><b>Почему это задание.</b> Из&nbsp;неиспробованных шаблонов сервер взял три самых информативных при θ&nbsp;=&nbsp;{est.theta.toFixed(2)} и&nbsp;выбрал одно случайно — так ни&nbsp;один шаблон не&nbsp;достаётся всем:</p>
            <ul className="r-small hood-list">{s.why.map((w) => <li key={w.id} className={w.id === cur.tpl ? 'is-on' : ''}>{w.id} {w.title} — информация {w.info}</li>)}</ul>
            <p className="r-small">Цифры и&nbsp;сюжет в&nbsp;условии собраны из&nbsp;зерна {cur.seed} — у&nbsp;соседа будут другие. Эталон ответа остаётся на&nbsp;сервере.</p>
            {last && <p className="r-small last">Прошлый ответ «{last.title}»: {last.score >= 0.5 ? 'верно' : 'неверно'}; θ {last.theta_before.toFixed(2)} → {last.theta_after.toFixed(2)}</p>}
          </aside>
        )}
      </div>
    </div>
  );
}

// ── 4. Кабинет ──────────────────────────────────────────────────────
function Cabinet() {
  const { state, dispatch } = useStore();
  const c = state.cand;
  const fresh = c.invites.filter((i) => i.status === 'отправлено').length;
  const tab = state.ui.candTab;
  return (
    <div className="page">
      <Tabs value={tab} onChange={(t) => dispatch({ type: 'ui', patch: { candTab: t } })} items={[['invites', 'Приглашения', fresh], ['view', 'Как меня видят'], ['stats', 'Статистика'], ['tasks', 'Задания'], ['grade', 'Категория и грейд'], ['profile', 'Факты'], ['vac', 'Вакансии'], ['settings', 'Настройки']]} />
      {tab === 'grade' && <GradeTab />}
      {tab === 'tasks' && <CandidateTasks />}
      {tab === 'view' && <CandidateProfileDoc profile={c.profile} tests={c.tests} rank={c.rank} />}
      {tab === 'stats' && <CandStatsDoc profile={c.profile} rank={c.rank} stats={c.stats} />}
      {tab === 'invites' && <InvitesTab />}
      {tab === 'profile' && <ProfileTab />}
      {tab === 'vac' && <VacTab />}
      {tab === 'settings' && <SettingsTab />}
    </div>
  );
}

function GradeTab() {
  const { state, act } = useStore();
  const m = state.cand.profile;
  const t = state.cand.tests[0];
  const v = t?.verdict;
  const since = m.grade_since ? Math.floor((Date.now() - new Date(m.grade_since)) / 86400000) : null;
  const left = since == null ? 0 : Math.max(0, COOLDOWN_DAYS - since);
  const retake = (g, mode = 'full') => act(() => post('cand', '/test/start', { claimed: g, mode }), 'cand');
  return (
    <div className="stack">
      {m.grade != null ? (
        <div className="r-card r-card--blue cat-card">
          <p className="r-micro on-blue">Ваша категория — её видит работодатель</p>
          <p className="cat-name">{spec(m.spec).name} · {GRADES[m.grade].name}</p>
          <p className="r-num">θ = {m.theta.toFixed(2)} ± {m.se.toFixed(2)} · подтверждено {dateRu(m.grade_since)}</p>
        </div>
      ) : (
        <div className="r-card r-card--sun"><p className="r-h3">{spec(m.spec).name} · {GRADES[m.claimed_grade].name} <span className="r-mark r-mark--warn">грейд не подтверждён</span></p><p>Вы в&nbsp;выдаче своей категории, но&nbsp;ниже всех, кто подтвердил грейд тестом. Пройдите тест на&nbsp;ступень ниже или&nbsp;повторите заявленный позже.</p></div>
      )}
      {t && (
        <div className="r-card r-card--flat">
          <h2 className="r-h3">Последний тест · {dateRu(t.date)}{t.mode === 'express' ? ' · экспресс' : ''}</h2>
          {v.kind === 'ok' && <p>Заявленный грейд «{GRADES[t.claimed].name}» <b>подтверждён</b> за&nbsp;{t.n} заданий.{v.offer_up ? ' Результат уверенно выше границы — доступен отдельный тест на ступень выше.' : ''}</p>}
          {v.kind === 'below' && <p>Заявленный «{GRADES[t.claimed].name}» не&nbsp;подтверждён: оценка соответствует уровню «{GRADES[v.measured].name}». {v.close ? 'Вы были близко к границе.' : ''} Тест на&nbsp;ступень ниже доступен сразу, повтор заявленного — через {COOLDOWN_DAYS}&nbsp;дней.</p>}
          <Skills rows={t.skills} />
          {t.conduct && <p className="r-small r-mute">Протокол теста: {t.conduct.items} заданий{t.conduct.seconds != null ? `, ${Math.round(t.conduct.seconds / 60)} мин` : ''}, заданий с открытым ИИ — {t.conduct.ai_items}, вставок из буфера — {t.conduct.paste}, уходов со вкладки — {t.conduct.blur}. Это видит работодатель; штрафа нет.</p>}
          <div className="acts">
            {v.kind === 'below' && <button className="r-btn r-btn--main" onClick={() => retake(v.offer_down)}>Пройти тест на «{GRADES[v.offer_down].name}»</button>}
            {v.kind === 'ok' && v.offer_up && <button className="r-btn r-btn--main" onClick={() => retake(t.claimed + 1)}>Тест на «{GRADES[t.claimed + 1].name}»</button>}
            {v.kind === 'ok' && !v.offer_up && m.grade < 4 && <button className="r-btn" disabled title="Смена грейда — не чаще раза в 90 дней">Тест на ступень выше · через {left}&nbsp;дн.</button>}
          </div>
        </div>
      )}
      {state.cand.tests.length > 0 && (
        <div className="tablewrap scroll-x"><table className="r-table">
          <thead><tr><th>Дата</th><th>Заявлено</th><th>Итог</th><th>Оценка</th><th>Заданий</th></tr></thead>
          <tbody>{state.cand.tests.map((x) => <tr key={x.id}><td>{new Date(x.date).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })}</td><td>{GRADES[x.claimed].name}</td><td>{x.verdict.kind === 'ok' ? 'подтверждён' : 'не подтверждён'}</td><td className="r-num">{x.theta.toFixed(2)} ± {x.se.toFixed(2)}</td><td className="r-num">{x.n}</td></tr>)}</tbody>
        </table></div>
      )}
    </div>
  );
}

/* Карточка роста: тест разложен по навыкам. Кандидат видит, какой навык тянет вниз. */
function Skills({ rows }) {
  if (!rows?.length) return null;
  const sorted = [...rows].sort((a, b) => a.theta - b.theta);
  return (
    <div className="growth">
      <p className="r-label">По навыкам</p>
      <div className="tablewrap scroll-x"><table className="r-table">
        <thead><tr><th>Навык</th><th>Оценка</th><th>Заданий</th></tr></thead>
        <tbody>{sorted.map((r) => <tr key={r.name}><td>{r.name}</td><td className="r-num">{r.theta.toFixed(2)} ± {r.se.toFixed(2)}</td><td className="r-num">{r.items}</td></tr>)}</tbody>
      </table></div>
      <p className="doc-note">Тянет вниз: <b>{sorted[0].name.toLowerCase()}</b>. На пересдаче система снова даст задания этого навыка — других вариантов, той же трудности.</p>
    </div>
  );
}

function InvitesTab() {
  const { state, act } = useStore();
  const list = state.cand.invites;
  const [open, setOpen] = useState(null);
  const inv = list.find((i) => i.id === open);
  const show = (i) => { setOpen(i.id); if (i.status === 'отправлено') act(() => post('cand', `/candidate/invites/${i.id}`, { status: 'просмотрено' }), 'cand'); };
  if (!list.length) return <Empty img="./empty-invite.svg" title="Приглашений пока нет">{state.cand.profile.grade != null ? 'Работодатели видят вашу категорию. Первое приглашение придёт с вилкой зарплаты.' : 'Вы в выдаче с меткой «грейд не подтверждён»; подтвердите грейд тестом, чтобы подняться.'}</Empty>;
  return (
    <div className="stack">
      {list.map((i) => (
        <button key={i.id} className="r-card inv-row" onClick={() => show(i)}>
          <div><p className="r-micro">{i.company}</p><p className="r-h3">{i.title}</p><p className="r-small r-mute">{i.text}</p></div>
          <div className="inv-side"><span className="r-vac__pay">{fmtRange(i.salary_from, i.salary_to)}</span><Status s={i.status} /></div>
        </button>
      ))}
      {inv && <InviteModal inv={inv} onClose={() => setOpen(null)} />}
    </div>
  );
}

function InviteModal({ inv, onClose }) {
  const { act } = useStore();
  const [mode, setMode] = useState(null);
  const [emp, setEmp] = useState(null);
  useEffect(() => { if (mode === 'company' && !emp) get('cand', `/candidate/employers/${inv.employer.id}`).then(setEmp).catch(() => {}); }, [mode, emp, inv.employer.id]);
  const decide = (status, reason) => act(() => post('cand', `/candidate/invites/${inv.id}`, { status, reason }), 'cand').then(() => setMode(null));
  return (
    <Modal title={inv.title} onClose={onClose} wide>
      <p className="r-micro">{inv.company}</p>
      <p className="r-vac__pay">{fmtRange(inv.salary_from, inv.salary_to)} <span className="r-small r-mute">на&nbsp;руки</span></p>
      <p>{inv.text}</p>
      <p className="r-small"><b>Связь:</b> {inv.status === 'принято' ? inv.contact : 'откроется после вашего согласия'} · <b>формат:</b> {inv.work_format || '—'}</p>
      {inv.status === 'принято' && <p className="r-toast">Вы приняли приглашение — компания видит ваши контакты</p>}
      {inv.status === 'отклонено' && <p className="r-small">Отклонено: {inv.reason}</p>}
      <div className="acts"><button className="r-btn r-btn--sm" onClick={() => setMode('company')}>Профиль компании…</button>{inv.talk && <button className="r-btn r-btn--sm" onClick={() => setMode('nego')}>Протокол переговоров агентов…</button>}</div>
      {mode === 'company' && emp && <EmployerProfileDoc e={emp} offer={{ from: inv.salary_from, to: inv.salary_to }} />}
      {mode === 'nego' && <Negotiation talk={inv.talk} company={inv.company} who="Вы" side="cand" instant />}
      {mode === 'no' && (
        <div className="stack-sm"><p className="r-label">Причина — компания её увидит и&nbsp;поправит подборку</p><div className="r-chips">{REASONS.map((r) => <button key={r} className="r-chip" onClick={() => decide('отклонено', r)}>{r}</button>)}</div></div>
      )}
      {['отправлено', 'просмотрено'].includes(inv.status) && (
        <div className="acts">
          <button className="r-btn r-btn--main" onClick={() => decide('принято')}>Принять</button>
          <button className="r-btn r-btn--quiet" onClick={() => setMode('no')}>Отклонить…</button>
        </div>
      )}
    </Modal>
  );
}

function ProfileTab() {
  const { state, act } = useStore();
  const m = state.cand.profile;
  const setFact = (k, approved) => act(() => patch('cand', `/candidate/facts/${encodeURIComponent(k)}?approved=${approved}`), 'cand');
  const hide = (id, hidden) => act(() => patch('cand', `/candidate/fsp/${id}?hidden=${hidden}`), 'cand');
  const [q, setQ] = useState({ k: 'Почему ищет', v: '' });
  const addFact = () => act(() => post('cand', '/candidate/facts', { k: q.k, v: q.v, approved: true }), 'cand').then(() => setQ({ ...q, v: '' }));
  return (
    <div className="stack">
      <div className="r-card">
        <div className="r-cand">
          <div className="r-avatar">{(m.name || 'Вы').split(' ').map((w) => w[0]).join('').slice(0, 2)}</div>
          <div><p className="r-cand__name">{m.name || 'Без имени'}</p><p className="r-cand__role">{spec(m.spec).name}{m.grade != null ? ` · ${GRADES[m.grade].name}` : ` · ${GRADES[m.claimed_grade].name} (не подтверждён)`} · {m.work_format} · ожидания {fmt(m.salary)}</p>
            <div className="r-cand__marks"><Mark src="fsp" /> подтвердила федерация <Mark src="test" /> подтвердил тест <Mark src="word" /> со&nbsp;слов</div></div>
          <div className="r-cand__act"><a className="r-btn r-btn--sm" href="/api/candidate/resume.txt" onClick={(e) => { e.preventDefault(); get('cand', '/candidate/resume.txt').then((r) => { const w = window.open('', '_blank'); w.document.write(`<pre style="font:14px/1.5 JetBrains Mono,monospace;padding:24px">${r.text.replace(/</g, '&lt;')}</pre>`); w.print(); }); }}>PDF-профиль…</a></div>
        </div>
      </div>
      <h2 className="r-h3">Факты профиля</h2>
      <p className="r-small r-mute">Включённые факты видит работодатель и&nbsp;по&nbsp;ним отвечает ваш агент. Выключенные агент не&nbsp;назовёт — скажет, что вы&nbsp;уточните сами.</p>
      <div className="tablewrap scroll-x"><table className="r-table">
        <thead><tr><th>Факт</th><th>Значение</th><th>Источник</th><th>Видно</th></tr></thead>
        <tbody>{m.facts.map((f) => <tr key={f.k}><td>{f.k}</td><td>{f.v}</td><td><Mark src={f.src} /></td><td><label className="r-switch"><input type="checkbox" checked={f.approved} onChange={(e) => setFact(f.k, e.target.checked)} /><i /></label></td></tr>)}</tbody>
      </table></div>
      <div className="r-card r-card--flat stack-sm">
        <p className="r-micro">Вопрос рекрутера · ответ станет фактом «со слов»</p>
        <div className="r-chips">{['Почему ищет', 'Роль в команде', 'Английский', 'Переезд'].map((k) => <button key={k} className="r-chip" aria-pressed={q.k === k} onClick={() => setQ({ ...q, k })}>{k}</button>)}</div>
        <div className="r-field wide"><input className="r-input" value={q.v} onChange={(e) => setQ({ ...q, v: e.target.value })} placeholder="Коротко, как сказали бы рекрутеру" aria-label="Ответ" /></div>
        <button className="r-btn r-btn--sm" disabled={q.v.trim().length < 3} onClick={addFact}>Сохранить факт</button>
      </div>
      <h2 className="r-h3">Соревнования ФСП</h2>
      {m.fsp?.length ? m.fsp.map((e) => (
        <div key={e.id} className={`r-ach r-card r-card--flat ${e.hidden ? 'is-hidden' : ''}`}><div className="r-rank"><b>{e.place}</b>место</div><div><p><b>{e.event}</b>, {e.year}</p><p className="r-small">{e.place} из&nbsp;{e.participants} · {e.level} · {e.discipline} · разряд: {e.rank} <Mark src="fsp" /></p></div>
          <label className="r-switch" title="Скрыть можно, изменить нельзя"><input type="checkbox" checked={!e.hidden} onChange={(ev) => hide(e.id, !ev.target.checked)} /><i /></label></div>
      )) : <Empty img="./empty-fsp.svg" title={m.fsp_id ? 'В реестре ФСП записей нет' : 'ФСП ID не привязан'}>Профиль работает и&nbsp;без них: место в&nbsp;категории решает тест. Соревнования добавляют вес внутри категории, но&nbsp;их отсутствие не&nbsp;штрафуется.</Empty>}
    </div>
  );
}

function VacTab() {
  const { state, act } = useStore();
  const resp = state.cand.responses;
  return (
    <div className="stack">
      <p className="r-small r-mute">Пока приглашений мало, можно откликнуться самим. Вилка указана у&nbsp;каждой вакансии.</p>
      {state.cand.vacancies.map((v) => {
        const r = resp.find((x) => x.vacancy_id === v.id);
        return (
          <div key={v.id} className="r-card r-card--flat inv-row">
            <div><p className="r-micro">{v.company} · {spec(v.spec).name} · {GRADES[v.grade].name}</p><p className="r-h3">{v.title}</p><p className="r-small">{v.stack.join(', ')} · {v.work_format}</p></div>
            <div className="inv-side"><span className="r-vac__pay">{fmtRange(v.salary_from, v.salary_to)}</span>{r ? <Status s={r.status} /> : <button className="r-btn r-btn--sm" onClick={() => act(() => post('cand', `/candidate/vacancies/${v.id}/respond`), 'cand')}>Откликнуться</button>}</div>
          </div>
        );
      })}
    </div>
  );
}

function SettingsTab() {
  const { state, act, loadCand } = useStore();
  const m = state.cand.profile;
  const p = (k, v) => act(() => patch('cand', '/candidate/profile', { privacy: { ...m.privacy, [k]: v } }), 'cand');
  const [accounts, setAccounts] = useState(null);
  const link = (sub) => act(async () => {
    const resp = await fetch(`/api/fsp-id/authorize?sub=${sub}&redirect_uri=${encodeURIComponent(location.origin + '/cb')}`, { redirect: 'manual' });
    const m2 = /code=([^&]+)/.exec(resp.headers.get('location') || resp.url || '') || /code=([^&]+)/.exec(await resp.text().catch(() => ''));
    if (m2) await post('cand', '/candidate/fsp/link', { code: m2[1] });
  }, 'cand').then(() => setAccounts(null));
  return (
    <div className="r-card r-card--flat stack">
      <h2 className="r-h3">Что видно работодателю</h2>
      <label className="r-switch"><input type="checkbox" checked={m.privacy.fsp} onChange={(e) => p('fsp', e.target.checked)} /><i />Результаты соревнований ФСП</label>
      <label className="r-switch"><input type="checkbox" checked={m.privacy.salary} onChange={(e) => p('salary', e.target.checked)} /><i />Ожидания по&nbsp;зарплате</label>
      <label className="r-switch"><input type="checkbox" checked={!!m.privacy.city} onChange={(e) => p('city', e.target.checked)} /><i />Город</label>
      <label className="r-switch"><input type="checkbox" checked={m.visible} onChange={(e) => act(() => patch('cand', '/candidate/profile', { visible: e.target.checked }), 'cand')} /><i />Показывать меня в&nbsp;банке кандидатов</label>
      <p className="r-small r-mute">Имя и&nbsp;контакты не&nbsp;видны никогда до&nbsp;вашего согласия.</p>
      <h2 className="r-h3">ФСП&nbsp;ID</h2>
      {m.fsp_id ? <p>Привязан · {m.fsp_id} <button className="r-btn r-btn--sm r-btn--quiet" onClick={() => act(() => del('cand', '/candidate/fsp/link'), 'cand')}>Отвязать</button></p>
        : accounts ? <div className="stack-sm">{accounts.map((a) => <button key={a.sub} className="r-btn r-btn--sm" onClick={() => link(a.sub)}>{a.name} · {a.history ? 'с историей' : 'без истории'}</button>)}</div>
        : <button className="r-btn r-btn--sm" onClick={() => get(null, '/fsp-id/accounts').then(setAccounts)}>Привязать ФСП&nbsp;ID…</button>}
      <p className="r-small r-mute">Отвязали — достижения ушли из&nbsp;профиля. Изменить записи реестра нельзя, скрыть любую — можно во&nbsp;вкладке «Факты».</p>
      <h2 className="r-h3">Выход</h2>
      <button className="r-btn r-btn--sm r-btn--quiet" onClick={() => { setToken('cand', null); loadCand(); }}>Выйти из&nbsp;кабинета кандидата</button>
    </div>
  );
}
