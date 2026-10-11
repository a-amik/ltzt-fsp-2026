import { useEffect, useRef, useState } from 'react';
import { Store, useStore } from './store.jsx';
import Candidate from './Candidate.jsx';
import Employer from './Employer.jsx';
import How from './How.jsx';
import Landing from './Landing.jsx';
import Login from './Login.jsx';
import Nav from './Nav.jsx';
import { Modal } from './ui.jsx';
import { navigate, pathOf } from './route.js';

function Shell() {
  const { state: st, dispatch, loadCand, loadEmp } = useStore();
  const state = st.ui;
  const set2 = (patch) => dispatch({ type: 'ui', patch });
  const bar = useRef(null);
  const [bye, setBye] = useState(false);
  // Шапка на телефоне уходит по скроллу вниз и возвращается от движения вверх.
  useEffect(() => {
    let last = window.scrollY, acc = 0;
    const on = () => {
      const y = window.scrollY, d = y - last; last = y;
      const el = bar.current; if (!el) return;
      if (y < 50) { el.classList.remove('is-hidden'); acc = 0; return; }
      if (document.documentElement.dataset.jump) { acc = 0; return; }
      if (Math.abs(d) > 200) return;
      acc = Math.sign(d) === Math.sign(acc) ? acc + d : d;
      if (document.body.style.overflow === 'hidden') el.classList.remove('is-hidden');
      else if (acc > 8) el.classList.add('is-hidden');
      else if (acc < -30) el.classList.remove('is-hidden');
    };
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);
  const role = state.role;
  // Адрес следует за экраном: у входа, онбординга, профиля и вкладок — свои пути.
  useEffect(() => { const p = pathOf(st); if (p) navigate(p); }, [st]);
  // Тема: светлая, тёмная или как в системе; скин: Разряд или ФСП.
  const [sysDark, setSysDark] = useState(() => window.matchMedia?.('(prefers-color-scheme: dark)').matches);
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)'); if (!mq) return;
    const on = (e) => setSysDark(e.matches); mq.addEventListener('change', on); return () => mq.removeEventListener('change', on);
  }, []);
  const dark = state.theme === 'dark' || (state.theme === 'auto' && sysDark);
  // Подача по стороне: кабинет и главная кандидата — яркий «Разряд», всё остальное — строгий вид ФСП. Выбор в меню перебивает.
  const skin = !state.skin || state.skin === 'auto' ? (role === 'cand' || (role === 'home' && state.lside === 'cand') ? 'razryad' : 'fsp') : state.skin;
  useEffect(() => {
    const bg = getComputedStyle(document.querySelector('.app')).getPropertyValue('--r-back').trim();
    document.documentElement.style.background = bg; document.documentElement.style.colorScheme = dark ? 'dark' : 'light';

  }, [dark, skin]);
  // Значок вкладки — по стороне (участник, 11.10.2026): компаниям — белая плитка с триколором,
  // кандидатам — синий знак на жёлтой. Иконка приложения одна — белая (site.webmanifest).
  const cand = role === 'cand' || ((role === 'home' || role === 'login') && state.lside === 'cand');
  useEffect(() => {
    const side = cand ? 'cand' : 'biz';
    document.querySelectorAll('link[rel="icon"]').forEach((l) => { l.href = l.type === 'image/png' ? `./favicon-${side}-32.png` : `./favicon-${side}.svg`; });
  }, [cand]);
  // Переход в кабинет перечитывает его данные: приглашение, отправленное из другой роли, видно сразу.
  const set = (r) => { set2({ role: r, ...(r === 'cand' || r === 'emp' ? { cab: r } : {}) }); window.scrollTo(0, 0); if (r === 'cand') loadCand(); if (r === 'emp') loadEmp(); };
  return (
    <div className="kit app" data-skin={skin} data-kit={dark ? 'night' : undefined}>
      <Nav barRef={bar} role={role} side={state.lside === 'cand' ? 'cand' : 'emp'} set={set} skin={state.skin} theme={state.theme} setUi={set2} onBye={() => setBye(true)} me={st.me} cab={state.cab || 'cand'} />
      <main>
        {role === 'home' && <Landing go={set} />}
        {role === 'login' && <Login />}
        {role === 'cand' && <Candidate />}
        {role === 'emp' && <Employer />}
        {role === 'how' && <How />}
      </main>
      {bye && (
        <Modal title="Выйти из аккаунта?" onClose={() => setBye(false)}>
          <p className="r-mute">Профиль, тесты и приглашения останутся на сервере. Войти снова можно по той же почте.</p>
          <div className="acts">
            <button className="r-btn r-btn--main" onClick={() => { localStorage.removeItem('razryad-tokens'); localStorage.removeItem('razryad-ui-v2'); location.reload(); }}>Выйти</button>
            <button className="r-btn" onClick={() => setBye(false)}>Остаться</button>
          </div>
        </Modal>
      )}
      {state.error && <div className="r-toast r-toast--err" role="alert">{state.error}</div>}
      <footer className="foot r-small r-mute">MVP для спецтрека ФСП, ЛЦТ 2026. <a href="/docs">API</a></footer>
    </div>
  );
}

export default function App() {
  return <Store><Shell /></Store>;
}
