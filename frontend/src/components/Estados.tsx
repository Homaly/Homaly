import { cn } from '../lib/cn';
import Botao from './Botao';
import Icone, { type NomeIcone } from './Icone';

export function EstadoCarregar() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="A carregar">
      {[0, 1, 2].map(i => (
        <div key={i} className="h-20 motion-safe:animate-pulse rounded-2xl bg-surface-container" />
      ))}
    </div>
  );
}

export function EstadoErro({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <span className="flex size-16 items-center justify-center rounded-full bg-danger/10">
        <Icone nome="cloud_off" className="size-8 text-danger" />
      </span>
      <p className="text-xl font-semibold">Não foi possível falar com a casa</p>
      <Botao onClick={onRetry} className="mt-2">
        Tentar de novo
      </Botao>
    </div>
  );
}

/**
 * Estado vazio como na app Connected Home: ícone num círculo, título e, se houver, uma frase.
 * `tudoBem` pinta o ícone de verde; só para o "Está tudo normal", porque verde quer dizer que correu bem.
 */
export function EstadoVazio({
  icon,
  texto,
  descricao,
  tudoBem,
}: {
  icon: NomeIcone;
  texto: string;
  descricao?: string;
  tudoBem?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
      <span
        className={cn(
          'flex size-16 items-center justify-center rounded-full',
          tudoBem ? 'bg-accent-green/15' : 'bg-surface-container'
        )}
      >
        <Icone nome={icon} className={cn('size-8', tudoBem ? 'text-accent-green' : 'text-muted')} />
      </span>
      <p className="text-xl font-semibold">{texto}</p>
      {descricao && <p className="text-on-surface-variant">{descricao}</p>}
    </div>
  );
}
