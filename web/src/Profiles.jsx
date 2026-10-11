/* Профили одного входа: кандидат и компания. Здесь — создание второго
   профиля, условия поиска кандидата и настройки найма компании. Экраны
   работают и шагом онбординга (first), и вкладкой настроек. */
import { useEffect, useState } from 'react';
import { useStore } from './store.jsx';
import { get, patch, post } from './api.js';
import { AGENT_ASKS, AGENT_CRITS, AGENT_IMP, AGENT_STOPS, CITIES, FIELDS, FORMATS, GRADES, HIRING, SEARCH, SPECS, cap, fmtRange } from './const.js';
import { Dictate, Modal } from './ui.jsx';
import { Negotiation } from './Artifacts.jsx';

const toggle = (list, x) => (list.includes(x) ? list.filter((y) => y !== x) : [...list, x]);

function Chips({ label, all, value, onChange, name = (x) => x, id = (x) => x }) {
  return (
    <div><p className="r-label">{label}</p>
      <div className="r-chips">{all.map((x) => <button key={id(x)} className="r-chip" aria-pressed={value.includes(id(x))} onClick={() => onChange(toggle(value, id(x)))}>{name(x)}</button>)}</div>
    </div>
  );
}

function Seg({ label, items, value, onChange }) {
  const cur = items.find((x) => x.id === value) || items[0];
  return (
    <div><p className="r-label">{label}</p>
      <div className="seg" role="group" aria-label={label}>{items.map((x) => <button key={x.id} aria-pressed={cur.id === x.id} title={x.hint} onClick={() => onChange(x.id)}>{x.name}</button>)}</div>
      <p className="r-hint">{cur.hint}</p>
    </div>
  );
}

// ── Второй профиль на том же входе ──────────────────────────────────
export function AddProfile({ kind }) {
  const { state, act } = useStore();
  const me = state.me;
  const cand = kind === 'cand';
  const other = cand ? me?.profiles?.employer?.name : me?.profiles?.candidate?.name;
  const add = () => act(() => post('cand', `/auth/profiles/${cand ? 'candidate' : 'employer'}`), 'all');
  return (
    <div className="page">
      <p className="r-micro">{me?.email}</p>
      <h1 className="r-h1">{cand ? 'Профиль кандидата' : 'Профиль компании'}</h1>
      <div className="r-card r-card--flat stack">
        {cand ? (<>
          <p>Ищете работу сами, пока нанимаете{other ? <> за&nbsp;«{other}»</> : null}? Профиль кандидата живёт на&nbsp;том&nbsp;же входе, переключение&nbsp;— в&nbsp;меню профиля.</p>
          <ul className="r-small stack-sm">
            <li><b>Своя компания вас не&nbsp;видит.</b> Ни&nbsp;в&nbsp;подборке, ни&nbsp;в&nbsp;банке, ни&nbsp;в&nbsp;откликах.</li>
            <li><b>Остальным&nbsp;— по&nbsp;вашему статусу.</b> «Ищу», «Рассматриваю» или «Не&nbsp;ищу» меняется в&nbsp;настройках.</li>
            <li><b>Вакансии своей компании</b> в&nbsp;поиске работы не&nbsp;показываются.</li>
          </ul>
        </>) : (<>
          <p>Нанимаете в&nbsp;свою команду? Заведите профиль компании на&nbsp;том&nbsp;же входе: подбор, задания и&nbsp;приглашения&nbsp;— от&nbsp;её имени.</p>
          <ul className="r-small stack-sm">
            <li><b>Ваш профиль кандидата компания не&nbsp;увидит</b>{other ? <> ({other})</> : null}.</li>
            <li><b>Три шага:</b> компания, кого нанимаете, первый подбор.</li>
          </ul>
        </>)}
        <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--main" onClick={add}>{cand ? 'Создать профиль кандидата' : 'Создать профиль компании'}</button></div>
      </div>
    </div>
  );
}

