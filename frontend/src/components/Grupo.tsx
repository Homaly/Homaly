import type { ReactNode } from 'react';

/**
 * Grupo das Definições, como nas definições do telemóvel: título pequeno, o conteúdo num cartão
 * e, por baixo, uma nota curta a explicar para que serve.
 */
export default function Grupo({ titulo, nota, children }: { titulo: string; nota?: ReactNode; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="px-1 text-sm font-semibold text-on-surface-variant">{titulo}</h2>
      <div className="space-y-4 rounded-2xl bg-surface-container p-4">{children}</div>
      {nota && <p className="px-1 text-sm text-muted">{nota}</p>}
    </section>
  );
}
