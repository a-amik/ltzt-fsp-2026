import { useEffect } from 'react';
import { GRADES } from './const.js';

const MARK = { fsp: ['r-mark--fsp', 'ФСП'], test: ['r-mark--code', 'тест'], interview: ['r-mark--code', 'встреча'], word: ['r-mark--word', 'со слов'] };
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

export const Empty = ({ img, title, children }) => (
  <div className="r-empty">{img && <img src={img} alt="" className="empty-img" />}<p className="r-h3">{title}</p><div className="r-mute">{children}</div></div>
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
export const Status = ({ s }) => <span className={`status ${STATUS_CLS[s] || ''}`}>{s}</span>;
