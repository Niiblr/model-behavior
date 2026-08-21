/**
 * Theme utilities — light/dark toggle persisted to localStorage.
 * The active theme is applied as [data-theme] on <html>.
 */

const STORAGE_KEY = 'mb-theme';

export function getStoredTheme() {
  return localStorage.getItem(STORAGE_KEY);
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(STORAGE_KEY, theme);
}

/** Resolve the initial theme: saved preference, else OS preference. */
export function initTheme() {
  const saved = getStoredTheme();
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.dataset.theme = theme;
  return theme;
}

export function toggleTheme(current) {
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  return next;
}
