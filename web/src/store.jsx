/* Состояние двух кабинетов. Всё содержательное приходит с сервера; здесь
   только кэш ответов, вкладки, тема и скин. Действие = запрос + перезагрузка
   нужного куска. */
import { createContext, useCallback, useContext, useEffect, useMemo, useReducer } from 'react';
import { get, patch, post, setToken, tokens } from './api.js';
import { current, parse } from './route.js';

const UI_KEY = 'razryad-ui-v2';
const initialUi = { role: 'home', lside: 'emp', skin: 'auto', theme: 'auto', candTab: 'home', empTab: 'search', needId: null, filters: { near: false, fsp_only: false, work_format: null, must_stack: false }, view: 'mass', shortlist: [], error: null };
// Адрес #business или #candidates открывает главную нужной стороны.
// Вид, сохранённый до подачи по стороне, выбором человека не был: без метки skinPicked он снова «по стороне».
// #camera и #interview открывают концепцию теста под камерой в кабинете кандидата.
const CAM_HASH = { '#camera': 'prep', '#interview': 'interview' };
// Без входа концепция открывается на демо-кандидате сервера (seed: demo-candidate-token).
if (CAM_HASH[location.hash] && !tokens.me) setToken('cand', 'demo-candidate-token');
const loadUi = () => { try { const saved = JSON.parse(localStorage.getItem(UI_KEY)) || {}; if (!saved.skinPicked) saved.skin = 'auto'; Object.assign(saved, { candTab: 'home', empTab: 'search', quizBack: false }, parse(current())); const h = { '#business': 'emp', '#candidates': 'cand' }[location.hash]; if (h) { saved.role = 'home'; saved.lside = h; } if (CAM_HASH[location.hash]) { saved.role = 'cand'; saved.cam = CAM_HASH[location.hash]; } return { ...initialUi, ...saved, error: null }; } catch { return initialUi; } };

function reducer(s, a) {
  switch (a.type) {
    case 'ui': return { ...s, ui: { ...s.ui, ...a.patch } };
    case 'cand': return { ...s, cand: { ...s.cand, ...a.patch } };
    case 'emp': return { ...s, emp: { ...s.emp, ...a.patch } };
    case 'me': return { ...s, me: a.me };
    case 'error': return { ...s, ui: { ...s.ui, error: a.text } };
    default: return s;
  }
}

const Ctx = createContext(null);

export function Store({ children }) {
  const [state, dispatch] = useReducer(reducer, null, () => ({ ui: loadUi(), me: null, cand: { authed: !!tokens.me, profile: null }, emp: { authed: !!tokens.me, company: null } }));
  useEffect(() => { try { const { error, ...rest } = state.ui; localStorage.setItem(UI_KEY, JSON.stringify(rest)); } catch { /* приватное окно */ } }, [state.ui]);

  // Ссылка #business / #candidates в уже открытой вкладке тоже ведёт на главную нужной стороны.
  useEffect(() => {
    const on = () => { const h = { '#business': 'emp', '#candidates': 'cand' }[location.hash]; if (h) { dispatch({ type: 'ui', patch: { role: 'home', lside: h } }); window.scrollTo(0, 0); } if (CAM_HASH[location.hash]) { if (!tokens.me) { setToken('cand', 'demo-candidate-token'); location.reload(); return; } dispatch({ type: 'ui', patch: { role: 'cand', cam: CAM_HASH[location.hash] } }); window.scrollTo(0, 0); } };
    // «Назад» и «вперёд» браузера: экран берётся из адреса.
    const pop = () => { if (!CAM_HASH[location.hash]) dispatch({ type: 'ui', patch: { quizBack: false, ...parse(current()) } }); };
    window.addEventListener('hashchange', on); window.addEventListener('popstate', pop);
    return () => { window.removeEventListener('hashchange', on); window.removeEventListener('popstate', pop); };
  }, []);

  const fail = useCallback((e) => { dispatch({ type: 'error', text: e.message }); setTimeout(() => dispatch({ type: 'error', text: null }), 4000); }, []);

  // ── Кандидат ────────────────────────────────────────────────────
  const loadCand = useCallback(async () => {
    if (!tokens.me) { dispatch({ type: 'cand', patch: { authed: false, profile: null, none: false } }); dispatch({ type: 'me', me: null }); return; }
    get('cand', '/auth/me').then((me) => dispatch({ type: 'me', me })).catch(() => {});
    try {
      const [profile, invites, tests, session, vacancies, responses, tasks, refs] = await Promise.all([
        get('cand', '/candidate/profile'), get('cand', '/candidate/invites'), get('cand', '/test/history'), get('cand', '/test/current'),
        get('cand', '/candidate/vacancies'), get('cand', '/candidate/responses'), get('cand', '/candidate/tasks'), get('cand', '/candidate/references').catch(() => null)]);
      const extra = profile.category ? await Promise.all([get('cand', '/candidate/rank'), get('cand', '/candidate/stats')]) : [null, null];
      dispatch({ type: 'cand', patch: { authed: true, none: false, profile, invites, tests, session, vacancies, responses, tasks, refs, rank: extra[0], stats: extra[1] } });
    } catch (e) {
      if (e.status === 401) dispatch({ type: 'cand', patch: { authed: false, profile: null } });
      else if (e.status === 404) dispatch({ type: 'cand', patch: { authed: true, none: true, profile: null } }); // вход есть, профиля кандидата нет
      else fail(e);
    }
  }, [fail]);

  // ── Работодатель ───────────────────────────────────────────────
  const loadEmp = useCallback(async () => {
    if (!tokens.me) { dispatch({ type: 'emp', patch: { authed: false, company: null, none: false } }); return; }
    try {
      const [company, invites, vacancies, tasks, stats] = await Promise.all([
        get('emp', '/employer/company'), get('emp', '/employer/invites'), get('emp', '/employer/vacancies'), get('emp', '/employer/tasks'), get('emp', '/employer/stats')]);
      dispatch({ type: 'emp', patch: { authed: true, none: false, company, invites, vacancies, tasks, stats } });
    } catch (e) {
      if (e.status === 401) dispatch({ type: 'emp', patch: { authed: false, company: null } });
      else if (e.status === 404) dispatch({ type: 'emp', patch: { authed: true, none: true, company: null } }); // вход есть, профиля компании нет
      else fail(e);
    }
  }, [fail]);

  useEffect(() => { loadCand(); loadEmp(); }, [loadCand, loadEmp]);

  const act = useCallback(async (fn, reload) => {
    try { const r = await fn(); if (reload === 'cand' || reload === 'all') await loadCand(); if (reload === 'emp' || reload === 'all') await loadEmp(); return r; } catch (e) { fail(e); throw e; }
  }, [loadCand, loadEmp, fail]);

  const value = useMemo(() => ({ state, dispatch, loadCand, loadEmp, act, get, post, patch }), [state, loadCand, loadEmp, act]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useStore = () => useContext(Ctx);