// ── Кандидат: статус поиска и условия ───────────────────────────────
export function CandTerms({ first, next, onDone, onBack, children }) {
  const { state, act } = useStore();
  const m = state.cand.profile;
  const w = m.wants || {};
  const [f, setF] = useState({
    search: m.search || 'active', formats: w.formats?.length ? w.formats : [m.work_format || 'гибрид'], salary: m.salary || '',
    cities: w.cities || (m.city ? [m.city] : []), relocate: !!w.relocate, fields: w.fields || [], hide: w.hide || [], note: w.note || '',
  });
  const [cos, setCos] = useState([]);
  useEffect(() => { get('cand', '/candidate/companies').then(setCos).catch(() => {}); }, []);
  const [saved, setSaved] = useState(false);
  const ok = f.formats.length > 0;
  const save = () => act(async () => {
    await patch('cand', '/candidate/profile', {
      search: f.search, work_format: f.formats[0], salary: f.salary ? +f.salary : undefined,
      wants: { formats: f.formats, cities: f.cities, relocate: f.relocate, fields: f.fields, hide: f.hide, note: f.note },
    });
    if (onDone) await onDone();
  }, 'cand').then(() => { setSaved(true); setTimeout(() => setSaved(false), 2000); });
  const own = cos.find((c) => c.own);
  return (
    <div className="r-card r-card--flat stack">
      <Seg label="Статус поиска" items={SEARCH} value={f.search} onChange={(v) => setF({ ...f, search: v })} />
      <div className="grid2 tight">
        <Chips label="Формат работы" all={FORMATS} value={f.formats} name={cap} onChange={(v) => setF({ ...f, formats: v })} />
        <div className="r-field"><label className="r-label" htmlFor="tsal">Деньги от, ₽ на&nbsp;руки</label><input id="tsal" className="r-input r-num" inputMode="numeric" value={f.salary} onChange={(e) => setF({ ...f, salary: e.target.value.replace(/\D/g, '') })} /></div>
      </div>
      <Chips label="Города" all={CITIES} value={f.cities} onChange={(v) => setF({ ...f, cities: v })} />
      <label className="r-switch"><input type="checkbox" checked={f.relocate} onChange={(e) => setF({ ...f, relocate: e.target.checked })} /><i />Рассматриваю переезд</label>
      <Chips label="Сферы компаний" all={FIELDS} value={f.fields} onChange={(v) => setF({ ...f, fields: v })} />
      <div className="r-field wide"><label className="r-label" htmlFor="tnote">Что важно в&nbsp;новой работе</label><input id="tnote" className="r-input" value={f.note} placeholder="Рост до техлида, продукт с нагрузкой" onChange={(e) => setF({ ...f, note: e.target.value })} /></div>
      {cos.length > 0 && (
        <div><p className="r-label">Скрыть профиль от&nbsp;компаний</p>
          <div className="r-chips">
            {own && <button className="r-chip" aria-pressed="true" disabled title="Компания, которую вы представляете на платформе, ваш профиль не видит никогда">{own.name} · ваша</button>}
            {cos.filter((c) => !c.own).map((c) => <button key={c.id} className="r-chip" aria-pressed={f.hide.includes(c.id)} onClick={() => setF({ ...f, hide: toggle(f.hide, c.id) })}>{c.name}</button>)}
          </div>
        </div>
      )}
      {children}
      <div className="acts">
        <button className="r-btn r-btn--main" disabled={!ok} onClick={save}>{first ? next || 'Дальше: тест' : saved ? 'Сохранено' : 'Сохранить'}</button>
        {onBack && <button className="r-btn r-btn--quiet" onClick={onBack}>Назад</button>}
      </div>
    </div>
  );
}

