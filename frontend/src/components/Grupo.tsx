import type { ReactNode } from 'react';
import { cn } from '../lib/cn';

/**
 * Grupo das Definições, como nas definições do telemóvel: título pequeno, o conteúdo num cartão
 * e, por baixo, uma nota curta a explicar para que serve.
 * `lista`: o cartão leva linhas (`Linha`) separadas por divisórias, sem espaço extra em cima e em baixo.
 */
export default function Grupo({
  titulo,
  nota,
  lista,
  children,
}: {
  titulo?: string;
  nota?: ReactNode;
  lista?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="space-y-2">
      {titulo && <h2 className="px-1 text-sm font-semibold text-on-surface-variant">{titulo}</h2>}
      <div
        className={cn(
          'rounded-2xl bg-surface-container',
          lista ? 'divide-y divide-outline-variant px-4' : 'space-y-4 p-4'
        )}
      >
        {children}
      </div>
      {nota && <p className="px-1 text-sm text-muted">{nota}</p>}
    </section>
  );
}
