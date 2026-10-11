/* Клиент API. Вход один на человека: у него до двух профилей — кандидата
   и компании, переключение в шапке. Слоты cand и emp оставлены ради старых
   вызовов и всегда равны общему токену me. */
const BASE = import.meta.env.VITE_API || '/api';
const KEY = 'razryad-tokens';

const save = (t) => { try { localStorage.setItem(KEY, JSON.stringify(t)); } catch { /* приватное окно */ } };
export const tokens = (() => {
  let t = {}; try { t = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { /* приватное окно */ }
  // Старое хранилище держало два разных входа; общим становится вход компании.
  const me = t.me || t.emp || t.cand;
  return me ? { me, cand: me, emp: me } : {};
})();
export function setToken(_role, t) {
  ['me', 'cand', 'emp'].forEach((k) => { if (t) tokens[k] = t; else delete tokens[k]; });
  save(t ? { me: t } : {});
}

export class ApiError extends Error { constructor(status, detail) { super(detail || `Ошибка ${status}`); this.status = status; } }

export async function req(role, method, path, body, { form } = {}) {
  const headers = {};
  if (role && tokens[role]) headers.Authorization = `Bearer ${tokens[role]}`;
  if (body && !form) headers['Content-Type'] = 'application/json';
  const r = await fetch(BASE + path, { method, headers, body: form ? body : body ? JSON.stringify(body) : undefined });
  if (r.status === 204) return null;
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    if (r.status === 401 && role) setToken(role, null);
    throw new ApiError(r.status, typeof data?.detail === 'string' ? data.detail : Array.isArray(data?.detail) ? data.detail.map((d) => d.msg).join('; ') : null);
  }
  return data;
}

export const get = (role, path) => req(role, 'GET', path);
export const post = (role, path, body) => req(role, 'POST', path, body);
export const patch = (role, path, body) => req(role, 'PATCH', path, body);
export const del = (role, path) => req(role, 'DELETE', path);
export const qs = (o) => { const p = new URLSearchParams(); Object.entries(o).forEach(([k, v]) => { if (v != null && v !== false && v !== '') p.set(k, v); }); const s = p.toString(); return s ? `?${s}` : ''; };
