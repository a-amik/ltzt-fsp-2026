import { useEffect, useRef, useState } from 'react';
import { Store, useStore } from './store.jsx';
import Candidate from './Candidate.jsx';
import Employer from './Employer.jsx';
import How from './How.jsx';

function Shell() {
  const { state: st, dispatch, loadCand, loadEmp } = useStore();
  const state = st.ui;
  const set2 = (patch) => dispatch({ type: 'ui', patch });
  const bar = useRef(null);
  // Шапка на телефоне уходит по скроллу вниз и возвращается от движения вверх.
  useEffect(() => {
    let last = window.scrollY, acc = 0;
    const on = () => {
      const y = window.scrollY, d = y - last; last = y;
      if (Math.abs(d) > 200) return;
      acc = Math.sign(d) === Math.sign(acc) ? acc + d : d;
      const el = bar.current; if (!el) return;
      if (y < 50 || document.body.style.overflow === 'hidden') el.classList.remove('is-hidden');
      else if (acc > 8) el.classList.add('is-hidden');
      else if (acc < -30) el.classList.remove('is-hidden');
    };
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);
  const role = state.role;
  // Тема: светлая, тёмная или как в системе; скин: Разряд или ФСП.
  const [sysDark, setSysDark] = useState(() => window.matchMedia?.('(prefers-color-scheme: dark)').matches);
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)'); if (!mq) return;
    const on = (e) => setSysDark(e.matches); mq.addEventListener('change', on); return () => mq.removeEventListener('change', on);
  }, []);
  const dark = state.theme === 'dark' || (state.theme === 'auto' && sysDark);
  const skin = state.skin || 'razryad';
  useEffect(() => {
    const bg = getComputedStyle(document.querySelector('.app')).getPropertyValue('--r-back').trim();
    document.documentElement.style.background = bg; document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
  }, [dark, skin]);
  const nextTheme = { auto: 'light', light: 'dark', dark: 'auto' }[state.theme || 'auto'];
  const ICONS = {
    auto: <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="2" /><path d="M10 3a7 7 0 0 1 0 14z" fill="currentColor" /></svg>,
    light: <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><circle cx="10" cy="10" r="4" fill="none" stroke="currentColor" strokeWidth="2" /><path d="M10 1v3M10 16v3M1 10h3M16 10h3M3.6 3.6l2.1 2.1M14.3 14.3l2.1 2.1M3.6 16.4l2.1-2.1M14.3 5.7l2.1-2.1" stroke="currentColor" strokeWidth="2" /></svg>,
    dark: <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M15.5 13.2A7 7 0 0 1 6.8 4.5 7 7 0 1 0 15.5 13.2z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>,
  };
  const themeIcon = ICONS[state.theme || 'auto'];
  const themeName = { auto: 'как в системе', light: 'светлая', dark: 'тёмная' }[state.theme || 'auto'];
  // Переход в кабинет перечитывает его данные: приглашение, отправленное из другой роли, видно сразу.
  const set = (r) => { set2({ role: r }); window.scrollTo(0, 0); if (r === 'cand') loadCand(); if (r === 'emp') loadEmp(); };
  return (
    <div className="kit app" data-skin={skin} data-kit={dark ? 'night' : undefined}>
      <header className="bar" ref={bar}>
        <div className="bar-in">
          <span className="r-word logo"><img src="./sign-master.svg" alt="" />Разряд</span>
          <nav className="roles" aria-label="Роль">
            {[['cand', 'Кандидат'], ['emp', 'Работодатель'], ['how', 'Как это работает']].map(([id, l]) => (
              <button key={id} className="role" aria-current={role === id ? 'page' : undefined} onClick={() => set(id)}>{l}</button>
            ))}
          </nav>
          <div className="bar-ctl">
            <div className="seg" role="group" aria-label="Стиль">
              <button aria-pressed={skin === 'razryad'} onClick={() => set2({ skin: 'razryad' })}>Разряд</button>
              <button aria-pressed={skin === 'fsp'} onClick={() => set2({ skin: 'fsp' })}>ФСП</button>
            </div>
            <button className="theme-btn" title={`Тема: ${themeName}`} aria-label={`Тема: ${themeName}. Переключить`} onClick={() => set2({ theme: nextTheme })}>{themeIcon}</button>
          </div>
          <button className="r-btn r-btn--quiet r-btn--sm reset" onClick={() => { if (confirm('Выйти из обоих кабинетов? Данные останутся на сервере.')) { localStorage.removeItem('razryad-tokens'); localStorage.removeItem('razryad-ui-v2'); location.reload(); } }}>Выйти</button>
        </div>
      </header>
      <main>
        {role === 'cand' && <Candidate />}
        {role === 'emp' && <Employer />}
        {role === 'how' && <How />}
      </main>
      {state.error && <div className="r-toast r-toast--err" role="alert">{state.error}</div>}
      <footer className="foot r-small r-mute">MVP для спецтрека ФСП, ЛЦТ 2026. Кандидаты синтетические. <a href="/docs">API</a></footer>
    </div>
  );
}

export default function App() {
  return <Store><Shell /></Store>;
}
