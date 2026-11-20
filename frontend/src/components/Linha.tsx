import type { ReactNode } from 'react';
import Icone, { type NomeIcone } from './Icone';

/**
 * Linha de lista, como nas definições do telemóvel: ícone num círculo, título, uma linha de apoio
 * e, à direita, uma seta ou uma ação curta. Só arruma o conteúdo: quem a usa decide se é um link,
 * um botão ou texto. Feita de `span`, para poder ir dentro de um `button`.
 */
export default function Linha({
  icone,
  titulo,
  descricao,
  fim,
}: {
  icone?: NomeIcone;
  titulo: ReactNode;
  descricao?: ReactNode;
  /** À direita: `<Seta />`, uma ação ("Conectar") ou nada. */
  fim?: ReactNode;
}) {
  return (
    <span className="flex min-h-14 w-full items-center gap-3 py-3 text-left">
      {icone && (
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-tonal text-on-surface">
          <Icone nome={icone} className="size-5" />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{titulo}</span>
        {descricao && <span className="block text-sm text-muted">{descricao}</span>}
      </span>
      {fim}
    </span>
  );
}

/** A seta de "abre outro ecrã". */
export function Seta() {
  return <Icone nome="chevron_right" className="size-5 text-muted" />;
}
