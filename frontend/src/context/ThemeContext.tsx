import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

/** `system` segue o tema do telemóvel; é o valor por omissão. */
export type Theme = 'system' | 'light' | 'dark';

/** O script em index.html lê a mesma chave antes de a app arrancar, para não piscar. */
const STORAGE_KEY = 'homaly-theme';

/** Cor da barra de estado do telemóvel: igual ao fundo do ecrã (--color-surface) de cada tema. */
const COR_BARRA = { claro: '#f4f5f9', escuro: '#131321' };

function lerTema(): Theme {
  try {
    const guardado = localStorage.getItem(STORAGE_KEY);
    return guardado === 'light' || guardado === 'dark' ? guardado : 'system';
  } catch {
    return 'system';
  }
}

function aplicarTema(theme: Theme) {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const useDark = theme === 'dark' || (theme === 'system' && prefersDark);
  document.documentElement.classList.toggle('dark', useDark);
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', useDark ? COR_BARRA.escuro : COR_BARRA.claro);
}

const ThemeContext = createContext<[Theme, (t: Theme) => void] | null>(null);

/**
 * Um só tema para a app toda, escolhido em Definições → Aparência.
 * Vive na raiz para continuar a seguir o telemóvel em qualquer ecrã, não só nas Definições.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(lerTema);

  useEffect(() => {
    aplicarTema(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // sem localStorage (ex.: janela privada): o tema vale só até fechar a app
    }
  }, [theme]);

  // Em `system`, acompanha o telemóvel quando ele muda de tema com a app aberta.
  useEffect(() => {
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => aplicarTema('system');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  return <ThemeContext.Provider value={[theme, setTheme]}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}
