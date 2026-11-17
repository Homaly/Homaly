import { cn } from '../lib/cn';
import Botao from './Botao';
import Icone from './Icone';

export function EstadoCarregar() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="A carregar">
      {[0, 1, 2].map(i => (
        <div key={i} className="h-20 animate-pulse rounded-xl bg-surface-tonal" />
      ))}
    </div>
  );
}

export function EstadoErro({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <Icone nome="cloud_off" className="text-4xl text-danger" />
      <p className="text-sm text-on-surface-variant">Não foi possível falar com a casa.</p>
      <Botao onClick={onRetry}>Tentar de novo</Botao>
    </div>
  );
}

/** `tudoBem` pinta o ícone de verde; só para o "Está tudo normal", porque verde quer dizer que correu bem. */
export function EstadoVazio({ icon, texto, tudoBem }: { icon: string; texto: string; tudoBem?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <Icone nome={icon} className={cn('text-5xl', tudoBem ? 'text-accent-green' : 'text-muted')} />
      <p className="text-base font-medium">{texto}</p>
    </div>
  );
}