// ── Компания: статус найма и критерии подбора ───────────────────────
export function HiringForm({ first, onDone }) {
  const { state, act } = useStore();
  const c = state.emp.company;
  const p = c.prefs || {};
  const [f, setF] = useState({ hiring: c.hiring || 'active', specs: p.specs || ['backend'], grades: p.grades || [2], formats: p.formats || ['гибрид'], cities: p.cities || (c.city ? [c.city] : []), confirmed_only: !!p.confirmed_only, fsp_first: !!p.fsp_first });
  const [saved, setSaved] = useState(false);
  const save = () => act(async () => {
    const { hiring, ...prefs } = f;
    await patch('emp', '/employer/company', { hiring, prefs });
    if (onDone) onDone();
  }, 'emp').then(() => { setSaved(true); setTimeout(() => setSaved(false), 2000); });
  return (
    <div className="r-card r-card--flat stack">
      <Seg label="Статус найма" items={HIRING} value={f.hiring} onChange={(v) => setF({ ...f, hiring: v })} />
      <Chips label="Специализации" all={SPECS} id={(s) => s.id} name={(s) => s.name} value={f.specs} onChange={(v) => setF({ ...f, specs: v })} />
      <Chips label="Грейды" all={GRADES} id={(g) => g.id} name={(g) => g.name} value={f.grades} onChange={(v) => setF({ ...f, grades: v })} />
      <div className="grid2 tight">
        <Chips label="Форматы" all={FORMATS} name={cap} value={f.formats} onChange={(v) => setF({ ...f, formats: v })} />
        <Chips label="Города" all={CITIES} value={f.cities} onChange={(v) => setF({ ...f, cities: v })} />
      </div>
      <label className="r-switch"><input type="checkbox" checked={f.confirmed_only} onChange={(e) => setF({ ...f, confirmed_only: e.target.checked })} /><i />Только с&nbsp;подтверждённым грейдом</label>
      <label className="r-switch"><input type="checkbox" checked={f.fsp_first} onChange={(e) => setF({ ...f, fsp_first: e.target.checked })} /><i />Сначала участники соревнований ФСП</label>
      {!first && <p className="r-small r-mute">Критерии встают фильтрами в&nbsp;банк кандидатов; в&nbsp;подборке их&nbsp;можно снять.</p>}
      <div className="acts"><button className="r-btn r-btn--main" disabled={!f.specs.length || !f.grades.length} onClick={save}>{first ? 'Дальше: подбор' : saved ? 'Сохранено' : 'Сохранить'}</button></div>
    </div>
  );
}

// ── Кандидат: настройка своего агента ───────────────────────────────
/* Агент кандидата ведёт первый разговор с агентом компании. Здесь человек
   решает, что для него важно, что — стоп-фактор, какие вопросы агент задаёт
   всегда и как искать своими словами. Всё это меняет протокол переговоров
   на сервере (core/agents.py), а не только хранится. */
