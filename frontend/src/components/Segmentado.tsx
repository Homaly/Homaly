import { useId } from 'react';
import { cn } from '../lib/cn';

export type OpcaoSegmentado<T extends string | number> = { valor: T; rotulo: string };

/**
 * Escolha de uma opção entre poucas, lado a lado (tema, tempo de espera).
 * Por dentro são botões de rádio: as setas do teclado mudam a escolha e o leitor de ecrã diz qual está.
 * A escolhida tem fundo turquesa claro e letra a negrito, para não depender só da cor.
 */
export default function Segmentado<T extends string | number>({
  rotulo,
  opcoes,
  valor,
  onChange,
  disabled,
}: {
  /** Nome do grupo para o leitor de ecrã; o rótulo à vista fica fora. */
  rotulo: string;
  opcoes: OpcaoSegmentado<T>[];
  valor: T;
  onChange: (valor: T) => void;
  disabled?: boolean;
}) {
  const nome = useId();
  return (
    // 48 px de altura, como os botões e os campos.
    <div
      role="radiogroup"
      aria-label={rotulo}
      className={cn('grid auto-cols-fr grid-flow-col gap-1 rounded-full bg-surface-tonal p-1', disabled && 'opacity-50')}
    >
      {opcoes.map(o => {
        const escolhida = o.valor === valor;
        return (
          <label
            key={String(o.valor)}
            className={cn(
              'flex min-h-10 items-center justify-center rounded-full px-2 text-center text-sm transition-colors',
              'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary-ink',
              escolhida ? 'bg-primary/25 font-semibold text-on-surface' : 'font-medium text-on-surface-variant',
              disabled ? 'cursor-default' : 'cursor-pointer'
            )}
          >
            <input
              type="radio"
              name={nome}
              value={String(o.valor)}
              checked={escolhida}
              disabled={disabled}
              onChange={() => onChange(o.valor)}
              className="sr-only"
            />
            {o.rotulo}
          </label>
        );
      })}
    </div>
  );
}
