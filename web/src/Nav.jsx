import { useEffect, useRef, useState } from 'react';
import './nav.css';

/* Шапка. На главной — навигация по её разделам; в кабинетах — переключение
   кабинетов. Вид, тема и технический раздел — в меню «…». */
const SECTIONS = {
  emp: [['agenty', 'Агенты'], ['kak', 'Как устроено'], ['ekonomiya', 'Скрининг'], ['yazyk', 'Два языка'], ['zakon', 'Данные'], ['otzyvy', 'Отзывы'], ['voprosy', 'Вопросы']],
  cand: [['kak', 'Как устроено'], ['test', 'Тест'], ['metki', 'Метки'], ['fsp', 'ФСП'], ['agent', 'Агент'], ['otzyvy', 'Отзывы'], ['voprosy', 'Вопросы']],
};

// Прыжок по якорю — не жест чтения: шапка на время прокрутки не прячется.
function jumpTo(id) {
  const el = document.getElementById(id); if (!el) return;
  const root = document.documentElement;
  root.dataset.jump = '1';
  // Флаг снимается, когда прокрутка затихла: последние её события тоже прыжок.
  let t = 0;
  const done = () => { delete root.dataset.jump; window.removeEventListener('scroll', tick); clearTimeout(cap); };
  const tick = () => { clearTimeout(t); t = setTimeout(done, 250); };
  const cap = setTimeout(done, 2500);
  window.addEventListener('scroll', tick, { passive: true }); tick();
  el.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
}

// Какой раздел главной сейчас перед глазами.
function useSpy(on, list) {
  const [cur, setCur] = useState(null);
  useEffect(() => {
    if (!on || !('IntersectionObserver' in window)) return;
    const els = list.map(([id]) => document.getElementById(id)).filter(Boolean);
    // Раздел в полосе 35–40 % экрана; вне всех разделов (первый экран) — ни один.
    const seen = new Set();
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => (e.isIntersecting ? seen.add(e.target.id) : seen.delete(e.target.id)));
      setCur(list.map(([id]) => id).filter((id) => seen.has(id)).pop() || null);
    }, { rootMargin: '-35% 0px -60% 0px' });
    els.forEach((el) => io.observe(el));
    return () => { io.disconnect(); setCur(null); };
  }, [on, list]);
  return on ? cur : null;
}

/* Знак — один для обеих версий (участник, 11.10.2026): вариант «Белый просвет»
   в цветах флага — синие блоки #0039A6, белый просвет, красная ножка; на светлом
   просвету нужен графитовый контур. */
function Sign({ line }) {
  return (
    <svg className="nv-sign" viewBox="-2 -2 126 148" aria-hidden="true">
      <path fill="#0039A6" d="M0 0H82V30H40V60H0Z" /><path fill="#0039A6" d="M82 30H122V90H40V60H82Z" />
      <path fill="#FFFFFF" stroke={line ? '#1B1C21' : 'none'} strokeWidth="4" d="M40 30H82V60H40Z" /><path fill="#D52B1E" d="M0 90H40V144H0Z" />
    </svg>
  );
}

const More = () => <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.8" /><circle cx="12" cy="12" r="1.8" /><circle cx="19" cy="12" r="1.8" /></svg>;

function Menu({ role, set, skin, theme, setUi, onBye }) {
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  useEffect(() => {
    if (!open) return;
    const away = (e) => !box.current?.contains(e.target) && setOpen(false);
    const key = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', away); document.addEventListener('keydown', key);
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', key); };
  }, [open]);
  const go = (r) => { setOpen(false); set(r); };
  const inside = role === 'cand' || role === 'emp';
  return (
    <div className="nv-more" ref={box}>
      <button className="nv-icon" aria-label="Ещё" aria-haspopup="menu" aria-expanded={open} title="Вид, тема и технический раздел" onClick={() => setOpen(!open)}><More /></button>
      {open && (
        <div className="nv-menu" role="menu">
          {role !== 'home' && <button role="menuitem" className="nv-item" onClick={() => go('home')}>Главная</button>}
          <button role="menuitem" className="nv-item" aria-current={role === 'how' ? 'page' : undefined} onClick={() => go('how')}>Как это работает<span>Механики и цифры с сервера</span></button>
          <div className="nv-group">
            <p className="nv-cap" title="По стороне: кабинет работодателя — строгий вид ФСП, кабинет кандидата — яркий «Разряд»">Вид</p>
            <div className="nv-seg" role="group" aria-label="Вид">
              {[['auto', 'По стороне'], ['fsp', 'ФСП'], ['razryad', 'Разряд']].map(([id, l]) => <button key={id} aria-pressed={(skin || 'auto') === id} onClick={() => setUi({ skin: id, skinPicked: id !== 'auto' })}>{l}</button>)}
            </div>
          </div>
          <div className="nv-group">
            <p className="nv-cap">Тема</p>
            <div className="nv-seg" role="group" aria-label="Тема">
              {[['auto', 'Как в системе'], ['light', 'Светлая'], ['dark', 'Тёмная']].map(([id, l]) => <button key={id} aria-pressed={(theme || 'auto') === id} onClick={() => setUi({ theme: id })}>{l}</button>)}
            </div>
          </div>
          {inside && <button role="menuitem" className="nv-item nv-item--out" onClick={() => { setOpen(false); onBye(); }}>Выйти…</button>}
        </div>
      )}
    </div>
  );
}

export default function Nav({ barRef, role, side = 'emp', dark = false, set, skin, theme, setUi, onBye }) {
  const list = SECTIONS[side];
  const cur = useSpy(role === 'home', list);
  const inside = role === 'cand' || role === 'emp';
  return (
    <header className={`bar nv ${inside ? 'nv--in' : ''}`} ref={barRef}>
      <div className="bar-in nv-in">
        <button className="r-word logo" onClick={() => set('home')} title="На главную"><Sign line={!dark} />Разряд</button>
        {role === 'home' && (
          <nav className="nv-links" aria-label="Разделы главной">
            {list.map(([id, l]) => <a key={id} href={`#${id}`} className="nv-link" aria-current={cur === id ? 'true' : undefined} onClick={(e) => { e.preventDefault(); jumpTo(id); }}>{l}</a>)}
          </nav>
        )}
        {inside && (
          <nav className="nv-cab" aria-label="Кабинет">
            {[['cand', 'Кандидат'], ['emp', 'Работодатель']].map(([id, l]) => <button key={id} aria-current={role === id ? 'page' : undefined} onClick={() => set(id)}>{l}</button>)}
          </nav>
        )}
        {!inside && role !== 'home' && <span className="nv-spacer" />}
        <div className="nv-ctl">
          {!inside && <button className="r-btn r-btn--main r-btn--sm nv-login" aria-current={role === 'login' ? 'page' : undefined} onClick={() => set('login')}>Войти</button>}
          <Menu role={role} set={set} skin={skin} theme={theme} setUi={setUi} onBye={onBye} />
        </div>
      </div>
    </header>
  );
}
