import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { cn } from '../lib/cn';
import Icone from './Icone';

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
  /** Conta as trocas de tema neste ecrã: a animação só corre depois de uma troca, não ao mudar de ecrã. */
  const [trocas, setTrocas] = useState(0);

  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface/95 px-4 backdrop-blur-md">
      <div className="flex min-w-0 items-center gap-1">
        {showBack && (
          <button
            onClick={() => navigate(-1)}
            className="-ml-3 flex size-12 shrink-0 items-center justify-center rounded-xl text-on-surface-variant transition-colors hover:bg-surface-tonal"
            aria-label="Voltar"
          >
            <Icone nome="arrow_back" />
          </button>
        )}
        <h1 className="truncate text-xl font-bold tracking-tight">{title}</h1>
      </div>
      <button
        onClick={() => {
          setTheme(isDark ? 'light' : 'dark');
          setTrocas(n => n + 1);
        }}
        className="group -mr-1 flex size-12 shrink-0 items-center justify-center"
        aria-label={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
      >
        <span className="flex size-10 items-center justify-center overflow-hidden rounded-lg bg-surface-tonal text-on-surface-variant transition-colors group-hover:bg-primary/20">
          <Icone
            key={trocas}
            nome={isDark ? 'light_mode' : 'dark_mode'}
            className={cn(trocas > 0 && 'animate-icon-flip-in')}
          />
        </span>
      </button>
    </header>
  );
}
