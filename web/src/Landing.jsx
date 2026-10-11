import { useEffect, useRef, useState } from 'react';
import { GRADES, WEIGHTS } from './const.js';
import { Mark } from './ui.jsx';
import { useStore } from './store.jsx';
import './landing.css';
import candArt from './assets/landing/cand-steps.svg?raw';
import empArt from './assets/landing/emp-steps.svg?raw';
import agentsArt from './assets/landing/scene-agents.svg?raw';
import photoEmpPath from './assets/landing/photo/photo-emp-path.webp';
import photoEmployer from './assets/landing/photo/photo-employer.webp';
import photoMeet from './assets/landing/photo/photo-meet.webp';
import faceE1 from './assets/landing/photo/face-e1.webp';
import faceE2 from './assets/landing/photo/face-e2.webp';
import faceE3 from './assets/landing/photo/face-e3.webp';
import rzHero from './assets/landing/photo/rz-hero.webp';
import rzPath from './assets/landing/photo/rz-path.webp';
import rzContest from './assets/landing/photo/rz-contest.webp';
import rzFinal from './assets/landing/photo/rz-final.webp';
import rzFaceC1 from './assets/landing/photo/rz-face-c1.webp';
import rzFaceC2 from './assets/landing/photo/rz-face-c2.webp';
import rzFaceC3 from './assets/landing/photo/rz-face-c3.webp';
const LOGO_SVG = import.meta.glob('./assets/landing/logos/*.svg', { query: '?raw', import: 'default', eager: true });
const CMP_SVG = import.meta.glob('./assets/landing/cmp/*.svg', { query: '?raw', import: 'default', eager: true });
const DISC_SVG = import.meta.glob('./assets/landing/disc/*.svg', { query: '?raw', import: 'default', eager: true });
import moveCandArt from './assets/landing/move-cand.svg?raw';
import moveEmpArt from './assets/landing/move-emp.svg?raw';

/* Главная: лендинг для кандидата и работодателя. Рисунки вставлены
   inline, чтобы брали краски темы (var(--r-*)) и двигались своим CSS. */
const Art = ({ svg, className = '' }) => <div className={`ld-art ${className}`} aria-hidden="true" dangerouslySetInnerHTML={{ __html: svg }} />;

// Неразрывные пробелы: после коротких слов, перед тире, между числом и знаком.
const ty = (t) => t.replace(/(^|[\s(«])(в|и|с|к|о|у|а|не|на|по|за|от|до|из|без|под|для|или|но|ни|он|её|их) /gi, '$1$2\u00a0').replace(/ —/g, '\u00a0—').replace(/(\d) (%|₽|тыс\.)/g, '$1\u00a0$2').replace(/тыс\. ₽/g, 'тыс.\u00a0₽');

const ICON = {
  lock: <><rect width="18" height="11" x="3" y="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></>,
  trophy: <><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" /><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" /><path d="M4 22h16" /><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" /><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" /><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" /></>,
  check: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><polyline points="16 11 18 13 22 9" /></>,
  play: <polygon points="6 3 20 12 6 21 6 3" />,
  ok: <polyline points="20 6 9 17 4 12" />,
  plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
  quote: <><path d="M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z" /><path d="M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z" /></>,
  shield: <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />,
  info: <><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></>,
  again: <><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /></>,
};
const Icon = ({ name, size = 20 }) => <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICON[name]}</svg>;

// Блок проявляется, когда доезжает до экрана; без поддержки — виден сразу.
function Reveal({ children, className = '', as: Tag = 'section', id }) {
  const ref = useRef(null);
  const [on, setOn] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || !('IntersectionObserver' in window)) { setOn(true); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setOn(true); io.disconnect(); } }, { rootMargin: '0px 0px -10% 0px' });
    io.observe(el); return () => io.disconnect();
  }, []);
  return <Tag ref={ref} id={id} className={`ld-reveal ${on ? 'is-on' : ''} ${className}`}>{children}</Tag>;
}

const PATHS = {
  cand: {
    art: candArt, photo: rzPath,
    steps: [
      ['Тест определяет грейд за 6–12 заданий', 'Выбираете специализацию и грейд. Следующее задание подбирается по прошлым ответам; тест останавливается, когда оценка точная.'],
      ['Профиль показывает, что подтверждено', 'У каждого факта метка источника: реестр ФСП, тест или ваши слова. Работодатель видит её рядом с фактом.'],
      ['Вилка зарплаты известна сразу', 'Работодатели вашей категории пишут первыми и указывают её в каждом приглашении. Почта и телефон открываются, когда вы согласились.'],
    ],
    go: ['cand', 'Пройти тест'],
  },
  emp: {
    art: empArt, photo: photoEmpPath,
    steps: [
      ['Категория вместо поиска по резюме', 'Видите категории «специализация × грейд» и число людей в каждой. Грейд подтверждён тестом, неподтверждённые стоят ниже с\u00a0меткой.'],
      ['Видно, почему кандидат выше', `Тест — ${WEIGHTS.test * 100} %, стек — ${Math.round(WEIGHTS.stack * 100)} %, ФСП — ${WEIGHTS.fsp * 100} %, свежесть — ${WEIGHTS.fresh * 100} %, отзывы коллег — ${Math.round(WEIGHTS.social * 100)} %. У каждого кандидата строка «почему здесь» со ссылкой на факт.`],
      ['Приглашение с вилкой зарплаты', 'Без неё приглашение не отправить; если вилка ниже ожиданий кандидата, предупредим до отправки. Агенты сторон заранее сверят условия.'],
    ],
    go: ['emp', 'Найти людей'],
  },
};

