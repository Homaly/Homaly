import type { InputHTMLAttributes } from 'react';
import { cn } from '../lib/cn';

/**
 * Campo de texto: 48 px de altura, cantos de 12 px, letra de 16 px (o iOS não faz zoom).
 * A caixa da conversa passa `rounded-full` de propósito, a condizer com o botão redondo de enviar.
 */
export default function Campo({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
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
