import { writable } from 'svelte/store';

// Basic user shape; extend as needed
export interface User {
  id?: string;
  name?: string;
  email?: string;
  role?: string;
  profile_image_url?: string | null;
}

// Guest user interface
export interface GuestUser {
  id: 'guest';
  name: 'Guest';
  email: 'guest@example.com';
  role: 'guest';
}

// Auth state and current user
export const isAuthenticated = writable<boolean>(false);
export const user = writable<User | null>(null);
export const isGuest = writable<boolean>(false);

// Optional: token store (not required by current code)
export const token = writable<string | null>(null);

// Guest user instance
export const guestUser: GuestUser = {
  id: 'guest',
  name: 'Guest',
  email: 'guest@example.com',
  role: 'guest'
};

// Helper functions
export function setGuestMode() {
  isAuthenticated.set(true);
  isGuest.set(true);
  user.set(guestUser);
  token.set(null);
}

export function clearAuth() {
  isAuthenticated.set(false);
  isGuest.set(false);
  user.set(null);
  token.set(null);
  localStorage.removeItem('token');
}

