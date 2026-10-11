/* Кабинет кандидата. Три шага до категории: вход, опрос с выбором грейда,
   адаптивный тест. Дальше — кабинет: приглашения, как меня видят, грейд,
   факты, задания, вакансии, настройки. Все данные — с сервера. */
import { useEffect, useState } from 'react';
import SignLoader from './SignLoader.jsx';
import { useStore } from './store.jsx';
import { get, post, patch, del, req, setToken } from './api.js';
import { GRADES, GRADE_HINT, SPECS, REASONS, COOLDOWN_DAYS, FSP_UPCOMING, spec, fmt, fmtRange, dateRu, cap, num, searchName, plural, ZAD, srvDate } from './const.js';
import { AddProfile, AgentCheck, AgentForm, CandTerms } from './Profiles.jsx';
import { CompanySummary, RefsTab } from './Refs.jsx';
import { Mark, Modal, Trace, Empty, Tabs, Status, Dictate, CabHead, OnbSteps, CAND_STEPS } from './ui.jsx';
import Login from './Login.jsx';
import { CandidateProfileDoc, CandStatsDoc, EmployerProfileDoc, Negotiation } from './Artifacts.jsx';
import { CandidateTasks } from './Tasks.jsx';
import doneArt from './assets/landing/test-done.svg?raw';
import CameraFlow, { CamCards } from './Camera.jsx';

export default function Candidate() {
  const { state } = useStore();
  const c = state.cand;
  if (!c.authed) return <Login only="cand" />;
  if (c.none) return <AddProfile kind="cand" />;
  if (!c.profile) return <SignLoader />;
  if (state.ui.cam) return <CameraFlow />;
  if (c.session && !c.session.finished) return <TestRun />;
  // Онбординг при каждом входе: шаги заполнены данными аккаунта, человек их проходит и подтверждает.
  const onb = state.ui.onb;
  if (onb === 'about' || !c.profile.spec || c.profile.claimed_grade == null || state.ui.quizBack) return <Quiz />;
  if (onb === 'terms' || (!c.profile.wants && c.profile.grade == null && !c.tests.length)) return <TermsStep />;
  if (onb === 'grade') return <GradeStep />;
  return <Cabinet />;
}

