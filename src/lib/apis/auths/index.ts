import { apiFetch } from '../client';

export interface RegisterBody {
  name: string;
  email: string;
  password: string;
}

export interface LoginBody {
  email: string;
  password: string;
}

export async function register(body: RegisterBody) {
  return apiFetch('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }, false);
}

export async function login(body: LoginBody): Promise<{ access_token: string; token_type: string }> {
  return apiFetch('/api/auth/login', { method: 'POST', body: JSON.stringify(body) }, false);
}

export async function me() {
  return apiFetch('/api/auth/me');
}

export interface UpdateProfileBody {
  name?: string | null;
  profile_image_url?: string | null;
  bio?: string | null;
}

export async function updateProfile(body: UpdateProfileBody) {
  return apiFetch('/api/auth/me', { method: 'PUT', body: JSON.stringify(body) });
}