const PATH_H = { cand: 'Три шага от\u00a0теста до\u00a0приглашения', emp: 'Три шага от\u00a0запроса до\u00a0встречи' };
function Paths({ go, side }) {
  const p = PATHS[side];
  return (
    <Reveal className="ld-sec" id="kak">
      <div className="ld-copy"><h2 className="r-h1">{PATH_H[side]}</h2></div>
      <div className="ld-path r-card r-card--flat">
        <ol className="ld-steps">
          {p.steps.map(([t, d], i) => (
            <li key={t} style={{ '--i': i }}><span className="ld-n r-num">{i + 1}</span><div><h3 className="r-h3">{ty(t)}</h3><p className="r-mute">{ty(d)}</p></div></li>
          ))}
        </ol>
        <div className="ld-path-art"><div className="ld-path-media"><img className="ld-photo" src={p.photo} alt="" loading="lazy" width="1600" height="1067" /><div className="ld-path-inset"><Art svg={p.art} /></div></div><button className="r-btn r-btn--main" onClick={() => go(p.go[0])}>{p.go[1]}</button></div>
      </div>
    </Reveal>
  );
}

/* Демо адаптивного теста. Банк из шести заданий с трудностью b; следующее —
   ближайшее по трудности к текущей оценке; шаг оценки уменьшается с каждым
   ответом, коридор погрешности сужается. Настоящий тест — в кабинете. */
const BANK = [
  { b: -1.6, q: 'len([1, 2, 3])', opts: ['2', '3', '6', 'Ошибка'], ok: 1 },
  { b: -0.8, q: '"abc"[::-1]', opts: ['"abc"', '"cba"', '"c"', 'Ошибка'], ok: 1 },
  { b: 0, q: 'SELECT COUNT(*) FROM t;\n-- в таблице t нет строк', opts: ['NULL', '0', 'Ошибка', 'Пустой результат'], ok: 1 },
  { b: 0.7, q: '[i * i for i in range(4)][-1]', opts: ['16', '9', '4', '3'], ok: 1 },
  { b: 1.3, q: 'Поиск ключа в сбалансированном\nдереве из n узлов занимает…', opts: ['O(1)', 'O(n)', 'O(log n)', 'O(n log n)'], ok: 2 },
  { b: 1.9, q: 'a = [[]] * 3\na[0].append(1)\nlen(a[1])', opts: ['0', '1', '3', 'Ошибка'], ok: 1 },
];
const SPAN = 2.8, LIMIT = 3;
const pos = (t) => ((Math.max(-SPAN, Math.min(SPAN, t)) + SPAN) / (2 * SPAN)) * 100;
const gradeOf = (t) => GRADES.find((g) => t >= g.from && t < g.to);