// ── 1. Вход ─────────────────────────────────────────────────────────
// Вход по почте или через ФСП ID: стоит на экране входа рядом с готовыми аккаунтами.
export function CandEntry() {
  const { act, dispatch } = useStore();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [consent, setConsent] = useState(false); // 152-ФЗ: согласие ставит человек, не форма
  const [sent, setSent] = useState(null);
  const [fspPick, setFspPick] = useState(false);
  const [accounts, setAccounts] = useState([]);
  useEffect(() => { if (fspPick && !accounts.length) get(null, '/fsp-id/accounts').then(setAccounts).catch(() => {}); }, [fspPick, accounts.length]);
  const start = () => act(async () => { const r = await post(null, '/auth/start', { email, role: 'candidate' }); setSent(r); if (r.code) setCode(r.code); });
  const confirm = (fspSub) => act(async () => {
    const r = await post(null, '/auth/confirm', { email, code, consent });
    setToken('cand', r.token);
    dispatch({ type: 'ui', patch: { onb: 'about', candTab: 'home' } });
    if (fspSub) {
      // Мок ФСП ID: authorize отдаёт code; из приложения просим его в теле ответа — Location редиректа браузер скрипту не отдаёт.
      const { code: fspCode } = await get(null, `/fsp-id/authorize?sub=${fspSub}&redirect_uri=${encodeURIComponent(location.origin + '/cb')}&response_mode=json`);
      await post('cand', '/candidate/fsp/link', { code: fspCode });
    }
  }, 'all');
  const fspLogin = (a) => { setEmail(a.email || `${a.sub}@fsp.example`); setFspPick(a.sub); };
  useEffect(() => { if (typeof fspPick === 'string' && email) act(async () => { const r = await post(null, '/auth/start', { email, role: 'candidate' }); setCode(r.code); setSent(r); }); }, [fspPick]); // eslint-disable-line
  const okMail = /.+@.+\..+/.test(email);
  return (
      <div className="entry">
        <div className="r-card entry-card">
          <h2 className="r-h3">Войти через ФСП&nbsp;ID</h2>
          <p className="r-small r-mute">Если вы&nbsp;участвовали в&nbsp;соревнованиях федерации, результаты сами встанут в&nbsp;профиль с&nbsp;меткой <Mark src="fsp" />.</p>
          {!fspPick ? <div className="entry-act"><button className="r-btn r-btn--main" onClick={() => setFspPick(true)}>Войти через ФСП&nbsp;ID</button></div> : typeof fspPick === 'string' ? (
            <div className="stack-sm">
              <p className="r-small">Учётная запись ФСП&nbsp;ID выбрана, почта <b>{email}</b>. Код подтверждения{sent?.code ? <>: <b className="r-num">{sent.code}</b></> : ' отправлен'}.</p>
              <label className="r-switch"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><i />Согласен на&nbsp;обработку и&nbsp;публикацию данных профиля (152-ФЗ)</label>
              <button className="r-btn r-btn--main" disabled={!code || !consent} onClick={() => confirm(fspPick)}>Подтвердить и&nbsp;привязать ФСП&nbsp;ID</button>
            </div>
          ) : (
            <div className="stack-sm">
              <p className="r-small">Тестовый стенд ФСП&nbsp;ID. Выберите учётную запись</p>
              {accounts.map((a) => <button key={a.sub} className="r-btn" onClick={() => fspLogin(a)}>{a.name} · {a.history ? 'с историей соревнований' : 'без истории'}</button>)}
            </div>
          )}
        </div>
        <div className="r-card entry-card">
          <h2 className="r-h3">Или по&nbsp;почте</h2>
          <p className="r-small r-mute">Пришлём код подтверждения. ФСП&nbsp;ID можно привязать позже в&nbsp;настройках.</p>
          <div className="r-field wide"><label className="r-label" htmlFor="em">Почта</label><input id="em" className="r-input" type="email" value={email} placeholder="name@mail.ru" onChange={(e) => setEmail(e.target.value)} disabled={typeof fspPick === 'string'} /></div>
          {!sent || typeof fspPick === 'string' ? (typeof fspPick !== 'string' && <div className="entry-act"><button className="r-btn" disabled={!okMail} onClick={start}>Получить код</button></div>) : (
            <div className="stack-sm">
              <p className="r-small">{sent.code ? <>Код для входа&nbsp;— <b className="r-num">{sent.code}</b>.</> : <>Код ушёл на&nbsp;<b>{email}</b>.</>}</p>
              <div className="r-field wide"><label className="r-label" htmlFor="cd">Код из письма</label><input id="cd" className="r-input r-num" value={code} onChange={(e) => setCode(e.target.value)} /></div>
              <label className="r-switch"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><i />Согласен на&nbsp;обработку и&nbsp;публикацию данных профиля (152-ФЗ)</label>
              <button className="r-btn r-btn--main" disabled={code.length < 6 || !consent} onClick={() => confirm(null)}>Подтвердить почту</button>
            </div>
          )}
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
  const [way, setWay] = useState(m.stack?.length ? 'hand' : null);
  const [about, setAbout] = useState('');
  const { dispatch } = useStore();
  const sp = spec(f.spec);
  const toggle = (s) => setF({ ...f, stack: f.stack.includes(s) ? f.stack.filter((x) => x !== s) : [...f.stack, s] });
  // Распознанное из резюме или рассказа заполняет только пустые поля и остаётся «со слов», пока не подтвердит тест.
  const take = (r) => {
    const p = r.parsed; setPdf(p); setWay('hand');
    setF((v) => ({ ...v, name: v.name || p.name || '', spec: p.spec || v.spec, stack: p.stack?.length ? p.stack : v.stack, years: p.years || v.years, salary: p.salary || v.salary, work_format: p.work_format || v.work_format, claimed: p.grade ?? v.claimed })); // грейд из резюме — подсказка, выбирает кандидат
  };
  const upload = (file) => { const fd = new FormData(); fd.append('file', file); act(() => req('cand', 'POST', '/candidate/resume', fd, { form: true })).then(take); };
  const tell = () => act(() => post('cand', '/candidate/about', { text: about })).then(take);
  const next = () => act(async () => {
    await patch('cand', '/candidate/profile', { name: f.name, spec: f.spec, stack: f.stack, work_format: f.work_format, salary: +f.salary || undefined, years: +f.years, claimed_grade: f.claimed });
    dispatch({ type: 'ui', patch: { quizBack: false, onb: state.ui.onb === 'about' ? 'terms' : state.ui.onb } });
  }, 'cand');
  return (
    <div className="page">
      {state.ui.onb || !m.spec ? <OnbSteps steps={CAND_STEPS} cur={1} /> : <p className="r-micro">Профиль</p>}
      <h1 className="r-h1">Опрос: кто вы&nbsp;в&nbsp;ИТ</h1>
      {!way && (
        <div className="ways">
          <label className="r-card way"><span className="r-h3">Загрузить резюме</span><span className="r-small r-mute">PDF или DOCX, выгруженный из&nbsp;hh.ru, Хабр Карьеры или LinkedIn</span><input type="file" accept=".pdf,.docx,.txt,.md" hidden onChange={(e) => e.target.files[0] && upload(e.target.files[0])} /></label>
          <button className="r-card way" onClick={() => setWay('tell')}><span className="r-h3">Рассказать о&nbsp;себе</span><span className="r-small r-mute">Пара фраз текстом или голосом: чем занимаетесь, стек, стаж, формат, ожидания</span></button>
          <button className="r-card way" onClick={() => setWay('hand')}><span className="r-h3">Заполнить вручную</span><span className="r-small r-mute">Пять полей, около минуты</span></button>
        </div>
      )}
      {way === 'tell' && (
        <div className="r-card r-card--flat stack-sm">
          <div className="r-field wide"><label className="r-label" htmlFor="ab">О&nbsp;себе</label><Dictate value={about} onChange={setAbout}><textarea id="ab" className="r-area" rows={4} value={about} onChange={(e) => setAbout(e.target.value)} placeholder="Бэкенд на Python шесть лет, последние три — в банке, PostgreSQL и Kafka. Хочу гибрид, от 280 тысяч на руки." /></Dictate></div>
          <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--main" disabled={about.trim().length < 20} onClick={tell}>Разобрать</button><button className="r-btn r-btn--quiet" onClick={() => setWay('hand')}>Заполнить вручную</button></div>
        </div>
      )}
      {way === 'hand' && (<>
      <div className="r-card r-card--flat stack">
        {pdf && <p className="r-small">Взяли {[pdf.name && 'имя', pdf.spec && 'специализацию', pdf.stack?.length && `стек (${pdf.stack.join(', ')})`, pdf.years && `стаж ${pdf.years}`, pdf.workplaces?.length && `места работы (${pdf.workplaces.join(', ')})`, pdf.salary && 'ожидания', pdf.work_format && 'формат'].filter(Boolean).join(', ') || 'немного'}. Всё с&nbsp;меткой <Mark src="word" />, пока не&nbsp;подтвердит тест.</p>}
        <div className="grid2 tight">
          <div className="r-field"><label className="r-label" htmlFor="nm">Имя</label><input id="nm" className="r-input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Видно только после вашего согласия" /></div>
          <div className="r-field"><label className="r-label" htmlFor="yr">Стаж, лет</label><input id="yr" className="r-input r-num" inputMode="numeric" value={f.years} onChange={(e) => setF({ ...f, years: e.target.value.replace(/\D/g, '') })} /></div>
        </div>
        <div><p className="r-label">Отрасль</p><div className="r-chips"><button className="r-chip" aria-pressed="true">Информационные технологии</button></div></div>
        <div><p className="r-label">Специализация</p><div className="r-chips">{SPECS.map((s) => <button key={s.id} className="r-chip" aria-pressed={f.spec === s.id} onClick={() => setF({ ...f, spec: s.id, stack: s.stack.slice(0, 2) })}>{s.name}</button>)}</div></div>
        <div><p className="r-label">Стек</p><div className="r-chips">{sp.stack.map((s) => <button key={s} className="r-chip" aria-pressed={f.stack.includes(s)} onClick={() => toggle(s)}>{s}</button>)}</div></div>
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
        <button className="r-btn r-btn--main r-btn--lg" onClick={next} disabled={!f.stack.length || !f.name.trim()}>{state.ui.onb || !m.spec ? 'Дальше: что ищете' : 'Сохранить'}</button>
      </div>
      </>)}
    </div>
  );
}

// ── 3. Что ищете: статус поиска и условия ───────────────────────────
function TermsStep() {
  const { state, act, dispatch } = useStore();
  const m = state.cand.profile;
  const [mode, setMode] = useState('full');
  const confirmed = m.grade != null || !!m.express; // экспресс уже дал грейд с меткой — на шаге «Грейд» предложим полный тест
  const start = () => { dispatch({ type: 'ui', patch: { onb: null } }); return act(() => post('cand', '/test/start', { claimed: m.claimed_grade, mode }), 'cand'); };
  const done = confirmed ? () => dispatch({ type: 'ui', patch: { onb: 'grade' } }) : start;
  return (
    <div className="page">
      <OnbSteps steps={CAND_STEPS} cur={2} />
      <h1 className="r-h1">Что ищете</h1>
      <p className="r-mute">По&nbsp;этим условиям ваш агент сверяет приглашения, а&nbsp;вакансии встают в&nbsp;порядке совпадения. Поменять можно в&nbsp;любой момент в&nbsp;настройках.</p>
      <CandTerms first next={confirmed ? 'Дальше: грейд' : 'Дальше: тест'} onDone={done} onBack={() => dispatch({ type: 'ui', patch: state.ui.onb ? { onb: 'about' } : { quizBack: true } })}>
        {!confirmed && <div><p className="r-label">Тест на&nbsp;грейд «{GRADES[m.claimed_grade].name}»</p>
          <div className="seg" role="group" aria-label="Режим теста"><button aria-pressed={mode === 'full'} onClick={() => setMode('full')}>Полный</button><button aria-pressed={mode === 'express'} onClick={() => setMode('express')}>Экспресс</button></div>
          <p className="r-hint">{mode === 'full' ? '20–30 минут, точная оценка грейда' : '3–5 минут, 3–4 задания, погрешность выше'}</p></div>}
      </CandTerms>
    </div>
  );
}

// Последний шаг онбординга у того, чей грейд уже подтверждён: итог теста и путь в профиль.
function GradeStep() {
  const { state, act, dispatch } = useStore();
  const m = state.cand.profile, last = state.cand.tests[0];
  const toProfile = () => { dispatch({ type: 'ui', patch: { onb: null, candTab: 'home' } }); window.scrollTo(0, 0); };
  const g = m.grade ?? m.claimed_grade, express = m.grade == null && !!m.express;
  const retest = () => { dispatch({ type: 'ui', patch: { onb: null } }); return act(() => post('cand', '/test/start', { claimed: g, mode: 'full' }), 'cand'); };
  return (
    <div className="page">
      <OnbSteps steps={CAND_STEPS} cur={3} />
      <h1 className="r-h1">{express ? 'Грейд с\u00a0меткой «экспресс»' : 'Грейд подтверждён'}</h1>
      <div className="onb-grade">
        <div className="r-card r-card--blue cat-card">
          <p className="r-micro on-blue">Ваша категория</p>
          <p className="cat-name">{spec(m.spec).name} · {GRADES[g].name}</p>
          <p className="r-num">Оценка {num(m.theta, 2)} ± {num(m.se, 2)}{m.grade_since ? ` · с ${dateRu(m.grade_since)}` : ''}</p>
        </div>
        <div className="r-card r-card--flat stack-sm">
          {express
            ? <p>Компании видят грейд с&nbsp;меткой «экспресс» и&nbsp;оценку{last ? `, тест — ${dateRu(last.date)}` : ''}. Подтвердить грейд можно полным тестом на&nbsp;6–12 заданий.</p>
            : <p>Тест повторно не&nbsp;нужен: компании видят подтверждённый грейд{last ? `, последний тест — ${dateRu(last.date)}` : ''}.</p>}
          <p className="r-small r-mute">Поднять место в&nbsp;выдаче можно в&nbsp;профиле: интервью под камерой, тест на&nbsp;ступень выше, задания компаний и&nbsp;соревнования ФСП.</p>
          <div className="acts" style={{ marginTop: 'auto' }}><button className="r-btn r-btn--main" onClick={toProfile}>В&nbsp;профиль</button><button className="r-btn" onClick={retest}>{express ? 'Пройти полный тест' : 'Пересдать тест'}</button></div>
        </div>
      </div>
    </div>
  );
}

// ── 4. Адаптивный тест ──────────────────────────────────────────────
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
            <div className="r-field wide"><label className="r-label" htmlFor="ans">{cur.code ? 'Решение на\u00a0Python — проверят скрытые тесты в\u00a0песочнице' : 'Ваш подход'}</label><Dictate value={text} onChange={setText} onStart={() => setEvents((e) => [...e, { t: Date.now(), e: 'voice' }])}><textarea id="ans" className="r-area" rows={cur.code ? 10 : 6} spellCheck={!cur.code} style={cur.code ? { fontFamily: 'var(--r-mono, ui-monospace, monospace)', fontSize: 14 } : undefined} value={text} onPaste={() => setEvents((e) => [...e, { t: Date.now(), e: 'paste' }])} onChange={(e) => setText(e.target.value)} placeholder="Что храним, где, как считаем, что отвечаем клиенту…" /></Dictate><span className="r-hint">Оценивается по&nbsp;рубрике; неуверенную оценку проверяет эксперт.</span></div>
          ) : (
            <div className="opts">{cur.opts.map((o) => <button key={o} className="r-chip opt" aria-pressed={pick === o} onClick={() => setPick(o)}>{o}</button>)}</div>
          )}
          <div className="acts"><button className="r-btn r-btn--main" disabled={cur.open ? text.trim().length < 20 : pick == null} onClick={answer}>Ответить</button></div>
        </div>
        {hood && (
          <aside className="hood r-card r-card--flat">
            <p className="r-micro">Оценка навыка θ</p>
            <p className="hood-num r-num">{num(est.theta, 2)} <span className="r-mute">± {num(est.se, 2)}</span></p>
            <Trace trace={s.trace} claimed={s.claimed} height={200} />
            <p className="r-small"><b>Почему это задание.</b> Из&nbsp;неиспробованных шаблонов сервер взял три самых информативных при θ&nbsp;=&nbsp;{num(est.theta, 2)} и&nbsp;выбрал одно случайно — так ни&nbsp;один шаблон не&nbsp;достаётся всем:</p>
            <ul className="r-small hood-list">{s.why.map((w) => <li key={w.id} className={w.id === cur.tpl ? 'is-on' : ''}>{w.id} {w.title} — информация {w.info}</li>)}</ul>
            <p className="r-small">Цифры и&nbsp;сюжет в&nbsp;условии собраны из&nbsp;случайного зерна — у&nbsp;соседа будут другие. Зерно и&nbsp;эталон ответа остаются на&nbsp;сервере.</p>
            {last && <p className="r-small last">Прошлый ответ «{last.title}»: {last.score >= 0.5 ? 'верно' : 'неверно'}; θ {num(last.theta_before, 2)} → {num(last.theta_after, 2)}</p>}
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
  // Сразу после теста — экран «что дальше», один раз на тест.
  const last = c.tests[0];
  if (last && state.ui.seenTest !== last.id && Date.now() - new Date(last.date) < 6 * 3600e3) return <Done test={last} />;
  return (
    <div className="page">
      <CabHead micro="Кабинет кандидата" title={c.profile.name || 'Без имени'} sub={`${spec(c.profile.spec).name} · ${c.profile.grade != null ? `${GRADES[c.profile.grade].name}, ${state.ui.camDone ? 'подтверждено под камерой' : 'подготовительный тест'}` : `${GRADES[c.profile.claimed_grade].name}, ${c.profile.express ? 'экспресс-тест' : 'грейд не подтверждён'}`} · ${searchName(c.profile.search)}`}>
        <Tabs value={tab} onChange={(t) => dispatch({ type: 'ui', patch: { candTab: t } })} items={[['home', 'Профиль'], ['invites', 'Приглашения', fresh], ['agent', 'Мой агент'], ['refs', 'Отзывы', (c.refs?.inbox || []).filter((r) => r.status === 'asked').length], ['view', 'Как меня видят'], ['stats', 'Статистика'], ['tasks', 'Задания'], ['grade', 'Категория и грейд'], ['profile', 'Факты'], ['vac', 'Вакансии'], ['settings', 'Настройки']]} />
      </CabHead>
      {tab === 'home' && <ProfileHome />}
      {tab === 'refs' && <RefsTab />}
      {tab === 'grade' && <GradeTab />}
      {tab === 'tasks' && <CandidateTasks />}
      {tab === 'view' && <CandidateProfileDoc profile={c.profile} tests={c.tests} rank={c.rank} />}
      {tab === 'stats' && <CandStatsDoc profile={c.profile} rank={c.rank} stats={c.stats} />}
      {tab === 'invites' && <InvitesTab />}
      {tab === 'profile' && <ProfileTab />}
      {tab === 'vac' && <VacTab />}
      {tab === 'settings' && <SettingsTab />}
      {tab === 'agent' && <div className="stack"><p className="r-mute">Агент ведёт первый разговор с&nbsp;агентом компании до&nbsp;приглашения. Отвечает только одобренными фактами профиля, а&nbsp;спрашивает&nbsp;— то, что вы&nbsp;зададите здесь.</p><AgentForm /><AgentCheck /></div>}
    </div>
  );
}

// ── Профиль: кто я, что заполнено и что осталось из онбординга ─────────
function ProfileHome() {
  const { state, dispatch } = useStore();
  const c = state.cand, m = c.profile, w = m.wants || {}, ag = m.agent;
  const tab = (t) => { dispatch({ type: 'ui', patch: { candTab: t } }); window.scrollTo(0, 0); };
  const facts = m.facts || [];
  const okFacts = facts.filter((f) => f.approved).length;
  const g = m.grade ?? m.claimed_grade;
  const steps = [
    { name: 'Кто вы в ИТ', done: !!(m.spec && m.stack?.length && m.claimed_grade != null), text: m.spec ? `${spec(m.spec).name} · ${m.stack.join(', ')} · стаж ${m.years} ${m.years === 1 ? 'год' : m.years > 1 && m.years < 5 ? 'года' : 'лет'}` : 'Специализация, стек и стаж', btn: 'Изменить', go: () => dispatch({ type: 'ui', patch: { quizBack: true } }) },
    { name: 'Что ищете', done: !!m.wants, text: m.wants ? [searchName(m.search), (w.formats || []).join(', '), m.salary ? `от ${fmt(m.salary)}` : null, (w.cities || []).join(', ')].filter(Boolean).join(' · ') : 'Статус поиска, формат, деньги, города', btn: m.wants ? 'Изменить' : 'Заполнить', go: () => tab('settings') },
    { name: 'Тест на грейд', done: m.grade != null, text: m.grade != null ? `«${GRADES[m.grade].name}» подтверждён тестом` : m.express ? `«${GRADES[g].name}» по экспресс-тесту, подтвердит полный` : `Заявлен «${GRADES[g].name}», тестом не подтверждён`, btn: m.grade != null ? 'Открыть' : m.express ? 'Пройти полный тест' : 'Пройти тест', go: () => tab('grade') },
    { name: 'Мой агент', done: !!ag, text: ag ? `Стоп-факторов: ${(ag.stops || []).length} · вопросов компаниям: ${(ag.asks || []).length}` : 'Не настроен: спрашивает компании только по общему сценарию', btn: ag ? 'Изменить' : 'Настроить', go: () => tab('agent') },
    { name: 'ФСП ID', done: !!m.fsp_id, text: m.fsp_id ? `Привязан · достижений: ${(m.fsp || []).length}` : 'Не привязан: результаты соревнований не видны', btn: m.fsp_id ? 'Открыть' : 'Привязать', go: () => tab('settings') },
    { name: 'Факты профиля', done: facts.length > 0 && okFacts === facts.length, text: `Одобрено ${okFacts} из ${facts.length}: компании видят только одобренные`, btn: 'Проверить', go: () => tab('profile') },
  ];
  const done = steps.filter((s) => s.done).length;
  const next = steps.find((s) => !s.done);
  const ini = (m.name || 'Я').split(/\s+/).slice(0, 2).map((x) => x[0]).join('').toUpperCase();
  return (
    <div className="stack">
      <div className="ph-top">
        <section className="r-card r-card--flat ph-card">
          <div className="ph-who">
            <span className="ph-ava" aria-hidden="true">{ini}</span>
            <div>
              <h2 className="r-h2 ph-name">{m.name || 'Без имени'}</h2>
              <p className="r-small">{spec(m.spec).name} · {GRADES[g].name}{m.grade == null ? (m.express ? ', экспресс-тест' : ', не подтверждён') : ''}</p>
            </div>
          </div>
          <dl className="ph-dl">
            <div><dt>Статус</dt><dd><span className={`ph-st ph-st--${m.search || 'active'}`}>{searchName(m.search)}</span></dd></div>
            <div><dt>Почта</dt><dd>{state.me?.email}</dd></div>
            {m.city && <div><dt>Город</dt><dd>{m.city}</dd></div>}
            {m.salary ? <div><dt>Ожидания</dt><dd className="r-num">{fmt(m.salary)}</dd></div> : null}
          </dl>
          <div className="acts" style={{ marginTop: 'auto' }}><button className="r-btn" onClick={() => tab('view')}>Как меня видят компании</button></div>
        </section>
        <section className="r-card r-card--flat ph-card">
          <p className="r-label">Профиль заполнен</p>
          <p className="ph-pct r-num">{Math.round((done / steps.length) * 100)}&nbsp;%</p>
          <div className="ph-bar" aria-hidden="true"><i style={{ width: `${(done / steps.length) * 100}%` }} /></div>
          {next ? <><p className="r-small">Следующий шаг: <b>{next.name}</b>. {next.text}.</p><div className="acts" style={{ marginTop: 'auto' }}><button className="r-btn r-btn--main" onClick={next.go}>{next.btn}</button></div></>
            : <p className="r-small" style={{ marginTop: 'auto' }}>Всё заполнено: компании видят полный профиль, агент знает ваши условия.</p>}
        </section>
      </div>
      <Boost tab={tab} />
      <section className="r-card r-card--flat">
        <h2 className="r-h3">Шаги профиля</h2>
        <ol className="ph-steps">{steps.map((s) => (
          <li key={s.name} className={s.done ? 'is-done' : ''}>
            <span className="ph-dot" aria-label={s.done ? 'Готово' : 'Не заполнено'}>{s.done ? '✓' : ''}</span>
            <div><b>{s.name}</b><span className="r-small r-mute">{s.text}</span></div>
            <button className="r-btn r-btn--sm" onClick={s.go}>{s.btn}</button>
          </li>))}</ol>
      </section>
    </div>
  );
}

// Усилить профиль: что поднимает место в выдаче после онбординга.
function Boost({ tab }) {
  const { state, dispatch } = useStore();
  const c = state.cand, m = c.profile, ui = state.ui;
  const reg = ui.fspReg || [];
  const camDone = !!ui.camDone;
  const g = m.grade;
  const tasks = (c.tasks || []).filter((t) => !t.answer).length;
  const join = (id) => dispatch({ type: 'ui', patch: { fspReg: reg.includes(id) ? reg.filter((x) => x !== id) : [...reg, id] } });
  const cards = [
    { k: 'cam', title: 'Интервью под камерой', text: camDone ? 'Пройдено: грейд подтверждён под камерой, вы выше подготовительного теста.' : 'Грейд, подтверждённый под камерой, ставит вас выше тех, кто прошёл только подготовительный тест.', btn: camDone ? 'Посмотреть' : 'Пройти интервью', go: () => { dispatch({ type: 'ui', patch: { cam: 'prep' } }); window.scrollTo(0, 0); }, main: !camDone && g != null },
    { k: 'test', title: g == null ? 'Подтвердить грейд' : g < 4 ? `Тест на «${GRADES[g + 1].name}»` : 'Пересдать тест', text: g == null ? 'Без теста вы в выдаче ниже всех подтверждённых: компании видят метку «грейд не подтверждён».' : g < 4 ? 'Пройдёте уверенно — перейдёте в категорию выше, где больше вилки зарплаты.' : 'Свежая оценка держит вас наверху категории.', btn: g == null ? 'Пройти тест' : 'К тесту', go: () => tab('grade'), main: g == null },
    { k: 'recs', title: 'Рекомендации коллег', text: (() => { const r = c.refs?.recs; return r ? `Одобрено ${r.approved}${r.asked ? `, ждём ${r.asked}` : ''}. Рекомендации и отзывы коллег — 5 % балла в выдаче.` : 'Рекомендации и отзывы коллег — 5 % балла в выдаче.'; })(), btn: 'Попросить', go: () => tab('refs') },
    { k: 'tasks', title: 'Задания компаний', text: tasks ? `Для вашей категории ${tasks} ${tasks === 1 ? 'задание' : tasks < 5 ? 'задания' : 'заданий'}. Ответ с оценкой «сильно» поднимает в выдаче.` : 'Новых заданий нет: они приходят от компаний вашей категории.', btn: 'К заданиям', go: () => tab('tasks') },
  ];
  return (
    <section className="stack-sm">
      <h2 className="r-h3">Усилить профиль</h2>
      <div className="boost">{cards.map((x) => (
        <div key={x.k} className="r-card r-card--flat boost-card"><b>{x.title}</b><p className="r-small r-mute">{x.text}</p>
          <div className="acts" style={{ marginTop: 'auto' }}><button className={`r-btn r-btn--sm ${x.main ? 'r-btn--main' : ''}`} onClick={x.go}>{x.btn}</button></div></div>))}
      <div className="r-card r-card--flat stack-sm boost-fsp">
        <b>Соревнования ФСП</b>
        <p className="r-small r-mute">{m.fsp_id ? 'Призовое место встанет в профиль с меткой ФСП и поднимет вас внутри категории.' : 'Привяжите ФСП ID, чтобы результат встал в профиль с меткой ФСП.'}</p>
        <ul className="boost-ev">{FSP_UPCOMING.map((ev) => (
          <li key={ev.id}><div><b>{ev.name}</b><span className="r-small r-mute">{ev.date} · {ev.where} · {ev.disc}</span></div>
            <button className={`r-btn r-btn--sm ${reg.includes(ev.id) ? '' : 'r-btn--main'}`} onClick={() => join(ev.id)}>{reg.includes(ev.id) ? 'Вы записаны' : 'Записаться'}</button></li>))}</ul>
        {!m.fsp_id && <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--sm" onClick={() => tab('settings')}>Привязать ФСП ID</button></div>}
      </div>
      </div>
    </section>
  );
}

function Done({ test }) {
  const { state, dispatch } = useStore();
  const m = state.cand.profile, r = state.cand.rank;
  const ok = test.verdict.kind === 'ok';
  const express = ok && test.mode === 'express';
  const go = (tab) => dispatch({ type: 'ui', patch: { seenTest: test.id, candTab: tab } });
  return (
    <div className="page">
      <p className="r-micro">Кандидат · тест завершён</p>
      <h1 className="r-h1">{express ? 'Экспресс-тест пройден — грейд с меткой «экспресс»' : ok ? 'Грейд подтверждён — дальше пишут вам' : 'Вы в категории, грейд пока не подтверждён'}</h1>
      <div className="done">
        <div className="stack">
          <div className="r-card r-card--blue cat-card">
            <p className="r-micro on-blue">Ваша категория</p>
            <p className="cat-name">{spec(m.spec).name} · {GRADES[ok ? test.claimed : m.claimed_grade].name}</p>
            {r && <p className="r-num">{r.pos} из&nbsp;{r.total} в&nbsp;категории{r.looking ? ` · ищут компаний: ${r.looking}` : ''}</p>}
          </div>
          <ol className="done-steps">
            <li><b>Работодатели видят категорию.</b> Имя, места работы и&nbsp;подтверждённый грейд; почта и&nbsp;телефон закрыты.</li>
            <li><b>Агенты сверяют условия.</b> Ваш агент отвечает только одобренными фактами и&nbsp;называет источник.</li>
            <li><b>Приглашение приходит с&nbsp;вилкой зарплаты.</b> Примете&nbsp;— компания увидит контакты; откажете&nbsp;— с&nbsp;причиной, она поправит подборку.</li>
          </ol>
          {express && <p className="r-small">Работодатели видят грейд с&nbsp;меткой <span className="r-mark" title="Экспресс-тест из 4 заданий: грейд с меткой, подтверждает полный тест">экспресс</span> выше тех, кто тест не&nbsp;проходил. Подтвердить грейд&nbsp;— полным тестом на&nbsp;6–12 заданий во&nbsp;вкладке «Категория и&nbsp;грейд».</p>}
          {!ok && <p className="r-small">Тест на&nbsp;ступень ниже доступен сразу во&nbsp;вкладке «Категория и&nbsp;грейд». Пока вы&nbsp;в&nbsp;выдаче с&nbsp;меткой <span className="r-mark r-mark--warn">грейд не&nbsp;подтверждён</span>.</p>}
          <div className="acts">
            <button className="r-btn r-btn--main" onClick={() => go('view')}>Посмотреть, как меня видят</button>
            <button className="r-btn" onClick={() => go(ok && !express ? 'invites' : 'grade')}>{express ? 'К полному тесту' : ok ? 'К приглашениям' : 'К тесту на ступень ниже'}</button>
          </div>
        </div>
        {doneArt && <div className="done-art" aria-hidden="true" dangerouslySetInnerHTML={{ __html: doneArt }} />}
      </div>
    </div>
  );
}

// Значок грейда для README и подписи: картинка с подписанным адресом, ведёт на главную сервиса.
function Badge() {
  const [b, setB] = useState(null);
  const [done, setDone] = useState(false);
  useEffect(() => { get('cand', '/candidate/badge').then(setB).catch(() => {}); }, []);
  if (!b) return null;
  const md = `[![Разряд](${location.origin}${b.path})](${location.origin}/)`;
  const copy = () => navigator.clipboard?.writeText(md).then(() => { setDone(true); setTimeout(() => setDone(false), 2000); });
  return (
    <div className="r-card r-card--flat stack-sm">
      <h2 className="r-h3">Значок грейда</h2>
      <p className="r-small r-mute">Поставьте в&nbsp;README на&nbsp;GitHub или в&nbsp;подпись: грейд подтверждён тестом, значок обновится сам.</p>
      <img src={b.path} alt="Значок грейда" className="badge-img" />
      <code className="badge-md">{md}</code>
      <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--sm" onClick={copy}>{done ? 'Скопировано' : 'Скопировать для README'}</button></div>
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
          <p className="r-num" title={`Оценка навыка θ = ${num(m.theta, 2)} ± ${num(m.se, 2)}`}>{state.ui.camDone ? `Под камерой · ${dateRu(state.ui.camDone.date)}` : `Подготовительный тест · ${dateRu(m.grade_since)}`}</p>
        </div>
      ) : (
        <div className="r-card r-card--sun"><p className="r-h3">{spec(m.spec).name} · {GRADES[m.claimed_grade].name} <span className="r-mark r-mark--warn">грейд не подтверждён</span></p><p>Вы в&nbsp;выдаче своей категории, но&nbsp;ниже всех, кто подтвердил грейд тестом. Пройдите тест на&nbsp;ступень ниже или&nbsp;повторите заявленный позже.</p></div>
      )}
      <CamCards />
      {m.grade != null && <Badge />}
      {t && (
        <div className="r-card r-card--flat">
          <h2 className="r-h3">Последний тест · {dateRu(t.date)}{t.mode === 'express' ? ' · экспресс' : ''}</h2>
          {v.kind === 'ok' && <p>Заявленный грейд «{GRADES[t.claimed].name}» <b>подтверждён</b> за&nbsp;{plural(t.n, ...ZAD)}.{v.offer_up ? ' Результат уверенно выше границы — доступен отдельный тест на ступень выше.' : ''}</p>}
          {v.kind === 'below' && <p>Заявленный «{GRADES[t.claimed].name}» не&nbsp;подтверждён: оценка соответствует уровню «{GRADES[v.measured].name}». {v.close ? 'Вы были близко к границе.' : ''} Тест на&nbsp;ступень ниже доступен сразу, повтор заявленного — через {COOLDOWN_DAYS}&nbsp;дней.</p>}
          <Skills rows={t.skills} />
          {t.conduct && <p className="r-small r-mute">Протокол теста: {plural(t.conduct.items, ...ZAD)}{t.conduct.seconds != null ? `, ${Math.round(t.conduct.seconds / 60)} мин` : ''}, заданий с открытым ИИ — {t.conduct.ai_items}, вставок из буфера — {t.conduct.paste}, уходов со вкладки — {t.conduct.blur}. Это видит работодатель; штрафа нет.</p>}
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
          <tbody>{state.cand.tests.map((x) => <tr key={x.id}><td>{srvDate(x.date).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })}</td><td>{GRADES[x.claimed].name}</td><td>{x.verdict.kind === 'ok' ? 'Подтверждён' : 'Не подтверждён'}</td><td className="r-num">{num(x.theta, 2)} ± {num(x.se, 2)}</td><td className="r-num">{x.n}</td></tr>)}</tbody>
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
        <tbody>{sorted.map((r) => <tr key={r.name}><td>{r.name}</td><td className="r-num">{num(r.theta, 2)} ± {num(r.se, 2)}</td><td className="r-num">{r.items}</td></tr>)}</tbody>
      </table></div>
      <p className="doc-note">Тянет вниз: <b>{sorted[0].name.toLowerCase()}</b>. На пересдаче система снова даст задания этого навыка — других вариантов, той же трудности.</p>
    </div>
  );
}

