/* Регулярные короткие задания. Работодатель даёт категории задачу из бэклога,
   ответы приходят без имён, оценка поднимает кандидата в выдаче. */
import { useState } from 'react';
import { useStore } from './store.jsx';
import { post } from './api.js';
import { GRADES, SPECS, spec, gradeName, dateRu } from './const.js';
import { Empty, Modal } from './ui.jsx';

const SCORE = [['Слабо', 0], ['Годно', 0.5], ['Сильно', 1]];

export function EmployerTasks() {
  const { state, act } = useStore();
  const tasks = state.emp.tasks || [];
  const [open, setOpen] = useState(tasks[0]?.id || null);
  const [form, setForm] = useState(false);
  const t = tasks.find((x) => x.id === open) || tasks[0];
  const rate = (a, score) => act(() => post('emp', `/employer/tasks/answers/${a.id}/score?score=${score}`), 'emp');
  return (
    <div className="stack">
      <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--main" onClick={() => setForm(true)}>Новое задание…</button></div>
      {!tasks.length && <Empty title="Заданий нет">Дайте категории задачу из своего бэклога — ответы придут без имён.</Empty>}
      <div className="task-list">
        {tasks.map((x) => (
          <button key={x.id} className={`r-card task-item ${t?.id === x.id ? 'is-on' : ''}`} onClick={() => setOpen(x.id)}>
            <span className="r-micro">{spec(x.spec).name} · {gradeName(x.grade)}</span>
            <b>{x.title}</b>
            <span className="r-small r-mute">ответов {x.answers.length} · оценено {x.answers.filter((a) => a.score != null).length}</span>
          </button>
        ))}
      </div>
      {t && (
        <section className="doc">
          <header className="doc-head">
            <div><p className="r-micro">Задание · {dateRu(t.created_at)}</p><h2 className="r-h2 doc-title">{t.title}</h2><p className="r-small">{t.text}</p></div>
            <div className="doc-kpis"><div><b className="r-num">{t.answers.length}</b><span>ответили</span></div></div>
          </header>
          {!t.answers.length && <p className="r-mute">Ответы ещё идут.</p>}
          {t.answers.map((a) => (
            <article key={a.id} className="answer">
              <p className="r-micro">{a.candidate}</p>
              <p className="answer-text">{a.text}</p>
              <div className="answer-act"><div className="seg" role="group" aria-label="Оценка">{SCORE.map(([l, v]) => <button key={l} aria-pressed={a.score === v} onClick={() => rate(a, v)}>{l}</button>)}</div></div>
            </article>
          ))}
          <p className="r-small r-mute">Оценка добавляет кандидату свежий сигнал: решённое задание и его оценка входят в «свежесть» (10 % порядка). Имя откроется, только если вы пригласите и он примет.</p>
        </section>
      )}
      {form && <NewTask onClose={() => setForm(false)} />}
    </div>
  );
}

function NewTask({ onClose }) {
  const { state, act } = useStore();
  const need = state.emp.selection?.need;
  const [f, setF] = useState({ title: '', text: '', spec: need?.spec || 'backend', grade: need?.grade ?? 2 });
  const send = () => act(() => post('emp', '/employer/tasks', f), 'emp').then(onClose);
  return (
    <Modal title="Новое задание категории" onClose={onClose}>
      <div className="r-field wide"><label className="r-label" htmlFor="tt">Задача</label><input id="tt" className="r-input" value={f.title} placeholder="Например: очередь уведомлений без дублей" onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
      <div className="r-field wide"><label className="r-label" htmlFor="tx">Условие</label><textarea id="tx" className="r-area" value={f.text} placeholder="Что дано, что нужно, в каком виде ответ" onChange={(e) => setF({ ...f, text: e.target.value })} /></div>
      <p className="r-label">Кому</p>
      <div className="r-chips scroll-x nowrap">{SPECS.map((s) => <button key={s.id} className="r-chip" aria-pressed={f.spec === s.id} onClick={() => setF({ ...f, spec: s.id })}>{s.name}</button>)}</div>
      <div className="r-chips scroll-x nowrap mt-s">{GRADES.map((g) => <button key={g.id} className="r-chip" aria-pressed={f.grade === g.id} onClick={() => setF({ ...f, grade: g.id })}>{g.name}</button>)}</div>
      <p className="r-small mt-s">Задание увидят кандидаты категории и соседних грейдов. Ответ — подход в 3–5 предложениях.</p>
      <div className="acts"><button className="r-btn r-btn--main" disabled={f.title.length < 5 || f.text.length < 20} onClick={send}>Разослать категории</button></div>
    </Modal>
  );
}

export function CandidateTasks() {
  const { state, act } = useStore();
  const mine = state.cand.tasks || [];
  const [text, setText] = useState({});
  if (!mine.length) return <Empty title="Заданий пока нет">Работодатели присылают короткие задачи вашей категории.</Empty>;
  return (
    <div className="stack">
      {mine.map((t) => {
        const a = t.answer;
        const label = a?.score == null ? null : SCORE.find(([, v]) => v === a.score)?.[0];
        return (
          <div key={t.id} className="r-card r-card--flat stack-sm">
            <p className="r-micro">{t.company} · задание категории · {gradeName(t.grade)}</p>
            <p className="r-h3">{t.title}</p>
            <p>{t.text}</p>
            {!a ? (<>
              <textarea className="r-area" rows={4} value={text[t.id] || ''} onChange={(e) => setText({ ...text, [t.id]: e.target.value })} placeholder="Ваш подход в 3–5 предложениях" aria-label="Ваш подход" />
              <button className="r-btn r-btn--main r-btn--sm" disabled={(text[t.id] || '').trim().length < 30} onClick={() => act(() => post('cand', `/candidate/tasks/${t.id}/answer`, { text: text[t.id] }), 'cand')}>Отправить без имени</button>
            </>) : (
              <p className="r-small">{label ? <>Работодатель оценил: <b>{label}</b>. Сигнал добавлен в профиль.</> : 'Отправлено. Ждёт оценки работодателя — компания видит ответ без имени.'}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
