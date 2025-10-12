export const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8080';

export function getToken(): string | null {
  try {
    return localStorage.getItem('token');
  } catch {
    return null;
  }
}

export async function apiFetch(path: string, init: RequestInit = {}, auth: boolean = true) {
  const headers = new Headers(init.headers || {});
  headers.set('Content-Type', 'application/json');
  if (auth) {
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers
  });
  if (!res.ok) {
    let detail: any = undefined;
    try { detail = await res.json(); } catch {}
    throw new Error(detail?.detail || res.statusText);
  }
  const text = await res.text();
  try { return JSON.parse(text); } catch { return text as any; }
}

