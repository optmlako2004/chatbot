/* Client API pour le backend FastAPI.
   Toutes les fonctions retournent une Promise et lèvent une erreur si non-2xx. */

const API_BASE = (window.VA_CONFIG && window.VA_CONFIG.API_BASE) || 'http://localhost:8000';

function _token() {
  try { return localStorage.getItem('va.token'); } catch { return null; }
}

function _lang() {
  try { return (window.VA_I18N && window.VA_I18N.getLang()) || 'fr'; } catch { return 'fr'; }
}

async function _fetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  const tok = _token();
  if (tok) headers['Authorization'] = `Bearer ${tok}`;
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const detail = (data && data.detail) || res.statusText;
    const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

const api = {
  health: () => _fetch('/health'),

  searchTrajets: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v); });
    return _fetch(`/trajets?${qs.toString()}`);
  },
  getTrajet: (id) => _fetch(`/trajets/${id}`),

  cityImage: (q) => _fetch(`/images?q=${encodeURIComponent(q)}`),

  createBillet: (payload) => _fetch('/billets', { method: 'POST', body: JSON.stringify({ ...payload, lang: _lang() }) }),
  myBillets: () => _fetch('/billets/mine'),
  // Upload d'un PDF de billet pour extraction (multipart/form-data).
  // On NE fixe PAS Content-Type : le navigateur ajoute le boundary lui-même.
  extractBillet: async (file) => {
    const fd = new FormData();
    fd.append('file', file);
    const headers = {};
    const tok = _token();
    if (tok) headers['Authorization'] = `Bearer ${tok}`;
    const res = await fetch(`${API_BASE}/billets/extract`, { method: 'POST', body: fd, headers });
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (!res.ok) {
      const detail = (data && data.detail) || res.statusText;
      const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },
  accessBillet: (numero_billet, identity) =>
    _fetch('/billets/access', {
      method: 'POST',
      body: JSON.stringify({ numero_billet, identity }),
    }),
  annulerBillet: (numero_billet, identity) =>
    _fetch(`/billets/${numero_billet}/annuler`, {
      method: 'POST',
      body: JSON.stringify({ numero_billet, identity }),
    }),

  createReclamation: (payload) => _fetch('/reclamations', { method: 'POST', body: JSON.stringify(payload) }),
  suiviReclamation: (numero_suivi) => _fetch(`/reclamations/${numero_suivi}`),

  chatStart: (session_token = null) =>
    _fetch('/chat/start', { method: 'POST', body: JSON.stringify({ session_token, lang: _lang() }) }),
  chatMessage: (session_token, message) =>
    _fetch('/chat/message', { method: 'POST', body: JSON.stringify({ session_token, message, lang: _lang() }) }),
  chatHistory: (session_token) => _fetch(`/chat/${session_token}/history`),
  chatSessions: () => _fetch('/chat/sessions'),
  deleteSession: (session_token) => _fetch(`/chat/sessions/${session_token}`, { method: 'DELETE' }),
  endSession: (session_token, rating, feedback) =>
    _fetch(`/chat/sessions/${session_token}/end`, {
      method: 'POST',
      body: JSON.stringify({ rating, feedback: feedback || '' }),
    }),

  signup: (payload) => _fetch('/auth/signup', { method: 'POST', body: JSON.stringify(payload) }),
  login: (email, password) => _fetch('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  googleAuth: (googlePayload) => _fetch('/auth/google', { method: 'POST', body: JSON.stringify(googlePayload) }),
  me: () => _fetch('/auth/me'),
};

window.VA_API = api;
