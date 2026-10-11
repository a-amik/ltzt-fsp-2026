/* Рейтинговый тест под камерой и интервью с агентом — концепция на макетах.
   Камера, экран и микрофон нарисованы: ничего не снимается и не пишется.
   Вопрос голосом озвучивает синтез речи браузера, ответ — заготовка.
   Решения участника 11.10.2026 — лист fsp-2026/926p4ridynr8inmg. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useStore } from './store.jsx';
import { GRADES, spec, dateRu, plural, ZAD } from './const.js';
import { Mark, Modal } from './ui.jsx';
import './camera.css';

// ── Значки Lucide (ISC) ─────────────────────────────────────────────
const ICON = {
  video: <><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5" /><rect x="2" y="6" width="14" height="12" rx="2" /></>,
  videoOff: <><path d="M10.66 6H14a2 2 0 0 1 2 2v2.5l5.248-3.062A.5.5 0 0 1 22 7.87v8.196" /><path d="M16 16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2" /><path d="m2 2 20 20" /></>,
  mic: <><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4" /></>,
  monitor: <><rect width="20" height="14" x="2" y="3" rx="2" /><path d="M8 21h8M12 17v4" /></>,
  scan: <><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" /><circle cx="12" cy="10" r="3" /><path d="M7 18a6 6 0 0 1 10 0" /></>,
  check: <path d="M20 6 9 17l-5-5" />,
  info: <><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></>,
  bot: <><path d="M12 8V4H8" /><rect width="16" height="12" x="4" y="8" rx="2" /><path d="M2 14h2M20 14h2M15 13v2M9 13v2" /></>,
  volume: <><path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z" /><path d="M16 9a5 5 0 0 1 0 6M19.364 18.364a9 9 0 0 0 0-12.728" /></>,
  volumeOff: <><path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z" /><path d="m22 9-6 6M16 9l6 6" /></>,
  archive: <><rect width="20" height="5" x="2" y="3" rx="1" /><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8M10 12h4" /></>,
  cpu: <><rect width="16" height="16" x="4" y="4" rx="2" /><rect width="6" height="6" x="9" y="9" rx="1" /><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2" /></>,
  play: <path d="M6 3 20 12 6 21Z" />,
  text: <><path d="M4 7V4h16v3M9 20h6M12 4v16" /></>,
};
export const Ico = ({ n, size = 16, title }) => (
  <svg className="cm-ico" viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" role={title ? 'img' : undefined} aria-hidden={title ? undefined : true} aria-label={title}>{title && <title>{title}</title>}{ICON[n]}</svg>
);
// Свойство грейда «под камерой»: значок у грейда, не четвёртая метка происхождения (решение 5.4).
export const CamBadge = () => <span className="cm-badge" title="Грейд подтверждён тестом под камерой: лицо, экран и голос в одной записи"><Ico n="video" size={14} /></span>;

// ── Задания. Голосовые — свои, не пересказ экранных (решение 5.2) ───
const SCREEN = [
  { skill: 'Базы данных', q: 'Запрос по полю status идёт полным проходом таблицы на 40 млн строк. Значений у status четыре, нужно одно — «new», его 0,3 %. Что поможет быстрее всего?', opts: ['B-tree индекс по status', 'Частичный индекс WHERE status = \'new\'', 'Hash-индекс по status', 'Поднять shared_buffers'] },
  { skill: 'Python', q: 'Сервис на asyncio под нагрузкой отвечает всё медленнее, процессор загружен на 15 %. Где искать первым делом?', opts: ['Синхронный вызов внутри корутины', 'Мало воркеров uvicorn', 'Медленный JSON-сериализатор', 'Сборщик мусора'] },
  { skill: 'Архитектура', q: 'Сообщение о заказе может прийти из очереди дважды. Как сделать обработку безопасной?', opts: ['Ключ идемпотентности и уникальный индекс', 'Подтверждать сообщение до обработки', 'Увеличить таймаут видимости', 'Одна партиция на всю очередь'] },
  { skill: 'Сети', q: 'Клиент получает 502 от nginx, приложение за ним живо и отвечает на прямой запрос. Что проверить?', opts: ['Адрес и порт upstream, таймауты прокси', 'Сертификат на клиенте', 'DNS клиента', 'Размер заголовков ответа'] },
  { skill: 'Тестирование', q: 'Интеграционный тест падает раз в 20 запусков. Что сделать первым?', opts: ['Найти общий ресурс и порядок зависимости', 'Добавить повтор теста', 'Поднять таймауты', 'Пометить как нестабильный'] },
  { skill: 'Кэш', q: 'После сброса кэша база легла под одновременными запросами к одному ключу. Как защититься?', opts: ['Блокировка на пересчёт ключа', 'Уменьшить TTL', 'Добавить реплику базы', 'Кэшировать на клиенте'] },
];
const VOICE = [
  { skill: 'Базы данных', q: 'Расскажите, как вы поймёте, что запрос в PostgreSQL не использует индекс, и что сделаете дальше.', a: 'Сначала смотрю план через explain analyze: если там Seq Scan по большой таблице, проверяю селективность условия и статистику. Если статистика старая — analyze, если условие на редкое значение — частичный индекс.' },
  { skill: 'Архитектура', q: 'Как сделать повтор запроса к платёжному сервису, чтобы деньги не списались дважды?', a: 'На каждый платёж генерирую ключ идемпотентности и передаю его в заголовке. Сервис по ключу возвращает прежний результат. Повторы — с экспоненциальной задержкой, и только на сетевые ошибки и пятисотые.' },
  { skill: 'Эксплуатация', q: 'Ночью задержка ответа сервиса выросла втрое. Назовите первые три шага.', a: 'Смотрю, что менялось: выкладки и конфиги за ночь. Потом метрики по зависимостям — база, очередь, внешние API. И разрез по эндпоинтам: всё медленно или один запрос.' },
];
const TRIAL = { q: 'Назовите свой основной стек — это пробный вопрос, он не оценивается.', a: 'Python, FastAPI, PostgreSQL, немного Go.' };

// Порядок случайный, в среднем один голосовой на три (решение 5.2): у каждого кандидата свой.
function makeSeq() {
  const items = [...SCREEN.map((t) => ({ ...t, kind: 'screen' })), ...VOICE.map((t) => ({ ...t, kind: 'voice' }))];
  for (let i = items.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [items[i], items[j]] = [items[j], items[i]]; }
  return items;
}

// ── Синтез речи: вопрос звучит голосом ─────────────────────────────
function say(text, on, done) {
  const ss = window.speechSynthesis;
  if (!on || !ss) { const t = setTimeout(done, 2600); return () => clearTimeout(t); }
  ss.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'ru-RU'; u.rate = 1.05;
  const v = ss.getVoices().find((x) => x.lang?.startsWith('ru')); if (v) u.voice = v;
  let fired = false; const fin = () => { if (!fired) { fired = true; done(); } };
  u.onend = fin; u.onerror = fin;
  ss.speak(u);
  const guard = setTimeout(fin, 15000);
  return () => { clearTimeout(guard); ss.cancel(); };
}

// ── Кадры: камера, экран, агент ───────────────────────────────────
export function CamFrame({ label = 'Вы', off, rec = true, mesh = true }) {
  return (
    <div className={`cm-frame${off ? ' is-off' : ''}`}>
      <svg viewBox="0 0 160 120" aria-hidden="true" preserveAspectRatio="xMidYMid slice">
        <rect width="160" height="120" className="cm-bg" />
        {!off && <>
          <path d="M34 120c3-25 22-37 46-37s43 12 46 37z" className="cm-person" />
          <ellipse cx="80" cy="54" rx="19" ry="23" className="cm-person" />
          {mesh && <g className="cm-mesh">
            <circle cx="72" cy="50" r="1.6" /><circle cx="88" cy="50" r="1.6" /><circle cx="80" cy="58" r="1.2" /><circle cx="74" cy="66" r="1.2" /><circle cx="86" cy="66" r="1.2" />
            <path d="M62 32h6M62 32v6M98 32h-6M98 32v6M62 78h6M62 78v-6M98 78h-6M98 78v-6" />
          </g>}
        </>}
      </svg>
      {off && <span className="cm-frame__off"><Ico n="videoOff" size={22} /></span>}
      {rec && !off && <span className="cm-rec"><i />Запись</span>}
      <span className="cm-tag">{label}</span>
    </div>
  );
}

function ScreenFrame({ voice }) {
  return (
    <div className="cm-frame cm-frame--screen">
      <div className="cm-mini">
        <i className="w60" /><i className="w90" /><i className="w75" />
        {voice ? <b className="cm-mini__wave"><i /><i /><i /><i /><i /></b> : <><s /><s /><s /></>}
      </div>
      <span className="cm-rec"><i />Экран</span>
    </div>
  );
}

function Wave({ on, n = 7, cls = '' }) {
  return <span className={`cm-wave ${cls}${on ? ' is-on' : ''}`} aria-hidden="true">{Array.from({ length: n }, (_, i) => <i key={i} style={{ animationDelay: `${(i % 4) * -0.18 - i * 0.07}s` }} />)}</span>;
}

function AgentTile({ speaking, big }) {
  return (
    <div className={`cm-agent r-card${big ? ' cm-agent--big' : ''}`}>
      <span className="cm-agent__orb"><Wave on={speaking} n={5} /></span>
      <span className="cm-tag">Агент Разряда</span>
      <span className="cm-agent__state r-small">{speaking ? 'Говорит' : 'Слушает'}</span>
    </div>
  );
}

// Текст вопроса печатается по буквам — только по кнопке «Показать текст».
const calm = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
function TypeText({ text }) {
  const [n, setN] = useState(() => (calm() ? text.length : 0));
  useEffect(() => { if (n >= text.length) return; const t = setTimeout(() => setN(n + 1), 28); return () => clearTimeout(t); }, [n, text]);
  return <p className="cm-qtext" aria-label={text}>{text.slice(0, n)}{n < text.length && <span className="cm-caret" />}</p>;
}
// Голосовой вопрос в карточке задания: агент говорит здесь же, а не в боковой колонке.
function VoiceBlock({ speaking, q, ask = 'Агент задаёт вопрос…', onReplay, agent = true, children }) {
  const [shown, setShown] = useState(false);
  return (
    <div className={`cm-vblock${agent ? '' : ' is-bare'}`}>
      {agent && <div className="cm-vblock__agent"><span className="cm-agent__orb"><Wave on={speaking} n={5} /></span><span className="r-small r-mute">{speaking ? 'Говорит' : 'Слушает'}</span></div>}
      <div className="cm-voice">
        <p className="r-h3 cm-voice__q">{!agent && <Ico n="volume" size={20} />}{speaking ? ask : 'Отвечайте вслух'}</p>
        {shown && <TypeText text={q} />}
        {(!shown || onReplay) && (
          <div className="cm-vblock__acts">
            {!shown && <button className="r-btn r-btn--sm" onClick={() => setShown(true)}><Ico n="text" size={14} />Показать текст</button>}
            {onReplay && <button className="r-btn r-btn--sm" onClick={onReplay}><Ico n="volume" size={14} />Повторить вопрос</button>}
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

// ── Раскладки (решение 5.5: обе, выбирает кандидат) ─────────────────
const LAYOUTS = [['a', 'Задание в центре'], ['b', 'Как созвон']];
function LayoutSeg({ value, onChange }) {
  return <div className="seg" role="group" aria-label="Раскладка экрана">{LAYOUTS.map(([id, name]) => <button key={id} aria-pressed={value === id} onClick={() => onChange(id)}>{name}</button>)}</div>;
}
function LayoutPick({ value, onChange }) {
  return (
    <div className="cm-pick">
      {LAYOUTS.map(([id, name]) => (
        <button key={id} className="cm-pick__opt r-card" aria-pressed={value === id} onClick={() => onChange(id)}>
          <span className="cm-pick__mark" aria-hidden="true"><Ico n="check" size={14} /></span>
          <svg viewBox="0 0 160 96" aria-hidden="true" className="cm-pick__wire">
            {id === 'a' ? <><rect x="6" y="6" width="100" height="84" rx="4" /><rect x="114" y="6" width="40" height="30" rx="4" className="hi" /><rect x="114" y="42" width="40" height="30" rx="4" /><rect x="114" y="80" width="40" height="6" rx="2" className="hi" /></>
              : <><rect x="6" y="6" width="72" height="38" rx="4" className="hi" /><rect x="82" y="6" width="72" height="38" rx="4" /><rect x="6" y="50" width="148" height="40" rx="4" /></>}
          </svg>
          <b>{name}</b>
          <span className="r-small r-mute">{id === 'a' ? 'Камера и экран сбоку, задание крупно' : 'Агент и вы сверху, задание снизу'}</span>
        </button>
      ))}
    </div>
  );
}

// ── Отчёт сессии: кандидату и работодателю ─────────────────────────
const EP = {
  gaze: ['Взгляд с экрана', 'note'], read: ['Чтение во время ответа', 'ask'], voice2: ['Второй голос', 'ask'],
  face2: ['Второе лицо в кадре', 'ask'], tab: ['Уход со вкладки', 'note'], paste: ['Вставка', 'note'], pause: ['Долгая пауза', 'note'], stop: ['Тест на паузе', 'note'],
};
const mmss = (m) => `${String(Math.floor(m)).padStart(2, '0')}:${String(Math.round((m % 1) * 60)).padStart(2, '0')}`;
const VARIANTS = [
  { minutes: 23, eps: [{ t: 4.1, k: 'gaze', task: 2, text: 'Взгляд вниз, 3 с. Кандидат смотрит на клавиатуру, руки в кадре' }, { t: 15.6, k: 'pause', task: 6, text: 'Пауза 6 с перед голосовым ответом, потом ответ без запинок' }] },
  { minutes: 27, eps: [{ t: 6.4, k: 'tab', task: 3, text: 'Уход со вкладки, 4 с' }, { t: 12.2, k: 'read', task: 5, text: 'Во время голосового ответа взгляд идёт строками слева направо, 18 с' }, { t: 21.8, k: 'gaze', task: 8, text: 'Взгляд вправо за край экрана, 5 с' }] },
  { minutes: 31, eps: [{ t: 3.2, k: 'paste', task: 1, text: 'Вставка 240 знаков в поле ответа' }, { t: 9.7, k: 'voice2', task: 4, text: 'Второй голос в комнате во время ответа, 7 с' }, { t: 18.4, k: 'read', task: 6, text: 'Чтение с экрана во время голосового ответа, 22 с' }, { t: 26.1, k: 'face2', task: 8, text: 'Второе лицо в кадре, 2 с' }] },
];
const MOODS = ['Спокойно, ровный темп', 'Уверенно, речь без пауз', 'Заметное напряжение, темп ниже обычного', 'Уверенно, короткие ответы', 'Сомнение в начале, затем уверенно'];
function buildReport(seq, v, extra = {}) {
  const kinds = seq.map((t) => t.kind);
  const voiceAt = kinds.map((k, i) => (k === 'voice' ? i : -1)).filter((i) => i >= 0);
  return { minutes: v.minutes, kinds, eps: v.eps, emo: voiceAt.map((i, j) => ({ task: i + 1, mood: MOODS[(i + j) % MOODS.length], conf: [0.82, 0.67, 0.74, 0.58, 0.9][(i + j) % 5] })), ...extra };
}
// Работодателю — макет: у половины подтверждённых кандидатов есть тест под камерой.
const hash = (s) => [...String(s)].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7);
export function camOf(c) {
  if (!c?.confirmed) return null;
  const h = hash(c.id ?? c.display);
  if (h % 2) return null;
  const order = ['screen', 'voice', 'screen', 'screen', 'voice', 'screen', 'screen', 'voice', 'screen'];
  return buildReport(order.map((kind) => ({ kind })), VARIANTS[h % 3], { date: new Date(Date.now() - (h % 40) * 86400e3).toISOString(), bio: h % 5 < 3, interview: h % 4 === 0 });
}
const keepTill = (d) => { const x = new Date(d); x.setMonth(x.getMonth() + 6); return dateRu(x.toISOString()); };

export function CamReport({ r, own, locked }) {
  const [sel, setSel] = useState(0);
  const [argue, setArgue] = useState(null);
  const [argued, setArgued] = useState({});
  const asks = r.eps.filter((e) => EP[e.k][1] === 'ask').length;
  const ep = r.eps[sel];
  const n = r.kinds.length, nv = r.kinds.filter((k) => k === 'voice').length;
  const counts = Object.entries(r.eps.reduce((a, e) => ({ ...a, [e.k]: (a[e.k] || 0) + 1 }), {}));
  return (
    <div className="cm-report stack">
      <div className="cm-report__head">
        <p className="r-h3 cm-verdict"><span className={`cm-dot ${asks ? 'is-ask' : 'is-ok'}`} />{asks ? `Есть вопросы: ${asks} ${asks === 1 ? 'эпизод' : 'эпизода'}` : 'Нарушений не найдено'}</p>
        <p className="r-small r-mute">{r.minutes} мин · {plural(n, ...ZAD)}, {nv} голосом · {dateRu(r.date)}</p>
        <div className="cm-chips">
          {r.bio && <span className="r-chip cm-chip" title="Лицо сверено с фото ФСП ID с согласия кандидата: тест проходил тот, кто зарегистрировался"><Ico n="scan" size={14} />Личность сверена</span>}
          {r.interview && <span className="r-chip cm-chip" title="Кандидат прошёл интервью с агентом по фактам своего профиля"><Ico n="bot" size={14} />Интервью с агентом</span>}
          <span className="r-chip cm-chip" title={`Запись сжата и хранится в архиве 6 месяцев, до ${keepTill(r.date)}. Разметка и расшифровка — локальной моделью на сервере Разряда, в облачные сервисы запись не уходит`}><Ico n="archive" size={14} />До {keepTill(r.date)}</span>
        </div>
      </div>

      <div className="cm-tl" role="group" aria-label="Шкала сессии">
        <div className="cm-tl__bar">
          {r.kinds.map((k, i) => <span key={i} className={`cm-tl__seg${k === 'voice' ? ' is-voice' : ''}`} title={`Задание ${i + 1}${k === 'voice' ? ', голосом' : ''}`} />)}
          {r.eps.map((e, i) => (
            <button key={i} className={`cm-tl__ep is-${EP[e.k][1]}`} style={{ left: `${(e.t / r.minutes) * 100}%` }} aria-pressed={sel === i} onClick={() => setSel(i)} title={`${mmss(e.t)} · ${EP[e.k][0]}`} aria-label={`${mmss(e.t)}, ${EP[e.k][0]}`} />
          ))}
        </div>
        <div className="cm-tl__axis r-small r-mute"><span>00:00</span><span className="cm-tl__legend"><i className="is-voice" />Голосом <i className="is-ask" />Вопрос <i className="is-note" />Отметка</span><span>{mmss(r.minutes)}</span></div>
      </div>

      {ep && (
        <div className="cm-ep r-card r-card--flat">
          <div className="cm-ep__frames"><CamFrame label={mmss(ep.t)} rec={false} /><ScreenFrame voice={r.kinds[ep.task - 1] === 'voice'} /></div>
          <div className="stack-sm">
            <p><span className={`cm-dot is-${EP[ep.k][1]}`} /><b>{EP[ep.k][0]}</b> · задание {ep.task} · {mmss(ep.t)}</p>
            <p className="r-small">{ep.text}</p>
            {argued[sel] && <p className="r-small"><Mark src="word">Кандидат</Mark> {argued[sel]}</p>}
            <div className="acts" style={{ marginTop: 0 }}>
              <button className="r-btn r-btn--sm" disabled={locked} title={locked ? 'Запись откроется, когда кандидат примет приглашение' : 'Десять секунд записи вокруг отметки'}><Ico n="play" size={12} />Смотреть 10 с</button>
              {own && !argued[sel] && <button className="r-btn r-btn--sm r-btn--quiet" onClick={() => setArgue(sel)}>Оспорить эпизод…</button>}
            </div>
          </div>
        </div>
      )}

      <div className="tablewrap scroll-x"><table className="r-table">
        <thead><tr><th>Сигнал</th><th>За сессию</th><th>Как читать</th></tr></thead>
        <tbody>
          {counts.map(([k, v]) => <tr key={k}><td><span className={`cm-dot is-${EP[k][1]}`} />{EP[k][0]}</td><td className="r-num">{v}</td><td className="r-small">{EP[k][1] === 'ask' ? 'Стоит посмотреть запись' : 'Обычное поведение, отмечено для полноты'}</td></tr>)}
          {!counts.length && <tr><td colSpan="3" className="r-mute">Сигналов нет</td></tr>}
        </tbody>
      </table></div>

      <div className="cm-emo r-card r-card--flat">
        <p className="r-h3">Эмоции и уверенность <span className="cm-info" title="Модель оценивает выражение лица и голос и может ошибаться. На балл, грейд и место в выдаче не влияет — прикладывается к отчёту записке для собеседования."><Ico n="info" size={14} /></span></p>
        <p className="r-small r-mute">Справочно, на балл не влияет</p>
        <ul className="cm-emo__list">
          {r.emo.map((e) => <li key={e.task}><span className="r-small">Задание {e.task}</span><span>{e.mood}</span><span className="cm-conf" title={`Уверенность в голосе: ${Math.round(e.conf * 100)} % по оценке модели`}><i style={{ width: `${e.conf * 100}%` }} /></span></li>)}
        </ul>
      </div>

      {argue != null && (
        <Modal title="Оспорить эпизод" onClose={() => setArgue(null)}>
          <ArgueForm ep={r.eps[argue]} onDone={(t) => { setArgued({ ...argued, [argue]: t }); setArgue(null); }} />
        </Modal>
      )}
    </div>
  );
}
function ArgueForm({ ep, onDone }) {
  const [t, setT] = useState('');
  return (<>
    <p className="r-small r-mute">{mmss(ep.t)} · {EP[ep.k][0]}. Пояснение увидит работодатель рядом с отметкой.</p>
    <div className="r-field wide"><label className="r-label" htmlFor="argue">Что происходило</label><textarea id="argue" className="r-area" rows={3} value={t} onChange={(e) => setT(e.target.value)} placeholder="Смотрел в окно, думал над ответом" /></div>
    <div className="acts"><button className="r-btn r-btn--main" disabled={t.trim().length < 5} onClick={() => onDone(t.trim())}>Отправить</button></div>
  </>);
}

// ── Карточки во вкладке «Категория и грейд» ─────────────────────────
const TIERS = [['cam', 'Под камерой', 'Место в рейтинге категории'], ['prep', 'Подготовительный', 'Категория и грейд, ниже рейтинговых'], ['none', 'Грейд не подтверждён', 'В выдаче ниже всех']];
export function CamCards() {
  const { state, dispatch } = useStore();
  const m = state.cand.profile, done = state.ui.camDone, iv = state.ui.camInterview;
  const tier = done ? 'cam' : m.grade != null ? 'prep' : 'none';
  const go = (cam) => { dispatch({ type: 'ui', patch: { cam } }); window.scrollTo(0, 0); };
  return (
    <div className="cm-cards">
      <div className="r-card stack-sm">
        <p className="r-micro">Рейтинговый тест</p>
        <h2 className="r-h3">Под камерой: лицо, экран и голос</h2>
        <ol className="cm-tiers">{TIERS.map(([id, name, sub]) => <li key={id} className={id === 'cam' ? `r-card--sun cm-sun cm-goal${tier === id ? ' is-done' : ''}` : tier === id ? 'is-on' : ''}><b>{id === 'cam' && <Ico n="video" size={14} />}{name}{id === 'cam' && tier === 'cam' && <Ico n="check" size={14} title="Пройден" />}</b><span className="r-small r-mute">{sub}</span></li>)}</ol>
        <div className="acts" style={{ marginTop: 0 }}>
          {done ? <button className="r-btn" onClick={() => go('report')}>Отчёт сессии…</button> : <button className="r-btn r-btn--main" onClick={() => go('prep')}>Пройти рейтинговый тест…</button>}
        </div>
      </div>
      <div className="r-card stack-sm">
        <p className="r-micro">По желанию · 10 минут</p>
        <h2 className="r-h3">Интервью с агентом</h2>
        <p className="r-small">Агент спрашивает о&nbsp;фактах вашего профиля: соревнованиях ФСП, коде, опыте. Это точка верификации&nbsp;— она поднимает место в&nbsp;выдаче.</p>
        <div className="acts" style={{ marginTop: 0 }}>
          {iv ? <span className="r-small"><Ico n="check" size={14} /> Пройдено {dateRu(iv.date)}</span> : <button className="r-btn" onClick={() => go('interview')}>Начать интервью…</button>}
        </div>
      </div>
    </div>
  );
}

// ── Поток: подготовка → тест → итог; интервью ──────────────────────
export default function CameraFlow() {
  const { state, dispatch } = useStore();
  const step = state.ui.cam;
  const set = (patch) => dispatch({ type: 'ui', patch });
  const close = () => { window.speechSynthesis?.cancel(); set({ cam: null, candTab: 'grade' }); window.scrollTo(0, 0); };
  const [cfg, setCfg] = useState(() => ({ layout: state.ui.camLayout || 'a', bio: true, sound: true }));
  const setLayout = (layout) => { setCfg((c) => ({ ...c, layout })); set({ camLayout: layout }); };
  if (step === 'report' && state.ui.camDone) return <Final r={state.ui.camDone} onClose={close} onInterview={() => set({ cam: 'interview' })} />;
  if (step === 'run') return <Run cfg={cfg} setCfg={setCfg} setLayout={setLayout} onClose={close} onDone={(r) => { set({ cam: 'report', camDone: r }); window.scrollTo(0, 0); }} />;
  if (step === 'interview') return <Interview cfg={cfg} setCfg={setCfg} setLayout={setLayout} onClose={close} onDone={() => { set({ cam: null, candTab: 'grade', camInterview: { date: new Date().toISOString() } }); window.scrollTo(0, 0); }} />;
  return <Prep cfg={cfg} setCfg={setCfg} setLayout={setLayout} onClose={close} onStart={() => { set({ cam: 'run' }); window.scrollTo(0, 0); }} />;
}

function Head({ micro, title, onClose, children }) {
  return (
    <div className="cm-head">
      <div><p className="r-micro">{micro}</p><h1 className="r-h2 cm-title">{title}</h1></div>
      <div className="cm-head__acts">{children}<button className="r-btn r-btn--sm r-btn--quiet" onClick={onClose}>Выйти</button></div>
    </div>
  );
}
const SoundBtn = ({ on, toggle }) => <button className="r-btn r-btn--sm r-btn--quiet cm-iconbtn" onClick={toggle} aria-pressed={on} aria-label={on ? 'Выключить звук агента' : 'Включить звук агента'} title={on ? 'Выключить звук агента' : 'Включить звук агента'}><Ico n={on ? 'volume' : 'volumeOff'} /></button>;

function Prep({ cfg, setCfg, setLayout, onClose, onStart }) {
  const { state } = useStore();
  const m = state.cand.profile;
  const CHECKS = [['video', 'Камера'], ['mic', 'Микрофон'], ['monitor', 'Весь экран'], ['monitor', 'Один монитор']];
  const [ok, setOk] = useState(0);
  const [agree, setAgree] = useState(false);
  const [face, setFace] = useState(false);
  const [trial, setTrial] = useState('idle');
  useEffect(() => { if (ok >= CHECKS.length) return; const t = setTimeout(() => setOk(ok + 1), 450); return () => clearTimeout(t); }, [ok]);
  useEffect(() => { setFace(false); if (!cfg.bio) return; const t = setTimeout(() => setFace(true), 1400); return () => clearTimeout(t); }, [cfg.bio]);
  const stop = useRef(null);
  useEffect(() => () => stop.current?.(), []);
  const runTrial = () => { setTrial('ask'); stop.current = say(TRIAL.q, cfg.sound, () => setTrial('answer')); };
  return (
    <div className="page">
      <Head micro={`Рейтинговый тест · ${spec(m.spec).name} · ${GRADES[m.grade ?? m.claimed_grade].name}`} title="Подготовка, две минуты" onClose={onClose}><SoundBtn on={cfg.sound} toggle={() => setCfg({ ...cfg, sound: !cfg.sound })} /></Head>
      <div className="cm-prep">
        <div className="stack">
          <div className="r-card stack-sm">
            <h2 className="r-h3">Оборудование</h2>
            <CamFrame />
            <ul className="cm-checks">{CHECKS.map(([ic, name], i) => <li key={name} className={i < ok ? 'is-ok' : ''}><Ico n={ic} />{name}<span className="cm-checks__st">{i < ok ? <Ico n="check" /> : 'Проверяем…'}</span></li>)}</ul>
          </div>
          <div className="r-card stack-sm">
            <h2 className="r-h3">Пробный вопрос голосом</h2>
            <p className="r-small r-mute">Агент задаёт вопрос вслух, отвечаете тоже вслух. Пробный не&nbsp;оценивается.</p>
            <div className="cm-voice">
              <AgentTile speaking={trial === 'ask'} />
              {trial === 'idle' && <button className="r-btn" onClick={runTrial}><Ico n="volume" />Задать пробный вопрос</button>}
              {trial === 'ask' && <p className="r-small">Агент говорит…</p>}
              {trial === 'answer' && <VoiceAnswer text={TRIAL.a} onDone={() => setTrial('done')} />}
              {trial === 'done' && <p className="r-small"><Ico n="check" /> Слышно хорошо. Так же пройдут голосовые задания.</p>}
            </div>
          </div>
        </div>
        <div className="stack">
          <div className="r-card stack-sm">
            <h2 className="r-h3">Раскладка экрана</h2>
            <p className="r-small r-mute">Поменять можно и&nbsp;во&nbsp;время теста.</p>
            <LayoutPick value={cfg.layout} onChange={setLayout} />
          </div>
          <div className="r-card stack-sm cm-consent">
            <h2 className="r-h3">Согласие на запись</h2>
            <ul className="cm-facts r-small">
              <li><Ico n="video" />Пишем лицо, экран и&nbsp;голос всю сессию</li>
              <li><Ico n="cpu" />Разметка и&nbsp;расшифровка&nbsp;— локальной моделью <span className="cm-info" title="Модели работают на сервере Разряда: MediaPipe для взгляда и лиц, Whisper для расшифровки. В облачные сервисы запись не уходит"><Ico n="info" size={13} /></span></li>
              <li><Ico n="archive" />Запись хранится 6&nbsp;месяцев в&nbsp;сжатом архиве</li>
              <li><Ico n="info" />Эмоции и&nbsp;уверенность&nbsp;— справочно, на&nbsp;балл не&nbsp;влияют <span className="cm-info" title="Модель может ошибиться. Оценка прикладывается к отчёту запиской, на грейд и место в выдаче не влияет"><Ico n="info" size={13} /></span></li>
              <li><Ico n="scan" />Отчёт видите вы и&nbsp;компании, чьё приглашение вы&nbsp;приняли</li>
            </ul>
            <label className="r-switch"><input type="checkbox" checked={cfg.bio} onChange={(e) => setCfg({ ...cfg, bio: e.target.checked })} /><i />Сверить лицо с&nbsp;фото ФСП ID <span className="cm-info" title="Биометрия по 152-ФЗ: согласие отдельное, его можно отозвать. Сверка поднимает место в выдаче — работодатель уверен, что тест проходили вы"><Ico n="info" size={13} /></span></label>
            {cfg.bio && <p className="r-small cm-face">{face ? <><Ico n="check" /> Лицо совпадает с&nbsp;ФСП ID</> : 'Сверяем лицо…'}</p>}
            <div className="cm-consent__go">
              <label className="r-switch"><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} /><i />Согласен на&nbsp;запись</label>
              <button className="r-btn r-btn--main r-btn--lg" disabled={!agree || ok < CHECKS.length || (cfg.bio && !face)} onClick={onStart}>Начать тест</button></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Ответ голосом — макет: волна и расшифровка, которая набирается по ходу «речи».
function VoiceAnswer({ text, onDone, label = 'Закончить ответ' }) {
  const [rec, setRec] = useState(false);
  const [shown, setShown] = useState(0);
  useEffect(() => { if (!rec || shown >= text.length) return; const t = setTimeout(() => setShown(Math.min(text.length, shown + 3)), 45); return () => clearTimeout(t); }, [rec, shown, text]);
  if (!rec) return <button className="r-btn r-btn--main" onClick={() => setRec(true)}><Ico n="mic" />Ответить голосом</button>;
  return (
    <div className="cm-answer stack-sm">
      <div className="cm-answer__row"><Wave on={shown < text.length} n={12} cls="cm-wave--you" /><span className="r-small r-mute">{shown < text.length ? 'Слушаем…' : 'Ответ записан'}</span></div>
      <p className="cm-transcript">{text.slice(0, shown)}{shown < text.length && <span className="cm-caret" />}</p>
      <div><button className="r-btn r-btn--sm" disabled={shown < Math.min(text.length, 40)} onClick={onDone}>{label}</button></div>
    </div>
  );
}

function Run({ cfg, setCfg, setLayout, onClose, onDone }) {
  const { state } = useStore();
  const m = state.cand.profile;
  const seq = useMemo(makeSeq, []);
  const [i, setI] = useState(0);
  const [pick, setPick] = useState(null);
  const [phase, setPhase] = useState('ask');
  const [paused, setPaused] = useState(false);
  const [sec, setSec] = useState(0);
  const [tick, setTick] = useState(0);
  const [replayed, setReplayed] = useState(-1);
  const cur = seq[i];
  const stop = useRef(null);
  useEffect(() => { if (paused) return; const t = setInterval(() => setSec((s) => s + 1), 1000); return () => clearInterval(t); }, [paused]);
  useEffect(() => {
    setPick(null);
    if (cur.kind !== 'voice') return;
    setPhase('ask');
    stop.current = say(cur.q, cfg.sound, () => setPhase('answer'));
    return () => stop.current?.();
  }, [i, tick]);
  const next = () => {
    if (i + 1 < seq.length) { setI(i + 1); return; }
    // Отчёт — макет: настоящую разметку делает локальная модель после сессии.
    onDone(buildReport(seq, VARIANTS[hash(Date.now()) % 2], { date: new Date().toISOString(), bio: cfg.bio, layout: cfg.layout, interview: !!state.ui.camInterview }));
  };
  const task = cur.kind === 'voice' ? (
    <div className={`r-card cm-task${phase === 'answer' ? ' r-card--sun cm-sun' : ''}`}>
      <div className="task-head"><span className="r-micro">{cur.skill} · голосом</span><span className="r-micro">{i + 1} из {seq.length}</span></div>
      <VoiceBlock key={i} speaking={phase === 'ask'} q={cur.q} agent={cfg.layout === 'a'} onReplay={phase === 'answer' && replayed !== i ? () => { setReplayed(i); setTick((x) => x + 1); } : null}>
        {phase === 'answer' && <VoiceAnswer key={i} text={cur.a} onDone={next} label={i + 1 < seq.length ? 'Закончить ответ' : 'Закончить тест'} />}
      </VoiceBlock>
    </div>
  ) : (
    <div className="r-card cm-task">
      <div className="task-head"><span className="r-micro">{cur.skill} · на экране</span><span className="r-micro">{i + 1} из {seq.length}</span></div>
      <p className="task-q">{cur.q}</p>
      <div className="opts">{cur.opts.map((o) => <button key={o} className="r-chip opt" aria-pressed={pick === o} onClick={() => setPick(o)}>{o}</button>)}</div>
      <div className="acts"><button className="r-btn r-btn--main" disabled={pick == null} onClick={next}>{i + 1 < seq.length ? 'Ответить' : 'Ответить и закончить'}</button></div>
    </div>
  );
  const speaking = cur.kind === 'voice' && phase === 'ask';
  const signals = (
    <ul className="cm-live r-small">
      <li><Ico n="check" size={13} />Лицо в кадре</li><li><Ico n="check" size={13} />Один голос</li><li><Ico n="check" size={13} />Вкладка активна</li>
    </ul>
  );
  return (
    <div className="page">
      <Head micro={`Рейтинговый тест · ${spec(m.spec).name} · ${mmss(sec / 60)}`} title={`Задание ${i + 1} из ${seq.length}`} onClose={onClose}>
        <LayoutSeg value={cfg.layout} onChange={setLayout} />
        <SoundBtn on={cfg.sound} toggle={() => setCfg({ ...cfg, sound: !cfg.sound })} />
        <button className="r-btn r-btn--sm r-btn--quiet" onClick={() => { stop.current?.(); setPaused(true); }} title="Показать, что видит кандидат, когда камера теряет лицо">Пауза: пример</button>
      </Head>
      <div className="cm-progress" aria-hidden="true">{seq.map((t, j) => <i key={j} className={`${j < i ? 'is-done' : ''}${j === i ? ' is-cur' : ''}${t.kind === 'voice' && j < i ? ' is-voice' : ''}`} />)}</div>
      {cfg.layout === 'a' ? (
        <div className="cm-run cm-run--a">
          {task}
          <aside className="cm-side stack-sm">
            <CamFrame />
            <ScreenFrame voice={cur.kind === 'voice'} />
            {signals}
          </aside>
        </div>
      ) : (
        <div className="cm-run cm-run--b stack">
          <div className="cm-call">
            <AgentTile speaking={speaking} big />
            <div className="cm-you"><CamFrame /><div className="cm-you__pip"><ScreenFrame voice={cur.kind === 'voice'} /></div></div>
          </div>
          {task}
          {signals}
        </div>
      )}
      {paused && (
        <Modal title="Тест на паузе" onClose={() => setPaused(false)}>
          <div className="cm-pause">
            <CamFrame off rec={false} />
            <div className="stack-sm">
              <p><b>Камера не&nbsp;видит лицо.</b> Время остановлено, задание сохранено.</p>
              <p className="r-small r-mute">Тест не&nbsp;провален. Пауза попадёт в&nbsp;отчёт отметкой без штрафа.</p>
              <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--main" onClick={() => { setPaused(false); if (cur.kind === 'voice' && phase === 'ask') setTick((x) => x + 1); }}>Я в кадре, продолжить</button></div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Final({ r, onClose, onInterview }) {
  const { state } = useStore();
  const m = state.cand.profile;
  const g = m.grade ?? m.claimed_grade;
  return (
    <div className="page">
      <Head micro="Рейтинговый тест · итог" title="Грейд подтверждён под камерой" onClose={onClose} />
      <div className="cm-final">
        <div className="r-card r-card--blue cat-card">
          <p className="r-micro on-blue">Ваша категория</p>
          <p className="cat-name">{spec(m.spec).name} · {GRADES[g].name} <Ico n="video" size={22} /></p>
          <p className="r-num">Место в рейтинге категории{r.bio ? ' · личность сверена' : ''}</p>
        </div>
        {!state.ui.camInterview && (
          <div className="r-card r-card--sun cm-sun stack-sm">
            <h2 className="r-h3">Следующая точка верификации</h2>
            <p className="r-small">Интервью с&nbsp;агентом по&nbsp;фактам профиля, 10&nbsp;минут. Поднимает место в&nbsp;выдаче.</p>
            <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--main" onClick={onInterview}>Начать интервью…</button></div>
          </div>
        )}
      </div>
      <h2 className="r-h2">Отчёт сессии</h2>
      <p className="r-small r-mute">Тот&nbsp;же отчёт увидит компания, чьё приглашение вы&nbsp;примете. Эпизод можно оспорить&nbsp;— пояснение встанет рядом с&nbsp;отметкой.</p>
      <CamReport r={r} own />
    </div>
  );
}

// ── Интервью с агентом по фактам профиля ────────────────────────────
function interviewQs(m) {
  const qs = [];
  (m.fsp || []).filter((a) => !a.hidden).slice(0, 2).forEach((a) => qs.push({ src: 'fsp', fact: `${a.event}, ${a.year}: ${a.place} место`, q: `Вы заняли ${a.place} место на «${a.event}» в ${a.year} году. Какую задачу там решали дольше всего и почему?`, a: 'Дольше всего сидели над задачей на графы: сначала пошли перебором, упёрлись в лимит времени, потом переписали на динамику по подмножествам.' }));
  (m.facts || []).filter((f) => f.approved && f.src !== 'word').slice(0, 2).forEach((f) => qs.push({ src: f.src, fact: `${f.k}: ${f.v}`, q: `В профиле указано: «${f.k}: ${f.v}». Расскажите, как это было устроено и что вы сделали сами.`, a: 'Я отвечал за сервис целиком: схема данных, очередь задач и метрики. Самое трудное было убрать двойную обработку при повторах.' }));
  qs.push({ src: 'test', fact: 'Тест под камерой', q: 'В тесте вы выбрали частичный индекс. Где такое решение может подвести?', a: 'Если запросы начнут фильтровать по другому значению, индекс не поможет, а при частых сменах статуса будет лишняя запись в индекс.' });
  qs.push({ src: 'word', fact: 'Со слов кандидата', q: 'Какую задачу вы хотели бы решать на следующей работе?', a: 'Нагруженный бэкенд с понятными метриками, где можно отвечать за сервис от схемы до продакшена.' });
  return qs.slice(0, 5);
}
function Interview({ cfg, setCfg, setLayout, onClose, onDone }) {
  const { state } = useStore();
  const qs = useMemo(() => interviewQs(state.cand.profile), [state.cand.profile]);
  const [i, setI] = useState(-1);
  const [phase, setPhase] = useState('ask');
  const stop = useRef(null);
  useEffect(() => { if (i < 0 || i >= qs.length) return; setPhase('ask'); stop.current = say(qs[i].q, cfg.sound, () => setPhase('answer')); return () => stop.current?.(); }, [i]);
  if (i >= qs.length) return (
    <div className="page">
      <Head micro="Интервью с агентом · итог" title="Интервью записано" onClose={onClose} />
      <div className="r-card stack-sm cm-narrow">
        <p>Ответов записано и&nbsp;расшифровано: {qs.length}. У&nbsp;фактов профиля появилась отметка «Рассказал агенту», в&nbsp;выдаче&nbsp;— точка верификации.</p>
        <ul className="cm-facts r-small">{qs.map((q) => <li key={q.q}><Mark src={q.src} />{q.fact}</li>)}</ul>
        <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--main" onClick={onDone}>В кабинет</button></div>
      </div>
    </div>
  );
  const q = qs[Math.max(0, i)];
  const card = i < 0 ? (
    <div className="r-card stack-sm cm-task">
      <p>{qs.length}&nbsp;{qs.length < 5 ? 'вопроса' : 'вопросов'} о&nbsp;фактах вашего профиля, около 10&nbsp;минут. Агент дождётся конца ответа и&nbsp;не&nbsp;перебьёт.</p>
      <ul className="cm-facts r-small">{qs.map((x) => <li key={x.q}><Mark src={x.src} />{x.fact}</li>)}</ul>
      <div className="acts" style={{ marginTop: 0 }}><button className="r-btn r-btn--main" onClick={() => setI(0)}>Начать</button></div>
    </div>
  ) : (
    <div className={`r-card cm-task${phase === 'answer' ? ' r-card--sun cm-sun' : ''}`}>
      <div className="task-head"><span className="r-micro"><Mark src={q.src} /> {q.fact}</span><span className="r-micro">{i + 1} из {qs.length}</span></div>
      <VoiceBlock key={i} speaking={phase === 'ask'} q={q.q} ask="Агент спрашивает…" agent={cfg.layout === 'a'}>
        {phase === 'answer' && <VoiceAnswer key={i} text={q.a} onDone={() => setI(i + 1)} label={i + 1 < qs.length ? 'Следующий вопрос' : 'Закончить интервью'} />}
      </VoiceBlock>
    </div>
  );
  const speaking = i >= 0 && phase === 'ask';
  return (
    <div className="page">
      <Head micro="Интервью с агентом · по желанию" title={i < 0 ? 'Расскажите о своём опыте' : `Вопрос ${i + 1} из ${qs.length}`} onClose={onClose}>
        <LayoutSeg value={cfg.layout} onChange={setLayout} />
        <SoundBtn on={cfg.sound} toggle={() => setCfg({ ...cfg, sound: !cfg.sound })} />
      </Head>
      {cfg.layout === 'a' ? (
        <div className="cm-run cm-run--a">{card}<aside className="cm-side stack-sm"><CamFrame /></aside></div>
      ) : (
        <div className="cm-run cm-run--b stack"><div className="cm-call"><AgentTile speaking={speaking} big /><div className="cm-you"><CamFrame /></div></div>{card}</div>
      )}
    </div>
  );
}
