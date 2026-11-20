import { useNavigate } from 'react-router-dom';
import { cn } from '../lib/cn';
import Icone from './Icone';

type TopbarProps = {
  /** Sem título, a barra fica só com a seta: o detalhe da anomalia tem o título no conteúdo. */
  title?: string;
  /** Mostra a seta de voltar atrás (ecrãs sem separador, como o detalhe da anomalia). */
  showBack?: boolean;
};

/**
 * Barra de topo: seta de voltar e título, nada mais.
 * O tema escolhe-se em Definições → Aparência, não aqui.
 */
export default function Topbar({ title, showBack = false }: TopbarProps) {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 flex h-18 shrink-0 items-center gap-1 bg-surface/95 px-5 backdrop-blur-md">
      {showBack && (
        // Círculo de contorno da app Connected Home: 40 px de desenho, 48 px de toque.
        <button
          onClick={() => navigate(-1)}
          aria-label="Voltar"
          className="group -ml-1 flex size-12 shrink-0 items-center justify-center"
        >
          <span className="flex size-10 items-center justify-center rounded-full border-[1.75px] border-on-surface text-on-surface transition-colors group-hover:bg-surface-tonal">
            <Icone nome="arrow_back" className="size-5" />
          </span>
        </button>
      )}
      {/* Título grande nos separadores, como na app; mais pequeno nos ecrãs com seta. */}
      {title && (
        <h1 className={cn('min-w-0 truncate', showBack ? 'text-lg font-semibold' : 'text-2xl font-bold')}>{title}</h1>
      )}
    </header>
  );
}
