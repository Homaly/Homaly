import type { ComponentProps } from 'react';
import { cn } from '../lib/cn';

/**
 * Campo de texto: 48 px de altura, cantos de 12 px, letra de 16 px (o iOS não faz zoom).
 * A caixa da conversa passa `rounded-full`, a condizer com os botões em pílula, e um `ref` para lhe dar o foco.
 */
export default function Campo({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'min-h-12 w-full rounded-xl border border-field bg-surface-container px-4 py-2.5 text-base text-on-surface focus:border-primary-ink',
        className
      )}
      {...props}
    />
  );
}
