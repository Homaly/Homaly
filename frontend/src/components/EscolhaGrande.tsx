import { useId } from 'react';
import { cn } from '../lib/cn';

export interface OpcaoGrande<T extends string | number> {
  valor: T;
  rotulo: string;
  nota?: string;
}

interface EscolhaGrandeProps<T extends string | number> {
  rotulo: string;
  opcoes: OpcaoGrande<T>[];
  valor: T;
  onChange: (valor: T) => void;
}

/**
 * Escolha em cartões grandes, um por linha, com degrau por baixo (estilo Duolingo).
 * Por dentro são botões de rádio, como o Segmentado: setas do teclado e leitor de ecrã funcionam.
 * A escolhida tem contorno turquesa, fundo turquesa claro e letra a negrito: não depende só da cor.
 */
export default function EscolhaGrande<T extends string | number>({ rotulo, opcoes, valor, onChange }: EscolhaGrandeProps<T>) {
  const nome = useId();
  return (
    <div role="radiogroup" aria-label={rotulo} className="space-y-3">
      {opcoes.map(o => {
        const escolhida = o.valor === valor;
        return (
          <label
            key={String(o.valor)}
            className={cn(
              'flex min-h-14 cursor-pointer items-center justify-between gap-3 rounded-2xl border-2 border-b-4 px-4 py-3 transition-colors',
              'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary-ink',
              escolhida
                ? 'border-primary-ink bg-primary/15 font-semibold'
                : 'border-outline-variant bg-surface-container font-medium'
            )}
          >
            <input
              type="radio"
              name={nome}
              value={String(o.valor)}
              checked={escolhida}
              onChange={() => onChange(o.valor)}
              className="sr-only"
            />
            <span>{o.rotulo}</span>
            {o.nota && <span className="text-sm font-medium text-muted">{o.nota}</span>}
          </label>
        );
      })}
    </div>
  );
}