export function AgentForm() {
  const { state, act } = useStore();
  const m = state.cand.profile;
  const a = m.agent || {};
  const [f, setF] = useState({ importance: a.importance || {}, stops: a.stops || [], asks: a.asks || [AGENT_ASKS[0]], brief: a.brief || '', auto_decline: !!a.auto_decline });
  const [q, setQ] = useState('');
  const [saved, setSaved] = useState(false);
  const imp = (k) => f.importance[k] || 'high';
  const own = f.asks.filter((x) => !AGENT_ASKS.includes(x));
  const addQ = () => { const t = q.trim(); if (t.length < 5 || f.asks.includes(t)) return; setF({ ...f, asks: [...f.asks, t].slice(0, 10) }); setQ(''); };
  const save = () => act(() => patch('cand', '/candidate/profile', { agent: f }), 'cand').then(() => { setSaved(true); setTimeout(() => setSaved(false), 2000); });
  return (
    <div className="r-card r-card--flat stack">
      <div className="r-field wide"><label className="r-label" htmlFor="abrief">Как искать&nbsp;— своими словами</label>
        <Dictate value={f.brief} onChange={(v) => setF({ ...f, brief: v })}><textarea id="abrief" className="r-area" rows={3} value={f.brief} placeholder="Ищи продуктовые компании с нагрузкой, где можно вырасти до техлида. Стек вторичен, деньги — нет." onChange={(e) => setF({ ...f, brief: e.target.value })} /></Dictate>
        <span className="r-hint">С&nbsp;этого агент начинает каждый разговор с&nbsp;компанией.</span></div>
      <div><p className="r-label">Что для вас важно</p>
        <div className="ag-imp">{AGENT_CRITS.map(([k, name]) => (
          <div key={k} className="ag-imp__row"><span>{name}</span>
            <div className="seg" role="group" aria-label={name}>{AGENT_IMP.map((x) => <button key={x.id} aria-pressed={imp(k) === x.id} onClick={() => setF({ ...f, importance: { ...f.importance, [k]: x.id } })}>{x.name}</button>)}</div>
          </div>))}</div>
        <p className="r-hint" title="«Неважно» — расхождение по этому пункту не портит итог переговоров. «Стоп-фактор» — расхождение решает итог сразу.">Неважное не&nbsp;портит итог, стоп-фактор решает его сразу.</p></div>
      <div><p className="r-label">Стоп-факторы</p>
        <div className="r-chips">{AGENT_STOPS.map(([k, name]) => <button key={k} className="r-chip" aria-pressed={f.stops.includes(k)} onClick={() => setF({ ...f, stops: toggle(f.stops, k) })}>{name}</button>)}</div>
        <p className="r-hint">Агент проверит по&nbsp;вакансии, а&nbsp;чего в&nbsp;ней нет&nbsp;— спросит у&nbsp;компании.</p></div>
      <div><p className="r-label">Обязательно уточнить у&nbsp;компании</p>
        <div className="r-chips">
          {AGENT_ASKS.map((x) => <button key={x} className="r-chip" aria-pressed={f.asks.includes(x)} onClick={() => setF({ ...f, asks: toggle(f.asks, x) })}>{x}</button>)}
          {own.map((x) => <button key={x} className="r-chip" aria-pressed="true" title="Убрать вопрос" onClick={() => setF({ ...f, asks: f.asks.filter((y) => y !== x) })}>{x} ×</button>)}
        </div>
        <div className="ag-add"><input className="r-input" aria-label="Свой вопрос" value={q} placeholder="Свой вопрос: например, есть ли бюджет на конференции?" onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addQ()} /><button className="r-btn" disabled={q.trim().length < 5} onClick={addQ}>Добавить</button></div>
        <p className="r-hint">Без ответа в&nbsp;вакансии вопрос попадёт в&nbsp;протокол строкой «уточнить на&nbsp;встрече».</p></div>
      <label className="r-switch"><input type="checkbox" checked={f.auto_decline} onChange={(e) => setF({ ...f, auto_decline: e.target.checked })} /><i />Отклонять приглашения со&nbsp;стоп-фактором самому</label>
      <div className="acts"><button className="r-btn r-btn--main" onClick={save}>{saved ? 'Сохранено' : 'Сохранить'}</button></div>
    </div>
  );
}

// Проверка агента на живой вакансии: тот же разговор, что увидит компания.
export function AgentCheck() {
  const { state, act } = useStore();
  const list = (state.cand.vacancies || []).slice(0, 6);
  const [res, setRes] = useState(null);
  const run = (v) => act(() => post('cand', `/candidate/vacancies/${v.id}/talk`)).then(setRes).catch(() => {});
  if (!list.length) return null;
  return (
    <div className="stack-sm">
      <h2 className="r-h3">Проверить агента на&nbsp;вакансии</h2>
      <p className="r-small r-mute">Сохраните настройку и&nbsp;выберите вакансию: агент проведёт тот&nbsp;же разговор, что увидит компания.</p>
      <div className="r-chips">{list.map((v) => <button key={v.id} className="r-chip" onClick={() => run(v)}>{v.company} · {v.title} · {fmtRange(v.salary_from, v.salary_to)}</button>)}</div>
      {res && <Modal title={`${res.company} · ${res.title}`} wide onClose={() => setRes(null)}><Negotiation talk={res.talk} company={res.company} who="вы" side="cand" /></Modal>}
    </div>
  );
}
