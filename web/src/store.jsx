/* Состояние двух кабинетов. Всё содержательное приходит с сервера; здесь
   только кэш ответов, вкладки, тема и скин. Действие = запрос + перезагрузка
   нужного куска. */
import { createContext, useCallback, useContext, useEffect, useMemo, useReducer } from 'react';
import { get, patch, post, tokens } from './api.js';

const UI_KEY = 'razryad-ui-v2';
const initialUi = { role: 'cand', skin: 'razryad', theme: 'auto', candTab: 'invites', empTab: 'search', needId: null, filters: { near: false, fsp_only: false, work_format: null, must_stack: false }, view: 'mass', shortlist: [], error: null };
const loadUi = () => { try { return { ...initialUi, ...(JSON.parse(localStorage.getItem(UI_KEY)) || {}), error: null }; } catch { return initialUi; } };

function reducer(s, a) {
  switch (a.type) {
    case 'ui': return { ...s, ui: { ...s.ui, ...a.patch } };
    case 'cand': return { ...s, cand: { ...s.cand, ...a.patch } };
    case 'emp': return { ...s, emp: { ...s.emp, ...a.patch } };
    case 'error': return { ...s, ui: { ...s.ui, error: a.text } };
    default: return s;
  }
}

const Ctx = createContext(null);

export function Store({ children }) {
  const [state, dispatch] = useReducer(reducer, null, () => ({ ui: loadUi(), cand: { authed: !!tokens.cand, profile: null }, emp: { authed: !!tokens.emp, company: null } }));
  useEffect(() => { try { const { error, ...rest } = state.ui; localStorage.setItem(UI_KEY, JSON.stringify(rest)); } catch { /* приватное окно */ } }, [state.ui]);

  const fail = useCallback((e) => { dispatch({ type: 'error', text: e.message }); setTimeout(() => dispatch({ type: 'error', text: null }), 4000); }, []);

  // ── Кандидат ────────────────────────────────────────────────────
  const loadCand = useCallback(async () => {
    if (!tokens.cand) { dispatch({ type: 'cand', patch: { authed: false, profile: null } }); return; }
    try {
      const [profile, invites, tests, session, vacancies, responses, tasks] = await Promise.all([
        get('cand', '/candidate/profile'), get('cand', '/candidate/invites'), get('cand', '/test/history'), get('cand', '/test/current'),
        get('cand', '/candidate/vacancies'), get('cand', '/candidate/responses'), get('cand', '/candidate/tasks')]);
      const extra = profile.category ? await Promise.all([get('cand', '/candidate/rank'), get('cand', '/candidate/stats')]) : [null, null];
      dispatch({ type: 'cand', patch: { authed: true, profile, invites, tests, session, vacancies, responses, tasks, rank: extra[0], stats: extra[1] } });
    } catch (e) { if (e.status === 401) dispatch({ type: 'cand', patch: { authed: false, profile: null } }); else fail(e); }
  }, [fail]);

  // ── Работодатель ───────────────────────────────────────────────
  const loadEmp = useCallback(async () => {
    if (!tokens.emp) { dispatch({ type: 'emp', patch: { authed: false, company: null } }); return; }
    try {
      const [company, invites, vacancies, tasks, stats] = await Promise.all([
        get('emp', '/employer/company'), get('emp', '/employer/invites'), get('emp', '/employer/vacancies'), get('emp', '/employer/tasks'), get('emp', '/employer/stats')]);
      dispatch({ type: 'emp', patch: { authed: true, company, invites, vacancies, tasks, stats } });
    } catch (e) { if (e.status === 401) dispatch({ type: 'emp', patch: { authed: false, company: null } }); else fail(e); }
  }, [fail]);

  useEffect(() => { loadCand(); loadEmp(); }, [loadCand, loadEmp]);

  const act = useCallback(async (fn, reload) => {
    try { const r = await fn(); if (reload === 'cand') await loadCand(); if (reload === 'emp') await loadEmp(); return r; } catch (e) { fail(e); throw e; }
  }, [loadCand, loadEmp, fail]);

  const value = useMemo(() => ({ state, dispatch, loadCand, loadEmp, act, get, post, patch }), [state, loadCand, loadEmp, act]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useStore = () => useContext(Ctx);
