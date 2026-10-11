import { useEffect, useRef, useState } from 'react';
import { GRADES, cap } from './const.js';

const MARK = { fsp: ['r-mark--fsp', 'ФСП'], test: ['r-mark--code', 'Тест'], interview: ['r-mark--code', 'Встреча'], word: ['r-mark--word', 'Со слов'] };
export function Mark({ src, children }) {
  if (src === 'warn') return <span className="r-mark r-mark--warn">{children || '!'}</span>;
  const [cls, label] = MARK[src] || MARK.word;
  return <span className={`r-mark ${cls}`} title={{ fsp: 'Подтверждено реестром ФСП', test: 'Подтверждено тестом платформы', interview: 'Подтверждено работодателем после встречи', word: 'Со слов кандидата, не проверено' }[src]}>{children || label}</span>;
}

export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const k = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k); document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', k); document.body.style.overflow = ''; };
  }, [onClose]);
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal r-card scroll ${wide ? 'modal--wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head"><h2 className="r-h3">{title}</h2><button className="r-btn r-btn--sm" onClick={onClose} aria-label="Закрыть">✕</button></div>
        {children}
      </div>
    </div>
  );
}

const PART_NAMES = { test: 'Тест', stack: 'Стек', fsp: 'ФСП', fresh: 'Свежесть' };
export function Score({ parts }) {
  return (
    <div className="r-score" title="Из чего сложилось место в выдаче">
      <div className="r-score__bars" style={{ gridTemplateColumns: 'repeat(4, 1fr)', height: 44 }}>
        {Object.entries(parts).map(([k, v]) => <div key={k} className="r-score__bar"><i style={{ '--r-fill': `${Math.round(v * 100)}%` }} /></div>)}
      </div>
      <div className="r-score__legend" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        {Object.keys(parts).map((k) => <span key={k}>{PART_NAMES[k]}</span>)}
      </div>
    </div>
  );
}

/* Ход адаптивного теста: оценка после каждого ответа и её погрешность
   на фоне полос грейдов. Видно, как тест сужает коридор и где остановился. */
export function Trace({ trace, claimed, height = 220 }) {
  const W = 520, H = height, pad = { l: 64, r: 12, t: 10, b: 26 };
  const n = Math.max(trace.length, 8);
  const x = (i) => pad.l + (i / (n - 1 || 1)) * (W - pad.l - pad.r);
  const y = (t) => pad.t + ((2.8 - Math.max(-2.8, Math.min(2.8, t))) / 5.6) * (H - pad.t - pad.b);
  const band = trace.map((p, i) => [x(i), y(p.theta + p.se)]).concat(trace.map((p, i) => [x(i), y(p.theta - p.se)]).reverse());
  return (
    <svg className="trace" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Ход оценки навыка по шагам теста">
      {GRADES.map((g) => (
        <g key={g.id}>
          <rect x={pad.l} y={y(Math.min(g.to, 2.8))} width={W - pad.l - pad.r} height={y(Math.max(g.from, -2.8)) - y(Math.min(g.to, 2.8))} className={g.id === claimed ? 'trace-claimed' : g.id % 2 ? 'trace-band' : 'trace-band2'} />
          <text x={pad.l - 8} y={(y(Math.min(g.to, 2.8)) + y(Math.max(g.from, -2.8))) / 2 + 4} textAnchor="end" className="trace-label">{g.name}</text>
        </g>
      ))}
      {trace.length > 0 && <polygon points={band.map((p) => p.join(',')).join(' ')} className="trace-se" />}
      {trace.length > 0 && <polyline points={trace.map((p, i) => `${x(i)},${y(p.theta)}`).join(' ')} className="trace-line" />}
      {trace.map((p, i) => <circle key={`d${i}`} cx={x(i)} cy={y(p.theta)} r="5" className={p.ok == null ? 'trace-dot' : p.ok ? 'trace-dot ok' : 'trace-dot bad'} />)}
      {Array.from({ length: n }, (_, i) => <text key={`t${i}`} x={x(i)} y={H - 6} textAnchor="middle" className="trace-label">{i === 0 ? 'старт' : i}</text>)}
    </svg>
  );
}