function InvitesTab() {
  const { state, act, dispatch } = useStore();
  const list = state.cand.invites;
  const [open, setOpen] = useState(null);
  const inv = list.find((i) => i.id === open);
  const show = (i) => { setOpen(i.id); if (i.status === 'отправлено') act(() => post('cand', `/candidate/invites/${i.id}`, { status: 'просмотрено' }), 'cand'); };
  if (!list.length) return <Empty img="./empty-invite.svg" title="Приглашений пока нет">{state.cand.profile.grade != null ? 'Работодатели видят вашу категорию. Первое приглашение придёт с вилкой зарплаты.' : 'Вы в выдаче с меткой «грейд не подтверждён»; подтвердите грейд тестом, чтобы подняться.'}<div className="acts"><button className="r-btn" onClick={() => dispatch({ type: 'ui', patch: { candTab: 'view' } })}>Как меня видят работодатели</button></div></Empty>;
  return (
    <div className="stack">
      {list.map((i) => (
        <button key={i.id} className="r-card inv-row" onClick={() => show(i)}>
          <div><p className="r-micro">{i.company}</p><p className="r-h3">{i.title}</p><p className="r-small r-mute">{i.text}</p>{i.status === 'отклонено' && i.log.some((l) => l.by) && <p className="r-small">Отклонил ваш агент: {i.reason}</p>}</div>
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
      <CompanySummary s={inv.summary} />
      <p className="r-small"><b>Связь:</b> {inv.status === 'принято' ? inv.contact : 'откроется после вашего согласия'} · <b>Формат:</b> {cap(inv.work_format) || '—'}</p>
      {inv.status === 'принято' && <p className="r-toast">Вы приняли приглашение — компания видит ваши контакты</p>}
      {inv.status === 'отклонено' && <p className="r-small">Отклонено: {inv.reason}</p>}
      <div className="acts"><button className="r-btn r-btn--sm" onClick={() => setMode('company')}>Профиль компании…</button>{inv.talk && <button className="r-btn r-btn--sm" onClick={() => setMode('nego')}>Протокол переговоров агентов…</button>}</div>
      {mode === 'company' && emp && <EmployerProfileDoc e={emp} offer={{ from: inv.salary_from, to: inv.salary_to }} />}
      {mode === 'nego' && <Negotiation talk={inv.talk} company={inv.company} who="Вы" side="cand" instant />}
      {mode === 'no' && (
        <div className="stack-sm"><p className="r-label">Причина — компания её увидит и&nbsp;поправит подборку</p><div className="r-chips">{REASONS.map((r) => <button key={r} className="r-chip" onClick={() => decide('отклонено', r)}>{cap(r)}</button>)}</div></div>
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
        <div className="r-field wide"><Dictate value={q.v} onChange={(v) => setQ({ ...q, v })}><input className="r-input" value={q.v} onChange={(e) => setQ({ ...q, v: e.target.value })} placeholder="Коротко, как сказали бы рекрутеру" aria-label="Ответ" /></Dictate></div>
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
      <p className="r-small r-mute">Сначала&nbsp;— подходящие под ваши условия. Вакансии своей компании и&nbsp;компаний на&nbsp;паузе здесь не&nbsp;показываются.</p>
      {state.cand.vacancies.map((v) => {
        const r = resp.find((x) => x.vacancy_id === v.id);
        return (
          <div key={v.id} className="r-card r-card--flat inv-row">
            <div><p className="r-micro">{v.company} · {spec(v.spec).name} · {GRADES[v.grade].name}</p><p className="r-h3">{v.title}</p><p className="r-small">{v.stack.join(', ')} · {cap(v.work_format)}{v.city ? ` · ${v.city}` : ''}</p>
              <p className="r-small">{v.fits ? <span className="r-mark r-mark--fsp">Подходит под условия</span> : <span className="r-mark" title="Не совпало с вашими условиями поиска">Не совпало: {v.miss.join(', ')}</span>}</p></div>
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
    const { code: fspCode } = await get(null, `/fsp-id/authorize?sub=${sub}&redirect_uri=${encodeURIComponent(location.origin + '/cb')}&response_mode=json`);
    await post('cand', '/candidate/fsp/link', { code: fspCode });
  }, 'cand').then(() => setAccounts(null));
  return (
    <div className="stack">
    <h2 className="r-h3">Поиск работы</h2>
    {m.own_company && <p className="r-small r-mute">Вы&nbsp;представляете «{m.own_company.name}»: эта компания ваш профиль не&nbsp;видит.</p>}
    <CandTerms />
    <div className="r-card r-card--flat stack">
      <h2 className="r-h3">Что видно работодателю</h2>
      <label className="r-switch"><input type="checkbox" checked={m.privacy.fsp} onChange={(e) => p('fsp', e.target.checked)} /><i />Результаты соревнований ФСП</label>
      <label className="r-switch"><input type="checkbox" checked={m.privacy.salary} onChange={(e) => p('salary', e.target.checked)} /><i />Ожидания по&nbsp;зарплате</label>
      <label className="r-switch"><input type="checkbox" checked={!!m.privacy.city} onChange={(e) => p('city', e.target.checked)} /><i />Город</label>
      <label className="r-switch"><input type="checkbox" checked={m.visible} onChange={(e) => act(() => patch('cand', '/candidate/profile', { visible: e.target.checked }), 'cand')} /><i />Показывать меня в&nbsp;банке кандидатов</label>
      <p className="r-small r-mute">Почта и&nbsp;телефон закрыты, пока вы&nbsp;не&nbsp;приняли приглашение или не&nbsp;откликнулись сами.</p>
      <h2 className="r-h3">ФСП&nbsp;ID</h2>
      {m.fsp_id ? <p>Привязан · {m.fsp_id} <button className="r-btn r-btn--sm r-btn--quiet" onClick={() => act(() => del('cand', '/candidate/fsp/link'), 'cand')}>Отвязать</button></p>
        : accounts ? <div className="stack-sm">{accounts.map((a) => <button key={a.sub} className="r-btn r-btn--sm" onClick={() => link(a.sub)}>{a.name} · {a.history ? 'с историей' : 'без истории'}</button>)}</div>
        : <button className="r-btn r-btn--sm" onClick={() => get(null, '/fsp-id/accounts').then(setAccounts)}>Привязать ФСП&nbsp;ID…</button>}
      <p className="r-small r-mute">Отвязали — достижения ушли из&nbsp;профиля. Изменить записи реестра нельзя, скрыть любую — можно во&nbsp;вкладке «Факты».</p>
      <h2 className="r-h3">Выход</h2>
      <button className="r-btn r-btn--sm r-btn--quiet" onClick={() => { setToken('cand', null); location.reload(); }}>Выйти из&nbsp;аккаунта</button>
    </div>
    </div>
  );
}
