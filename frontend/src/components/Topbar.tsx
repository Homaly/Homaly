import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { cn } from '../lib/cn';
import Icone, { type NomeIcone } from './Icone';

type TopbarProps = {
  title: string;
  /** Mostra a seta de voltar atrás (ecrãs sem separador, como o detalhe da anomalia). */
  showBack?: boolean;
};

/** Botão de ícone com o círculo de contorno da app Connected Home: 40 px de desenho, 48 px de toque. */
function BotaoCirculo({
  icone,
  label,
  onClick,
  animar,
  className,
}: {
  icone: NomeIcone;
  label: string;
  onClick: () => void;
  /** Muda a cada clique para repetir a animação do ícone; 0 = sem animação. */
  animar?: number;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={cn('group flex size-12 shrink-0 items-center justify-center', className)}
    >
      <span className="flex size-10 items-center justify-center overflow-hidden rounded-full border-[1.75px] border-on-surface text-on-surface transition-colors group-hover:bg-surface-tonal">
        <Icone key={animar} nome={icone} className={cn('size-5', animar ? 'animate-icon-flip-in' : '')} />
      </span>
    </button>
  );
}

export default function Topbar({ title, showBack = false }: TopbarProps) {
  const navigate = useNavigate();
  const [theme, setTheme] = useTheme();
  const isDark =
    theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  /** Conta as trocas de tema neste ecrã: a animação só corre depois de uma troca, não ao mudar de ecrã. */
  const [trocas, setTrocas] = useState(0);

  return (
    <header className="sticky top-0 z-40 flex h-18 shrink-0 items-center justify-between gap-2 bg-surface/95 px-5 backdrop-blur-md">
      <div className="flex min-w-0 items-center gap-1">
        {showBack && (
          <BotaoCirculo icone="arrow_back" label="Voltar" onClick={() => navigate(-1)} className="-ml-1" />
        )}
        {/* Título grande nos separadores, como na app; mais pequeno no detalhe, onde o título é o da anomalia. */}
        <h1 className={cn('truncate', showBack ? 'text-lg font-semibold' : 'text-2xl font-bold')}>{title}</h1>
      </div>
      <BotaoCirculo
        icone={isDark ? 'light_mode' : 'dark_mode'}
        label={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
        onClick={() => {
          setTheme(isDark ? 'light' : 'dark');
          setTrocas(n => n + 1);
        }}
        animar={trocas}
        className="-mr-1"
      />
    </header>
  );
}
