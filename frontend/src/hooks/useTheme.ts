import { useEffect, useState } from 'react';

export type Theme = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'homaly-theme';

/** Cor da barra de estado do telemóvel: igual ao fundo do ecrã (--color-surface) de cada tema. */
const COR_BARRA = { claro: '#f5f8f8', escuro: '#0f1e23' };

function applyTheme(theme: Theme) {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const useDark = theme === 'dark' || (theme === 'system' && prefersDark);
  document.documentElement.classList.toggle('dark', useDark);
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', useDark ? COR_BARRA.escuro : COR_BARRA.claro);
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setThemeState] = useState<Theme>(
    () => (localStorage.getItem(STORAGE_KEY) as Theme) ?? 'system'
  );

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  // Keep in sync when system preference changes (only matters in 'system' mode)
  useEffect(() => {
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => applyTheme('system');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  return [theme, setThemeState];
}