// Значки пустых экранов — Lucide (ISC): в ките ФСП они заменяют рисунки «Разряда».
const LUCIDE = {
  mail: <><rect width="20" height="16" x="2" y="4" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" /></>,
  trophy: <><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" /><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" /><path d="M4 22h16" /><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" /><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" /><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" /></>,
  inbox: <><polyline points="22 12 16 12 14 15 10 15 8 12 2 12" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /></>,
};
const ICON_OF = { './empty-invite.svg': 'mail', './empty-fsp.svg': 'trophy' };
export const Empty = ({ img, icon, title, children }) => (
  <div className="r-empty">
    <span className="r-empty__icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">{LUCIDE[icon || ICON_OF[img] || 'inbox']}</svg></span>
    {img && <img src={img} alt="" className="empty-img" />}<p className="r-h3">{title}</p><div className="r-mute">{children}</div></div>
);

export function Tabs({ items, value, onChange }) {
  return (
    <nav className="tabs scroll-x" aria-label="Разделы">
      {items.map(([id, label, badge]) => (
        <button key={id} className="tab" aria-current={value === id ? 'page' : undefined} onClick={() => onChange(id)}>
          {label}{badge ? <span className="tab-badge r-num">{badge}</span> : null}
        </button>
      ))}
    </nav>
  );
}

export const STATUS_CLS = { 'отправлено': '', 'просмотрено': 'st-seen', 'принято': 'st-ok', 'отклонено': 'st-no' };
export const Status = ({ s }) => <span className={`status ${STATUS_CLS[s] || ''}`}>{cap(s)}</span>;

// Голосовой ввод: распознавание браузера (Chrome, Edge, Safari) по-русски; где его нет — подсказка про диктовку системы.
const SYS_DICT = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? 'дважды нажмите Fn (🌐)' : 'нажмите Win + H';
const SR_ERR = {
  'not-allowed': 'Браузер не дал микрофон — разрешите его в адресной строке',
  'service-not-allowed': `Распознавание в браузере выключено — ${SYS_DICT}, это диктовка системы`,
  'audio-capture': 'Микрофон не найден',
  network: `Сервис распознавания недоступен — ${SYS_DICT}, это диктовка системы`,
  'no-speech': 'Ничего не расслышали — нажмите микрофон и говорите',
};
const capFirst = (s) => s.charAt(0).toUpperCase() + s.slice(1);
export function Dictate({ value, onChange, onStart, children }) {
  const [on, setOn] = useState(false);
  const [msg, setMsg] = useState('');
  const rec = useRef(null), wrap = useRef(null), cb = useRef(onChange);
  useEffect(() => { cb.current = onChange; });
  useEffect(() => () => rec.current?.abort(), []);
  const toggle = () => {
    if (rec.current) { rec.current.stop(); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setMsg(`Браузер не распознаёт речь сам: ${SYS_DICT} и говорите — текст появится в поле`); wrap.current?.querySelector('textarea, input')?.focus(); return; }
    const head = value.replace(/\s+$/, '');
    const base = head ? `${head} ` : '';
    const r = new SR();
    r.lang = 'ru-RU'; r.continuous = true; r.interimResults = true;
    r.onresult = (e) => {
      const t = Array.from(e.results, (x) => x[0].transcript.trim()).filter(Boolean).join(' ');
      cb.current(base + (!head || /[.!?]$/.test(head) ? capFirst(t) : t));
    };
    r.onerror = (e) => e.error !== 'aborted' && setMsg(SR_ERR[e.error] || 'Распознавание прервалось — попробуйте ещё раз');
    r.onend = () => { rec.current = null; setOn(false); };
    try { r.start(); } catch { setMsg(`Не удалось включить распознавание — ${SYS_DICT}`); return; }
    rec.current = r; setOn(true); setMsg(''); onStart?.();
  };
  return (<>
    <div className="dict" ref={wrap}>
      {children}
      <button type="button" className="dict-btn" aria-pressed={on} onClick={toggle} aria-label={on ? 'Остановить диктовку' : 'Надиктовать голосом'} title={on ? 'Остановить диктовку' : 'Надиктовать голосом'}>
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
      </button>
    </div>
    {(on || msg) && <span className="r-hint" aria-live="polite">{on ? 'Говорите — текст появляется в поле. Нажмите микрофон ещё раз, чтобы закончить.' : msg}</span>}
  </>);
}
