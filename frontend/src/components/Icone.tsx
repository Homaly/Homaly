import { cn } from '../lib/cn';

type IconeProps = {
  /** Nome do ícone Material Symbols, ex.: "home". */
  nome: string;
  preenchido?: boolean;
  className?: string;
};

/**
 * Ícone decorativo: o leitor de ecrã não o lê (sem isto, lia "home", "shield"...).
 * Quando o ícone é a única informação, pôr texto ao lado em `sr-only`.
 *
 * A fonte só traz os ícones listados em `icon_names` no index.html. Para usar um novo,
 * junte-o a essa lista (por ordem alfabética), senão aparece o nome em texto.
 */
export default function Icone({ nome, preenchido, className }: IconeProps) {
  return (
    <span
      aria-hidden="true"
      className={cn('material-symbols-outlined select-none', className)}
      style={preenchido ? { fontVariationSettings: "'FILL' 1" } : undefined}
    >
      {nome}
    </span>
  );
}
