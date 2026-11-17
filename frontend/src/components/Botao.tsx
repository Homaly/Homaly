import type { ButtonHTMLAttributes } from 'react';
import { cn } from '../lib/cn';

export type VarianteBotao = 'primario' | 'secundario' | 'contorno' | 'texto' | 'perigo';

const VARIANTES: Record<VarianteBotao, string> = {
  /** A ação principal do ecrã; no máximo um por ecrã ou por bloco. */
  primario: 'bg-primary text-on-primary',
  /** Alternativa ao lado do primário (ex.: Recusar). */
  secundario: 'bg-surface-tonal text-on-surface',
  /** Ação secundária isolada (ex.: "Está tudo bem" quando há uma ação proposta). */
  contorno: 'border border-field text-on-surface',
  texto: 'text-on-surface-variant',
  perigo: 'text-danger',
};

type BotaoProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: VarianteBotao;
  /** Ocupa a largura toda. */
  largo?: boolean;
};

/** Botão com 48 px de altura mínima (alvo de toque) e cantos de 12 px. */
export default function Botao({ variante = 'primario', largo, className, type = 'button', ...props }: BotaoProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 font-semibold transition-transform disabled:opacity-50 motion-safe:enabled:active:scale-[0.98]',
        VARIANTES[variante],
        largo && 'w-full',
        className
      )}
      {...props}
    />
  );
}
