/* Адреса экранов. У каждого экрана — свой путь: вход, онбординг, профиль
   и его вкладки, компания и её вкладки. Ссылку можно дать, «назад» работает,
   перезагрузка возвращает на тот же экран. На доске макетов прототип лежит
   в папке со статикой (сборка с base ./), там тот же путь идёт после #. */
const HASHMODE = import.meta.env.BASE_URL !== '/';

// Вкладка ↔ часть адреса.
const CAND = { home: '', invites: 'invites', agent: 'agent', refs: 'reviews', view: 'view', stats: 'stats', tasks: 'tasks', grade: 'grade', profile: 'facts', vac: 'vacancies', settings: 'settings' };
const EMP = { search: '', bank: 'bank', tasks: 'tasks', invites: 'invites', stats: 'stats', vac: 'vacancies', company: 'profile', settings: 'settings' };
const inv = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [v, k]));
const CAND_BY = inv(CAND), EMP_BY = inv(EMP);

export function current() {
  if (HASHMODE) return location.hash.startsWith('#/') ? location.hash.slice(1) : '/';
  return location.pathname || '/';
}

// Где человек сейчас — по состоянию кабинетов. null — данные ещё грузятся.
export function pathOf(st) {
  const ui = st.ui, r = ui.role;
  if (r === 'home') return '/';
  if (r === 'login') return '/login';
  if (r === 'how') return '/how';
  if (r === 'cand') {
    const c = st.cand;
    if (!c.authed) return '/login/candidate';
    if (c.none) return '/profile/new';
    const p = c.profile;
    if (!p) return null;
    if (ui.cam) return '/profile/camera';
    const fresh = p.grade == null && !(c.tests || []).length;
    if (c.session && !c.session.finished) return fresh ? '/onboarding/test' : '/profile/test';
    if (ui.onb === 'about' || !p.spec || p.claimed_grade == null || ui.quizBack) return ui.quizBack && !ui.onb ? '/profile/about' : '/onboarding/about';
    if (ui.onb === 'terms' || (!p.wants && fresh)) return '/onboarding/terms';
    if (ui.onb === 'grade') return '/onboarding/grade';
    const s = CAND[ui.candTab] ?? '';
    return '/profile' + (s ? `/${s}` : '');
  }
  if (r === 'emp') {
    const e = st.emp;
    if (!e.authed) return '/login/company';
    if (e.none) return '/company/new';
    if (!e.company) return null;
    if (!e.company.name || ui.onbEmp === 'company') return '/onboarding/company';
    if (!e.company.prefs || ui.onbEmp === 'hiring') return '/onboarding/hiring';
    const s = EMP[ui.empTab] ?? '';
    return '/company' + (s ? `/${s}` : '');
  }
  return null;
}

// Адрес → состояние интерфейса.
export function parse(path) {
  const [a = '', b = ''] = path.split('/').filter(Boolean);
  if (a === 'login') return b === 'candidate' ? { role: 'cand' } : b === 'company' ? { role: 'emp' } : { role: 'login' };
  if (a === 'how') return { role: 'how' };
  if (a === 'profile') return { role: 'cand', candTab: CAND_BY[b] || 'home', onb: null, ...(b === 'about' ? { quizBack: true } : {}) };
  if (a === 'onboarding') return ['company', 'hiring'].includes(b) ? { role: 'emp', onbEmp: b } : { role: 'cand', onb: ['about', 'terms', 'grade'].includes(b) ? b : null };
  if (a === 'company') return { role: 'emp', empTab: EMP_BY[b] || 'search', onbEmp: null };
  return { role: 'home' };
}

// Шаги онбординга и входа сменяют друг друга без записи в историю: «назад» ведёт со всего онбординга, а не на шаг, который уже сохранён.
export function navigate(path) {
  const cur = current();
  if (path === cur) return;
  const flow = (p) => /^\/(onboarding|login)/.test(p);
  const url = HASHMODE ? (path === '/' ? location.pathname + location.search : `#${path}`) : path + (path === '/' ? location.hash : '');
  history[flow(cur) && flow(path) ? 'replaceState' : 'pushState'](null, '', url);
}
