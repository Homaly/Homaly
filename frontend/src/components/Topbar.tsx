import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';

type TopbarProps = {
  title: string;
  /** Mostra a seta de voltar atrás (ecrãs sem separador, como o detalhe da anomalia). */
  showBack?: boolean;
};

export default function Topbar({ title, showBack = false }: TopbarProps) {
  const navigate = useNavigate();
  const [theme, setTheme] = useTheme();
  const isDark =
    theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  const [themeKey, setThemeKey] = useState(0);

  return (
    <header className="h-16 border-b border-slate-200 dark:border-primary/10 flex items-center justify-between px-4 bg-background-light/95 dark:bg-background-dark/95 backdrop-blur-md z-40 sticky top-0 shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        {showBack && (
          <button
            onClick={() => navigate(-1)}
            className="flex items-center justify-center size-9 rounded-lg hover:bg-slate-100 dark:hover:bg-primary/10 transition-colors"
            aria-label="Voltar"
          >
            <span className="material-symbols-outlined text-slate-600 dark:text-slate-300">arrow_back</span>
          </button>
        )}
        <h1 className="text-xl font-bold tracking-tight truncate">{title}</h1>
      </div>
      <button
        onClick={() => {
          setTheme(isDark ? 'light' : 'dark');
          setThemeKey(k => k + 1);
        }}
        className="flex items-center justify-center rounded-lg size-10 bg-slate-100 dark:bg-primary/10 text-slate-700 dark:text-primary hover:bg-primary/20 transition-colors overflow-hidden"
        aria-label={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
      >
        <span key={themeKey} className="material-symbols-outlined animate-icon-flip-in">
          {isDark ? 'light_mode' : 'dark_mode'}
        </span>
      </button>
    </header>
  );
}