function TestDemo({ go }) {
  const [st, setSt] = useState({ theta: 0, se: 1.6, used: [], log: [] });
  const [pick, setPick] = useState(null);
  const done = st.log.length >= LIMIT;
  const item = done ? null : BANK.map((x, i) => [x, i]).filter(([, i]) => !st.used.includes(i)).sort((a, b) => Math.abs(a[0].b - st.theta) - Math.abs(b[0].b - st.theta))[0];
  const answer = (k) => {
    if (pick != null || !item) return;
    setPick(k);
    const ok = k === item[0].ok, n = st.log.length;
    setTimeout(() => {
      setSt({ theta: st.theta + (ok ? 1 : -1) * (1.1 / (n + 1)), se: 1.6 / Math.sqrt(n + 2), used: [...st.used, item[1]], log: [...st.log, ok] });
      setPick(null);
    }, 650);
  };
  const g = gradeOf(st.theta);
  return (
    <Reveal className="ld-sec ld-test" id="test">
      <div className="ld-copy">
        <p className="r-micro">Попробуйте</p>
        <h2 className="r-h1">Тест подстраивается под&nbsp;ответы</h2>
        <p className="r-mute">Верный ответ поднимает оценку, и&nbsp;следующее задание сложнее; ошибка опускает. Коридор на&nbsp;шкале — погрешность: с&nbsp;каждым ответом он&nbsp;уже. Здесь три задания, в&nbsp;кабинете — от&nbsp;6 до&nbsp;12.</p>
      </div>
      <div className="ld-demo r-card">
        <div className="ld-scale" aria-label={`Оценка: ${g.name}`}>
          <div className="ld-scale__bands">{GRADES.map((x) => <span key={x.id} className={x.id === g.id ? 'is-on' : ''}>{x.name}</span>)}</div>
          <div className="ld-scale__track">
            <i className="ld-scale__se" style={{ left: `${pos(st.theta - st.se)}%`, width: `${pos(st.theta + st.se) - pos(st.theta - st.se)}%` }} />
            <i className="ld-scale__dot" style={{ left: `${pos(st.theta)}%` }} />
          </div>
        </div>
        {item ? (
          <div className="ld-q" key={item[1]}>
            <div className="ld-q__top"><span className="r-micro">Задание {st.log.length + 1} из {LIMIT}</span><span className="r-micro r-num">Трудность {item[0].b.toFixed(1).replace('.', ',')}</span></div>
            <pre className="ld-q__code">{item[0].q}</pre>
            <div className="ld-q__opts">
              {item[0].opts.map((o, k) => (
                <button key={o} className={`r-btn ld-opt ${pick === k ? (k === item[0].ok ? 'is-ok' : 'is-bad') : ''} ${pick != null && pick !== k && k === item[0].ok ? 'is-ok' : ''}`} disabled={pick != null} onClick={() => answer(k)}>{o}</button>
              ))}
            </div>
          </div>
        ) : (
          <div className="ld-q ld-q--done">
            <p className="r-micro">Ваш результат</p>
            <p className="r-h2">{g.name} · {g.short}</p>
            <p className="r-mute">{st.log.filter(Boolean).length} из {LIMIT} верно. Настоящий грейд дают 6–12 заданий под вашу специализацию, и&nbsp;он встаёт в&nbsp;профиль с&nbsp;меткой <Mark src="test" />.</p>
            <div className="acts">
              <button className="r-btn r-btn--main" onClick={() => go('cand')}>Пройти настоящий тест</button>
              <button className="r-btn" onClick={() => setSt({ theta: 0, se: 1.6, used: [], log: [] })}><Icon name="again" size={18} />Ещё раз</button>
            </div>
          </div>
        )}
      </div>
    </Reveal>
  );
}

const FACTS = [
  { src: 'fsp', text: 'Призёр финала ФСП по продуктовому программированию, 2025', who: 'Реестр ФСП', how: 'Подтягивается по ФСП ID. Поднимает кандидата внутри категории; нет истории ФСП — ноль по строке, не штраф.' },
  { src: 'test', text: 'Бэкенд · Средний — 9 заданий, погрешность 0,34', who: 'Тест платформы', how: 'Определяет категорию и даёт 60 % веса в порядке выдачи. Повышение — только новым тестом.' },
  { src: 'word', text: '5 лет с Python и PostgreSQL, гибрид, от 250 тыс. ₽', who: 'Сам кандидат', how: 'Видно, но помечено как непроверенное. Агент кандидата пересказывает такие факты только с этой меткой.' },
];

function Provenance() {
  const [on, setOn] = useState(0);
  const f = FACTS[on];
  return (
    <Reveal className="ld-sec ld-prov" id="metki">
      <div className="ld-copy">
        <p className="r-micro">Метки происхождения</p>
        <h2 className="r-h1">Видно, откуда каждый факт</h2>
        <p className="r-mute">Резюме пишет сам человек, и&nbsp;проверить его нечем. В&nbsp;«Разряде» у&nbsp;факта есть источник, и&nbsp;работодатель видит его рядом. Нажмите на&nbsp;строку.</p>
      </div>
      <div className="ld-profile r-card">
        <div className="ld-profile__head">
          <span className="r-avatar" aria-hidden="true">К</span>
          <div><p className="r-h3">Кандидат №&nbsp;1042</p><p className="r-small r-mute">Бэкенд · Средний</p></div>
        </div>
        <ul className="ld-facts">
          {FACTS.map((x, i) => (
            <li key={x.src}><button className={i === on ? 'is-on' : ''} aria-pressed={i === on} onClick={() => setOn(i)}><Mark src={x.src} /><span>{ty(x.text)}</span></button></li>
          ))}
          <li className="ld-locked"><Icon name="lock" size={18} /><span>Почта и телефон откроются, когда кандидат примет приглашение</span></li>
        </ul>
        <div className="ld-why" key={on}><p className="r-label">Источник: {f.who}</p><p className="r-small r-mute">{ty(f.how)}</p></div>
      </div>
    </Reveal>
  );
}

const CRIT = ['Стек', 'Грейд', 'Деньги', 'Формат', 'Мотивация'];

const TALK = [
  ['emp', 'Был опыт с очередями сообщений под нагрузкой?'],
  ['cand', 'Тест подтвердил бэкенд, средний грейд; задание на обработку очереди Kafka решено.', 'test'],
  ['emp', 'Подходит гибрид, два дня в офисе?'],
  ['cand', 'Кандидат указал: гибрид или удалённо.', 'word'],
  ['emp', 'Вилка зарплаты 230–280 тыс. ₽.'],
  ['cand', 'Ожидания кандидата внутри вилки. Решение о встрече — за ним.'],
];

