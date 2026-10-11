import { useEffect, useState } from 'react';
import photoCand from './assets/landing/photo/rz-path.webp';
import photoEmployer from './assets/landing/photo/photo-employer.webp';
import { get, post, setToken } from './api.js';
import { useStore } from './store.jsx';
import { CandEntry } from './Candidate.jsx';
import { EmpEntry } from './Employer.jsx';
import './nav.css';

/* Вход один на обе стороны: готовые аккаунты — кандидаты разных типов
   и компании — входят в один клик, рядом новый кандидат и вход по почте.
   /login — обе стороны; /login/candidate и /login/company — та же сторона
   с теми же аккаунтами и формой входа по почте. Любой вход ведёт
   через онбординг своей стороны. */
const SIDES = [
  { id: 'cand', photo: photoCand, title: 'Кандидату', mail: 'Войти по почте или через ФСП ID' },
  { id: 'emp', photo: photoEmployer, title: 'Компании', mail: 'Войти по почте компании' },
];

export const initials = (s) => (s || '?').replace(/[«»"]/g, '').split(/[\s-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();

export default function Login({ only }) {
  const { act, dispatch, loadCand, loadEmp } = useStore();
  const [list, setList] = useState(null);
  useEffect(() => { get(null, '/auth/personas').then(setList).catch(() => setList([])); }, []);
  const go = (role, patch = {}) => { dispatch({ type: 'ui', patch: { role, cab: role, ...patch } }); window.scrollTo(0, 0); };
  // Вход ведёт через онбординг своей стороны: шаги заполнены данными аккаунта, человек их проходит и подтверждает.
  const onb = (side) => (side === 'emp' ? { onbEmp: 'company', empTab: 'search' } : { onb: 'about', candTab: 'home', quizBack: false });
  const enter = (token, side) => act(async () => { setToken('me', token); }, 'all').then(() => go(side, onb(side)));
  const fresh = () => act(async () => { const r = await post(null, '/auth/personas/fresh'); setToken('me', r.token); }, 'all').then(() => go('cand', onb('cand')));
  const byMail = (side) => { setToken('me', null); Promise.all([loadCand(), loadEmp()]).then(() => go(side)); };
  const sides = only ? SIDES.filter((s) => s.id === only) : SIDES;
  return (
    <div className="page lg">
      <div className="lg-head">
        <h1 className="r-h1">Вход в&nbsp;«Разряд»</h1>
      </div>
      <div className="lg-sides">
        {sides.map((s) => {
          const accs = (list || []).filter((p) => p.side === s.id || p.side === 'both');
          return (
            <section key={s.id} className="lg-side">
              <img src={s.photo} alt="" width="1600" height="1067" />
              <div className="lg-side__body">
                <h2 className="r-h2">{s.title}</h2>
                <div className="lg-accs">
                  {accs.map((p) => (
                    <button key={p.key} className="lg-acc" onClick={() => enter(p.token, s.id)}>
                      <span className={`lg-ava ${s.id === 'emp' && p.side === 'emp' ? 'lg-ava--emp' : ''}`} aria-hidden="true">{initials(p.name)}</span>
                      <span className="lg-acc__txt"><b>{p.name}</b><span>{p.title}</span><span className="lg-acc__hint">{p.hint}</span></span>
                    </button>
                  ))}
                  {s.id === 'cand' && (
                    <button className="lg-acc lg-acc--new" onClick={fresh}>
                      <span className="lg-ava" aria-hidden="true">+</span>
                      <span className="lg-acc__txt"><b>Новый кандидат</b><span>С&nbsp;первого шага: опрос, условия, тест</span></span>
                    </button>
                  )}
                </div>
                {!only && <button className="r-btn r-btn--quiet" onClick={() => byMail(s.id)}>{s.mail}</button>}
              </div>
            </section>
          );
        })}
        {only === 'cand' && <div className="lg-mail"><CandEntry /></div>}
        {only === 'emp' && <div className="lg-mail"><EmpEntry /></div>}
      </div>
    </div>
  );
}
