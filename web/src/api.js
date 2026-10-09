/* Клиент API. Токены двух ролей держим отдельно: в демо один человек ходит
   по обоим кабинетам, в жизни это два разных входа. */
const BASE = import.meta.env.VITE_API || '/api';
const KEY = 'razryad-tokens';

export const tokens = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } })();
export function setToken(role, t) { if (t) tokens[role] = t; else delete tokens[role]; try { localStorage.setItem(KEY, JSON.stringify(tokens)); } catch { /* приватное окно */ } }

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
