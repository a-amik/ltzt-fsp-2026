/* Переговоры с категорией. Агент работодателя проходит один сценарий со
   всеми кандидатами выдачи на сервере, человек читает строки протокола
   и пишет тем, с кем совпало. */
import { useEffect, useMemo, useState } from 'react';
import { gradeName, fmt } from './const.js';
import { Modal } from './ui.jsx';
import { Negotiation } from './Artifacts.jsx';

const ORDER = { ok: 0, part: 1, no: 2 };
const CELLS = [['Стек', 'Стек'], ['Грейд', 'Грейд'], ['Деньги', 'Деньги'], ['Формат', 'Формат'], ['Мотивация', 'Мотив']];
const WORD = { ok: 'Совпадает', part: 'С оговоркой', no: 'Расхождение', nodata: 'Нет данных' };

export default function Mass({ items, company, salaryTo, onInvite }) {
  const rows = useMemo(() => items.map((c, i) => ({ c, pos: i + 1, n: c.talk })), [items]);
  const [done, setDone] = useState(0);
  const [sel, setSel] = useState([]);
  const [open, setOpen] = useState(null);
  const [only, setOnly] = useState('all');
  useEffect(() => { setDone(0); setSel([]); }, [rows]);
  useEffect(() => { if (done >= rows.length) return; const t = setTimeout(() => setDone(Math.min(rows.length, done + 3)), 45); return () => clearTimeout(t); }, [done, rows.length]);
  const finished = done >= rows.length;
  const shown = rows.slice(0, done);
  const sorted = finished ? [...shown].sort((a, b) => ORDER[a.n.verdict.kind] - ORDER[b.n.verdict.kind] || a.pos - b.pos) : shown;
  const vis = only === 'all' ? sorted : sorted.filter((r) => r.n.verdict.kind === only);
  const cnt = { ok: 0, part: 0, no: 0 };
  shown.forEach((r) => cnt[r.n.verdict.kind]++);
  const miss = {};
  shown.forEach((r) => r.n.crit.forEach((x) => { if (x.state === 'no') miss[x.name] = (miss[x.name] || 0) + 1; }));
  const payNear = salaryTo ? shown.filter((r) => r.c.salary > salaryTo && r.c.salary <= salaryTo * 1.1 && r.n.crit.filter((x) => x.state === 'no').every((x) => x.name === 'Деньги')).length : 0;
  const toggle = (id) => setSel(sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id]);
  return (
    <div className="stack mass">
      <div className="mass-head r-card r-card--flat">
        <div>
          <p className="r-micro">Агент · {company} · {finished ? 'прогон закончен' : `переговоры ${done} из ${rows.length}`}</p>
          <div className="mass-bar" aria-hidden="true"><i style={{ width: `${(done / Math.max(1, rows.length)) * 100}%` }} /></div>
          <p className="r-small r-mute">Один сценарий со всеми: стек, грейд, деньги, формат, мотивация. Агенты кандидатов отвечают только одобренными фактами.</p>
        </div>
        <div className="mass-sum">
          <button className="mass-k k-ok" aria-pressed={only === 'ok'} onClick={() => setOnly(only === 'ok' ? 'all' : 'ok')}><b className="r-num">{cnt.ok}</b><span>совпало всё</span></button>
          <button className="mass-k k-part" aria-pressed={only === 'part'} onClick={() => setOnly(only === 'part' ? 'all' : 'part')}><b className="r-num">{cnt.part}</b><span>с оговорками</span></button>
          <button className="mass-k k-no" aria-pressed={only === 'no'} onClick={() => setOnly(only === 'no' ? 'all' : 'no')}><b className="r-num">{cnt.no}</b><span>расхождение</span></button>
        </div>
      </div>
      {finished && Object.keys(miss).length > 0 && (
        <div className="doc-note">
          Чаще всего расходимся: {Object.entries(miss).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k.toLowerCase()} — ${v}`).join(', ')}.
          {payNear > 0 && <> Поднять верх вилки на 10 % до {fmt(Math.round(salaryTo * 1.1 / 1000) * 1000)} — ещё <b>{payNear}</b> без расхождений.</>}
        </div>
      )}
      <div className="tablewrap scroll-x">
        <table className="r-table mass-t">
          <thead><tr><th aria-label="Выбрать" /><th>Место</th><th>Кандидат</th>{CELLS.map(([k, s]) => <th key={k} title={k}>{s}</th>)}<th>Итог</th></tr></thead>
          <tbody>{vis.map((r) => {
            const by = Object.fromEntries(r.n.crit.map((x) => [x.name, x]));
            return (
              <tr key={r.c.id} className={sel.includes(r.c.id) ? 'is-sel' : ''}>
                <td><label className="mass-chk"><input type="checkbox" checked={sel.includes(r.c.id)} onChange={() => toggle(r.c.id)} aria-label={`Выбрать ${r.c.display}`} /><i /></label></td>
                <td className="r-num">{r.pos}</td>
                <td><button className="linkish" onClick={() => setOpen(r)}>{r.c.display}</button><span className="r-small r-mute"> · {gradeName(r.c.grade)}{r.c.confirmed ? '' : ' · не подтверждён'}</span></td>
                {CELLS.map(([k]) => { const x = by[k]; return <td key={k}>{x ? <i className={`cdot cd-${x.state}`} title={`${WORD[x.state]}: ${x.note}`} /> : <span className="r-mute">—</span>}</td>; })}
                <td className={`mass-v v2-${r.n.verdict.kind}`}>{{ ok: 'Совпало', part: 'Оговорки', no: 'Нет' }[r.n.verdict.kind]}</td>
              </tr>
            );
          })}</tbody>
        </table>
      </div>
      <p className="r-small r-mute legend"><i className="cdot cd-ok" /> Совпадает <i className="cdot cd-part" /> С оговоркой <i className="cdot cd-no" /> Расхождение <i className="cdot cd-nodata" /> Нет данных · строка открывает протокол</p>
      <div className="mass-act">
        <button className="r-btn r-btn--sm" disabled={!finished} onClick={() => setSel(sorted.filter((r) => r.n.verdict.kind === 'ok').map((r) => r.c.id))}>Выбрать всех «совпало»</button>
        <button className="r-btn r-btn--main" disabled={!sel.length} onClick={() => onInvite(rows.filter((r) => sel.includes(r.c.id)).map((r) => r.c))}>Пригласить выбранных · {sel.length}…</button>
      </div>
      {open && (
        <Modal title={`Протокол · ${open.c.display}`} wide onClose={() => setOpen(null)}>
          <Negotiation talk={open.n} company={company} who={open.c.display} side="emp" instant />
          <div className="acts"><button className="r-btn r-btn--main" onClick={() => { onInvite([open.c]); setOpen(null); }}>Пригласить…</button></div>
        </Modal>
      )}
    </div>
  );
}
