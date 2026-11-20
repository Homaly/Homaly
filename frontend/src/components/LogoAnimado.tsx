import type { ReactNode } from 'react';
import { cn } from '../lib/cn';

/**
 * O logótipo da Homaly (casa e linha de eletrocardiograma), como no ecrã de arranque. A linha volta
 * a desenhar-se sempre que `batida` muda (a cada passo das boas-vindas); `salta` faz a casa saltar
 * no fim. Decorativo: o texto está no balão ao lado.
 */
export default function LogoAnimado({ batida, salta, className }: { batida: number; salta?: boolean; className?: string }) {
  return (
    <svg
      viewBox="150 147 320 260"
      aria-hidden
      className={cn('overflow-visible', salta && 'logo-salta', className)}
      fill="none"
      stroke="currentColor"
      strokeWidth={26}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M200 268 L316 162 L372 213 V180 H396 V235 L432 268" />
      <path d="M231 315 V392 H400 V315" />
      <path
        key={batida}
        className="logo-linha"
        pathLength={1}
        d="M165 315 H258 L270 284 L292 355 L320 240 L343 342 L355 315 H455"
      />
    </svg>
  );
}

/** Balão de fala com o bico a apontar para o logótipo: à esquerda dele ou por baixo. */
export function Balao({ bico = 'esquerda', children }: { bico?: 'esquerda' | 'baixo'; children: ReactNode }) {
  return (
    <div className="relative flex-1 rounded-2xl border-2 border-outline-variant bg-surface-container px-4 py-3 font-semibold leading-snug">
      <span
        aria-hidden
        className={cn(
          'absolute size-4 rotate-45 bg-surface-container border-outline-variant',
          bico === 'esquerda'
            ? 'top-6 -left-[9px] border-b-2 border-l-2'
            : '-bottom-[9px] left-1/2 -translate-x-1/2 border-r-2 border-b-2'
        )}
      />
      <div className="relative">{children}</div>
    </div>
  );
}
