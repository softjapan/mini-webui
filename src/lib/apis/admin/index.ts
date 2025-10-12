import { apiFetch } from '../client';

// Stats
export interface AdminStats {
  users: number;
  chats: number;
  messages: number;
}

export function getStats(): Promise<AdminStats> {
  return apiFetch('/api/admin/stats');
}

// Users
export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: number;
  updated_at: number;
}

export interface UserListResp {
  items: AdminUser[];
  total: number;
}

export function listUsers(params: { q?: string; offset?: number; limit?: number } = {}): Promise<UserListResp> {
  const q = new URLSearchParams();
  if (params.q) q.set('q', params.q);
  if (params.offset != null) q.set('offset', String(params.offset));
  if (params.limit != null) q.set('limit', String(params.limit));
  const qs = q.toString();
  return apiFetch(`/api/admin/users${qs ? `?${qs}` : ''}`);
}

export function createUser(body: { name: string; email: string; password: string; role?: string }): Promise<AdminUser> {
  return apiFetch('/api/admin/users', { method: 'POST', body: JSON.stringify(body) });
}

export function getUser(id: string): Promise<AdminUser> {
  return apiFetch(`/api/admin/users/${id}`);
}

export function updateUser(id: string, body: Partial<Pick<AdminUser, 'name'|'email'|'role'|'is_active'>>): Promise<AdminUser> {
  return apiFetch(`/api/admin/users/${id}`, { method: 'PUT', body: JSON.stringify(body) });
}

export function activateUser(id: string): Promise<AdminUser> {
  return apiFetch(`/api/admin/users/${id}/activate`, { method: 'POST' });
}

export function deactivateUser(id: string): Promise<AdminUser> {
  return apiFetch(`/api/admin/users/${id}/deactivate`, { method: 'POST' });
}

export function deleteUser(id: string, opts: { hard?: boolean } = {}) {
  const q = opts.hard ? '?hard=true' : '';
  return apiFetch(`/api/admin/users/${id}${q}`, { method: 'DELETE' });
}

// Settings
export interface AdminSettings {
  openai_api_key?: string | null;
  openai_api_base?: string | null;
  app_name?: string | null;
  debug?: boolean | null;
}

export function getSettings(): Promise<AdminSettings> {
  return apiFetch('/api/admin/settings');
}

export function updateSettings(body: AdminSettings): Promise<AdminSettings> {
  return apiFetch('/api/admin/settings', { method: 'PUT', body: JSON.stringify(body) });
}