const AGENTS = {
  emp: { id: 'agenty', cap: 'Агенты', h: 'Агент собеседует всю категорию', p: 'Агент работодателя проходит с\u00a0каждым кандидатом категории один и\u00a0тот\u00a0же опрос. По\u00a0каждому вы получаете протокол и\u00a0балл совпадения и\u00a0зовёте на\u00a0встречу тех, кто совпал. Агент кандидата отвечает только одобренными фактами и\u00a0называет источник.' },
  cand: { id: 'agent', cap: 'Ваш агент', h: 'Первые вопросы работодателя берёт на\u00a0себя агент', p: 'Агент отвечает за\u00a0вас только теми фактами, что вы одобрили, и\u00a0называет источник каждого. Чего нет в\u00a0профиле, помечает «уточнит сам». Протокол разговора видите и\u00a0вы, и\u00a0работодатель; принять приглашение или отказать решаете вы.' },
};
function Agents({ side }) {
  const a = AGENTS[side];
  const [n, setN] = useState(0);
  const [play, setPlay] = useState(0);
  const run = play > 0 && n < TALK.length;
  useEffect(() => {
    if (!run) return;
    const t = setTimeout(() => setN((x) => x + 1), n === 0 ? 150 : 1100);
    return () => clearTimeout(t);
  }, [run, n, play]);
  const start = () => { setN(0); setPlay((x) => x + 1); };
  // Карточка не растёт: новые реплики прокручиваются внутри неё, к последней.
  const box = useRef(null);
  useEffect(() => { const el = box.current; if (el) el.scrollTo({ top: el.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); }, [n]);
  return (
    <Reveal className="ld-sec ld-agents" id={a.id}>
      <div className="ld-copy">
        <p className="r-micro">{a.cap}</p>
        <h2 className="r-h1">{a.h}</h2>
        <p className="r-mute">{a.p}</p>
        <ul className="ld-crit">{CRIT.map((c) => <li key={c}><Icon name="ok" size={16} />{c}</li>)}</ul>
        <button className="r-btn" onClick={start} disabled={run}><Icon name={n >= TALK.length ? 'again' : 'play'} size={18} />{n >= TALK.length ? 'Повторить разговор' : 'Показать разговор'}</button>
      </div>
      <div className="ld-talk r-card">
        {n === 0 ? <Art svg={agentsArt} className="ld-talk__art" /> : (
          <div className="r-talk scroll" aria-live="polite" ref={box}>
            {TALK.slice(0, n).map(([who, text, src], i) => (
              <div key={i} className={`r-turn r-turn--${who} ld-turn`}>
                <span className="r-turn__who">{who === 'emp' ? 'Агент работодателя' : 'Агент кандидата'}</span>
                <div className="r-turn__body">{ty(text)}{src && <> <Mark src={src} /></>}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Reveal>
  );
}

/* Как было — как в «Разряде». Подача по образцу зарубежных референсов:
   выигрыш человека первым, технология — ниже по странице. */
const COMPARE = {
  cand: [
    ['Сотня откликов, половина без ответа', 'Откликаться не нужно: компании вашей категории пишут первыми'],
    ['«Зарплата по договорённости» до третьего созвона', 'Вилка зарплаты известна сразу: без неё компания не отправит приглашение'],
    ['Тестовое в каждую компанию заново', 'Один тест на 20–30 минут, грейд видят все работодатели категории'],
    ['Медали олимпиад теряются в резюме', 'Призы ФСП поднимают внутри категории с меткой реестра'],
    ['Почту и телефон из резюме видит любой рекрутёр', 'Почта и телефон закрыты, пока вы не приняли приглашение'],
  ],
  emp: [
    ['Сотни откликов, грейд со слов кандидата', 'Категория с числом людей; видно, чей грейд подтверждён тестом'],
    ['Скрининг-звонок с каждым', 'Агенты сверяют стек, формат и деньги до приглашения'],
    ['Непонятно, почему поиск выдал этого человека', 'У каждого строка «почему здесь»: тест 60 %, стек 15 %, ФСП и свежесть по 10 %, отзывы коллег 5 %'],
    ['Тестовое отпугивает сильных', 'Короткое задание из своего бэклога всей категории, ответы без имён'],
    ['Вакансии заводить заново руками', 'Вставили текст своей вакансии — поля заполнились'],
  ],
};
const CMP_HEAD = { emp: ['ekonomiya', 'Скрининг проводят агенты', 'Люди решают одно: встречаться ли им.'], cand: ['bylo', 'Как было и\u00a0как стало', 'Что меняется в\u00a0поиске работы.'] };
function Compare({ side }) {
  const [id, h, sub] = CMP_HEAD[side];
  return (
    <Reveal className="ld-sec" id={id}>
      <div className="ld-copy"><h2 className="r-h1">{h}</h2><p className="r-mute">{sub}</p></div>
      <div className="ld-cmp r-card r-card--flat">
        <div className="ld-cmp__row ld-cmp__cap"><span /><span className="r-micro">Как было</span><span className="r-micro">В&nbsp;«Разряде»</span></div>
        {COMPARE[side].map(([was, now], i) => (
          <div key={was} className="ld-cmp__row" style={{ '--i': i }}><span className="ld-cmp__art" aria-hidden="true" dangerouslySetInnerHTML={{ __html: CMP_SVG[`./assets/landing/cmp/cmp-${side}-${i + 1}.svg`] || '' }} /><p className="r-mute">{ty(was)}</p><p><Icon name="ok" size={18} />{ty(now)}</p></div>
        ))}
      </div>
    </Reveal>
  );
}

/* Переезд: только свои данные стороны. Чужие вакансии не импортируем. */
function Move({ go, side }) {
  const { dispatch } = useStore();
  const toVac = () => { dispatch({ type: 'ui', patch: { empTab: 'vac' } }); go('emp'); };
  const cand = side === 'cand';
  return (
    <Reveal className="ld-sec">
      <div className="ld-copy">
        <p className="r-micro">Переезд</p>
        <h2 className="r-h1">Начните с&nbsp;того, что уже есть</h2>
        <p className="r-mute">Резюме, вакансию или пару фраз разбираем по&nbsp;полям. Всё распознанное получает метку «Со&nbsp;слов».</p>
      </div>
      <div className="r-card ld-move__card ld-move--one">
        <Art svg={cand ? moveCandArt : moveEmpArt} />
        <div className="ld-move__body">
          <p className="r-micro">{cand ? 'Кандидату' : 'Работодателю'}</p>
          {cand ? (
            <ul className="ld-list">
              <li><b>ФСП&nbsp;ID</b> — победы и&nbsp;призовые места встанут в&nbsp;профиль сами</li>
              <li><b>Резюме PDF или DOCX</b> из&nbsp;hh.ru, Хабр Карьеры, LinkedIn — имя, стек, стаж, места работы, ожидания</li>
              <li><b>Пара фраз голосом</b> — если резюме под рукой нет</li>
            </ul>
          ) : (
            <ul className="ld-list">
              <li><b>Текст своей вакансии</b> с&nbsp;сайта или из&nbsp;ATS — специализация, грейд, стек, вилка зарплаты, задачи разложатся по&nbsp;полям</li>
              <li><b>Файл описания</b> PDF, DOCX или TXT — тот&nbsp;же разбор</li>
              <li><b>«Кого ищете» своими словами</b> — первая выдача сразу, без вакансии</li>
            </ul>
          )}
          <button className="r-btn r-btn--main" onClick={cand ? () => go('cand') : toVac}>{cand ? 'Собрать профиль' : 'Перенести вакансию'}</button>
        </div>
      </div>
    </Reveal>
  );
}

const FAQ_MODEL = ['Агенты — это языковая модель?', 'Сейчас агенты работают на правилах: один протокол по пяти критериям и ответы только из одобренных фактов профиля. Следующим шагом подключаем модель (YandexGPT или GigaChat), чтобы реплики звучали как речь; к ней уходят только факты, которые кандидат одобрил к показу.'];
const FAQ = {
  cand: [
    ['Что, если я не пройду тест на свой грейд?', 'Вы останетесь в выдаче своей категории с меткой «грейд не подтверждён», ниже подтвердивших. Тест на ступень ниже можно пройти сразу; повышение — только новым тестом.'],
    ['Увидит ли нынешний работодатель, что я ищу работу?', 'Может, если он нанимает в вашей категории: имя и места работы работодатели видят сразу. Почта и телефон закрыты, пока вы не приняли приглашение, а любой факт профиля можно скрыть.'],
    ['Нет истории в ФСП — я буду ниже?', 'Только при прочих равных: ФСП весит 10 % порядка внутри категории, тест — 60 %. Без соревнований эта строка — ноль, штрафа нет.'],
    ['Что агент говорит от моего имени?', 'Только одобренные вами факты, и у каждого называет источник. Выключенный факт агент не назовёт — скажет, что вы уточните сами. Принять или отказать может только человек.'],
    FAQ_MODEL,
    ['Сколько это стоит?', 'Кандидату — бесплатно.'],
  ],
  emp: [
    ['Как агент собеседует кандидатов?', 'Один сценарий со всей категорией: стек, грейд, деньги, формат, мотивация. По каждому критерию — «Совпадает», «С оговоркой» или «Расхождение»; по каждому кандидату — протокол и балл.'],
    ['Почему грейду можно верить?', 'Грейд — результат адаптивного теста под категорию, а не строка резюме. Понижение — сразу, повышение — только новым тестом.'],
    ['Когда я увижу контакты?', 'Имя, места работы и профиль с метками видны сразу. Почта и телефон — после того, как кандидат принял приглашение.'],
    ['Как с персональными данными?', 'Кандидат даёт согласие на обработку при регистрации и сам решает, какие факты показывать. Контакты закрыты до его «да».'],
    FAQ_MODEL,
    ['Нужна интеграция с ATS?', 'В MVP — нет: вакансию переносите текстом или файлом, поля заполнятся сами. Интеграция с ATS — следующий шаг.'],
    ['Сколько это стоит?', 'В MVP работодателю бесплатно: поиск, приглашения и задания без оплаты.'],
  ],
};
function Faq({ side }) {
  return (
    <Reveal className="ld-sec" id="voprosy">
      <h2 className="r-h1">Вопросы</h2>
      <div className="ld-faq">
        {FAQ[side].map(([q, a]) => (
          <details key={q} className="ld-faq__item"><summary><span>{ty(q)}</span><Icon name="plus" size={20} /></summary><p className="r-mute">{ty(a)}</p></details>
        ))}
      </div>
    </Reveal>
  );
}

const TRUST = [
  ['lock', 'Контакты — после «да»', 'Работодатель видит имя, места работы и профиль с метками. Почту и телефон — только когда вы приняли приглашение.'],
  ['trophy', 'Без ФСП — не штраф', 'Победы и призовые места ФСП поднимают внутри категории. Без них место решают тест, стек и свежесть.'],
  ['check', 'Решает человек', 'Агенты готовят разговор, а принять приглашение или отказать с причиной может только кандидат.'],
];
const LAW = [
  ['check', 'Грейд подтверждён тестом', 'Категория строится по адаптивному тесту, а не по резюме. Без подтверждения кандидат стоит ниже с меткой «грейд не подтверждён».'],
  ['shield', 'Компания проверена', 'ИНН и корпоративная почта дают метку «Компания проверена» — кандидат видит её в приглашении.'],
  ['lock', '152-ФЗ', 'Согласие кандидата на обработку — при регистрации. Почта и телефон закрыты до его «да»; к модели, когда её подключим, уйдут только факты, которые он одобрил.'],
];
function Trust({ side }) {
  const emp = side === 'emp';
  return (
    <Reveal className="ld-sec" id={emp ? 'zakon' : undefined}>
      <h2 className="r-h1">{emp ? 'Что проверено и\u00a0что закрыто' : 'Что остаётся за\u00a0человеком'}</h2>
      <div className="ld-trust">
        {(emp ? LAW : TRUST).map(([ic, t, d], i) => (
          <div key={t} style={{ '--i': i }}><span className="ld-ic"><Icon name={ic} size={22} /></span><h3 className="r-h3">{ty(t)}</h3><p className="r-mute">{ty(d)}</p></div>
        ))}
      </div>
    </Reveal>
  );
}

/* Работодатели — те же компании, что в кабинете. */
const LOGOS = [
  ['transkod', 'ТрансКод'], ['oblachny-sklad', 'Облачный склад'], ['lenta-dannyh', 'Лента данных'], ['geoservis', 'ГеоСервис'],
  ['ritm-platezh', 'Ритм-Платёж'], ['medteh-plyus', 'МедТех Плюс'], ['logika-torga', 'Логика Торга'], ['finpotok', 'Финпоток'],
];
const logo = (k) => LOGO_SVG[`./assets/landing/logos/${k}.svg`];

function Logos({ side }) {
  return (
    <section className="ld-logos" aria-label="Работодатели">
      <p className="r-micro">{side === 'cand' ? 'Вас ищут компании' : 'Нанимают в\u00a0«Разряде»'}</p>
      <ul className="ld-logos__row">
        {LOGOS.map(([k, name]) => (
          <li key={k}>{logo(k) && <span className="ld-logo__mark" aria-hidden="true" dangerouslySetInnerHTML={{ __html: logo(k) }} />}<span className="ld-logo__name">{name}</span></li>
        ))}
      </ul>
    </section>
  );
}

const HERO = {
  emp: { h: 'Первый разговор ведут агенты', sub: 'Вы встречаетесь с\u00a0теми, кто уже совпал', go: ['emp', 'Найти людей'], other: 'Я ищу работу', facts: [['5 критериев', 'сверяет агент'], ['Грейд', 'подтверждён тестом'], ['Контакты', 'после «да» кандидата']], photo: photoEmployer },
  cand: { h: 'Ваш агент ведёт первый разговор', sub: 'Пройдите тест, и\u00a0работодатели увидят ваш грейд', go: ['cand', 'Пройти тест'], other: 'Я нанимаю', facts: [['6–12', 'заданий в\u00a0тесте'], ['Сразу', 'вилка зарплаты'], ['3 метки', 'источника у\u00a0фактов']], photo: rzHero },
};
const SIDES = [['emp', 'Компаниям'], ['cand', 'Кандидатам']];
function Switch({ side, setSide, pinned }) {
  return (
    <div className={`ld-switch ${pinned ? 'ld-switch--pin' : ''}`} role="tablist" aria-label="Для кого страница">
      {SIDES.map(([id, l]) => <button key={id} role="tab" aria-selected={side === id} onClick={() => setSide(id)}>{l}</button>)}
    </div>
  );
}
const PROTO_MINI = [['Стек', 'ok'], ['Грейд', 'ok'], ['Деньги', 'ok'], ['Формат', 'warn'], ['Мотивация', 'ok']];
function Hero({ go, side, setSide, heroRef }) {
  const h = HERO[side];
  return (
    <section className={`ld-band ld-band--ink ld-hero ld-hero--${side}`} ref={heroRef}>
      <div className="ld-hero__copy">
        <Switch side={side} setSide={setSide} />
        <h1 className="r-hero">{h.h}<span className="ld-hero__sub">{h.sub}</span></h1>
        <div className="acts">
          <button className="r-btn r-btn--main r-btn--lg" onClick={() => go(h.go[0])}>{h.go[1]}</button>
          <button className="r-btn r-btn--lg ld-btn-ghost" onClick={() => setSide(side === 'emp' ? 'cand' : 'emp')}>{h.other}</button>
        </div>
        <dl className="ld-facts-row">{h.facts.map(([t, d]) => <div key={t}><dt className="r-num">{t}</dt><dd>{d}</dd></div>)}</dl>
      </div>
      <div className="ld-hero__media">
        <img className="ld-photo" src={h.photo} alt="" width="1600" height="1067" fetchPriority="high" />
        {side === 'emp' ? (<>
          <div className="ld-float ld-float--inv ld-float--proto" aria-hidden="true">
            <div className="ld-float__top"><span className="ld-float__logo" dangerouslySetInnerHTML={{ __html: logo('transkod') || '' }} /><div><b>Протокол агента</b><span>Кандидат №&nbsp;1042 · Бэкенд, средний</span></div></div>
            <ul className="ld-proto">{PROTO_MINI.map(([k, st]) => <li key={k} className={`is-${st}`}><i />{k}<span>{st === 'ok' ? 'Совпадает' : 'Оговорка'}</span></li>)}</ul>
          </div>
          <div className="ld-float ld-float--mark" aria-hidden="true"><Mark src="test" /><span>Грейд подтверждён тестом</span></div>
        </>) : (<>
          <div className="ld-float ld-float--inv" aria-hidden="true">
            <div className="ld-float__top"><span className="ld-float__logo" dangerouslySetInnerHTML={{ __html: logo('transkod') || '' }} /><div><b>ТрансКод</b><span>Приглашение · Бэкенд, средний</span></div></div>
            <div className="ld-fork"><span>Вилка зарплаты</span><b className="r-num">230–280&nbsp;тыс.&nbsp;₽</b></div>
            <div className="ld-fork__bar"><i /></div>
            <div className="ld-float__acts"><span className="ld-pill ld-pill--main">Принять</span><span className="ld-pill">Отказать с&nbsp;причиной</span></div>
          </div>
          <div className="ld-float ld-float--mark" aria-hidden="true"><span className="ld-float__ok"><Icon name="ok" size={16} /></span><span>Агент ответил за&nbsp;вас по&nbsp;пяти критериям</span></div>
        </>)}
      </div>
    </section>
  );
}

const DISC = [['disc-product', 'Продуктовое программирование'], ['disc-algo', 'Алгоритмическое программирование'], ['disc-sec', 'Информационная безопасность'], ['disc-robo', 'Робототехника'], ['disc-uav', 'Беспилотные системы']];
function FspBand() {
  return (
    <section className="ld-band ld-fsp" id="fsp">
      <img className="ld-fsp__bg" src={rzContest} alt="" loading="lazy" width="1600" height="1067" />
      <div className="ld-fsp__in">
        <p className="r-micro">Федерация спортивного программирования</p>
        <h2 className="r-h1">Призы соревнований&nbsp;— в&nbsp;профиле, с&nbsp;меткой реестра</h2>
        <p>Победы и&nbsp;призовые места подтягиваются по&nbsp;ФСП&nbsp;ID и&nbsp;поднимают кандидата внутри категории. Все дисциплины равны: приз по&nbsp;направлению, близкому к&nbsp;специализации, весит полностью, по&nbsp;остальным&nbsp;— 0,8.</p>
        <ul className="ld-disc">
          {DISC.map(([k, name]) => <li key={k}><span className="ld-disc__ic" aria-hidden="true" dangerouslySetInnerHTML={{ __html: DISC_SVG[`./assets/landing/disc/${k}.svg`] || '' }} />{name}</li>)}
        </ul>
      </div>
    </section>
  );
}

const REVIEWS = [
  { face: rzFaceC1, name: 'Алина Морозова', role: 'Бэкенд-разработчица · Средний', side: 'Кандидат', text: 'Я больше не рассылаю резюме. Прошла тест, и приглашение из «ТрансКода» пришло сразу с вилкой зарплаты, без вопроса «сколько хотите».', mark: 'test' },
  { face: faceE1, name: 'Дмитрий Козлов', role: 'Технический директор, ТрансКод', side: 'Работодатель', text: 'Открываем категорию «бэкенд, средний» и сразу видим, у кого грейд проверен тестом. Скрининг-звонок теперь нужен не каждому.' },
  { face: rzFaceC2, name: 'Никита Смирнов', role: 'Фронтенд-разработчик · Младший', side: 'Кандидат', text: 'Призовое место на соревновании ФСП стоит в профиле с меткой реестра. В резюме это была строчка, которой никто не верил.', mark: 'fsp' },
  { face: faceE2, name: 'Елена Волкова', role: 'Руководитель найма, Ритм-Платёж', side: 'Работодатель', text: 'Строка «почему здесь» снимает спор с нанимающим менеджером: видно, что решил тест, а что кандидат написал о себе сам.' },
  { face: rzFaceC3, name: 'Егор Лебедев', role: 'Аналитик данных · Средний', side: 'Кандидат', text: 'Почту и телефон я открываю сам, когда принимаю приглашение. До этого компании пишут мне только через сервис.' },
  { face: faceE3, name: 'Ксения Зайцева', role: 'Тимлид, Лента данных', side: 'Работодатель', text: 'Агенты заранее сверяют формат и деньги. На первую встречу приходят люди, с которыми мы уже совпали по вилке зарплаты.' },
];
function Reviews({ side }) {
  const list = REVIEWS.filter((r) => r.side === (side === 'emp' ? 'Работодатель' : 'Кандидат'));
  return (
    <Reveal className="ld-sec ld-reviews" id="otzyvy">
      <div className="ld-copy"><p className="r-micro">Отзывы</p><h2 className="r-h1">{side === 'emp' ? 'Что говорят нанимающие' : 'Что говорят кандидаты'}</h2></div>
      <div className="ld-rev">
        {list.map((r, i) => (
          <figure key={r.name} className={`ld-rev__card ${r.side === 'Работодатель' ? 'is-emp' : ''}`} style={{ '--i': i }}>
            <Icon name="quote" size={22} />
            <blockquote>{ty(r.text)}</blockquote>
            <figcaption>
              <img src={r.face} alt="" width="56" height="56" loading="lazy" />
              <div><b>{r.name}</b><span>{ty(r.role)}</span></div>
              {r.mark && <Mark src={r.mark} />}
            </figcaption>
          </figure>
        ))}
      </div>
    </Reveal>
  );
}

const FINAL = {
  emp: { h: 'Опишите, кого ищете', go: ['emp', 'Найти людей'], other: 'Я ищу работу', photo: photoMeet },
  cand: { h: 'Первое приглашение начинается с\u00a0теста', go: ['cand', 'Пройти тест'], other: 'Я нанимаю', photo: rzFinal },
};
function Final({ go, side, setSide }) {
  const f = FINAL[side];
  return (
    <section className="ld-band ld-band--blue ld-final">
      <div className="ld-final__copy">
        <h2 className="r-h1">{f.h}</h2>
        {f.p && <p>{f.p}</p>}
        <div className="acts">
          <button className="r-btn r-btn--lg ld-btn-paper" onClick={() => go(f.go[0])}>{f.go[1]}</button>
          <button className="r-btn r-btn--lg ld-btn-ghost" onClick={() => setSide(side === 'emp' ? 'cand' : 'emp')}>{f.other}</button>
        </div>
      </div>
      <img className="ld-photo ld-final__photo" src={f.photo} alt="" loading="lazy" width="1600" height="1067" />
    </section>
  );
}

/* Два лендинга под одним адресом: #business — компаниям (вид ФСП, по умолчанию),
   #candidates — кандидатам (вид «Разряд»). Переключатель — на первом экране;
   когда первый экран уходит, он закрепляется внизу. */
const HASH = { emp: '#business', cand: '#candidates' };
export default function Landing({ go }) {
  const { state, dispatch } = useStore();
  const side = state.ui.lside === 'cand' ? 'cand' : 'emp';
  const heroRef = useRef(null);
  const [pin, setPin] = useState(false);
  useEffect(() => {
    const el = heroRef.current; if (!el || !('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver(([e]) => setPin(!e.isIntersecting), { rootMargin: '-80px 0px 0px 0px' });
    io.observe(el); return () => io.disconnect();
  }, [side]); // key={side} пересоздаёт первый экран — наблюдатель ставим заново
  useEffect(() => { if (location.hash !== HASH[side]) history.replaceState(null, '', HASH[side]); }, [side]);
  const setSide = (s2) => {
    dispatch({ type: 'ui', patch: { lside: s2 } });
    window.scrollTo({ top: 0, behavior: 'auto' });
  };
  const emp = side === 'emp';
  return (
    <div className={`ld ld--${side}`} key={side}>
      <Hero go={go} side={side} setSide={setSide} heroRef={heroRef} />
      <Logos side={side} />
      {emp ? (<>
        <Agents side={side} />
        <Paths go={go} side={side} />
        <Compare side={side} />
        <Trust side={side} />
        <Reviews side={side} />
        <Move go={go} side={side} />
      </>) : (<>
        <Paths go={go} side={side} />
        <TestDemo go={go} />
        <Provenance />
        <FspBand />
        <Agents side={side} />
        <Compare side={side} />
        <Reviews side={side} />
        <Move go={go} side={side} />
        <Trust side={side} />
      </>)}
      <Faq side={side} />
      <Final go={go} side={side} setSide={setSide} />
      {pin && <Switch side={side} setSide={setSide} pinned />}
    </div>
  );
}
