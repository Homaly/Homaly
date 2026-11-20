import type { ReactNode } from 'react';
import { useRealtimeLigado } from '../context/RealtimeContext';
import Topbar from './Topbar';

type LayoutProps = {
  /** Sem título, a barra de topo fica só com a seta (ver Topbar). */
  title?: string;
  showBack?: boolean;
  children: ReactNode;
};

/** Coluna de telemóvel: topo, conteúdo e espaço para a barra de baixo (que vive em App). */
export default function Layout({ title, showBack, children }: LayoutProps) {
  const ligado = useRealtimeLigado();
  return (
    <div className="mx-auto max-w-md min-h-dvh flex flex-col">
      <Topbar title={title} showBack={showBack} />
      {!ligado && (
        <div role="status" className="px-4 py-2 text-xs font-medium text-center bg-accent-orange/15 text-accent-orange">
          Sem ligação em tempo real. A tentar novamente…
        </div>
      )}
      {/* Coluna flex: deixa a Conversa encostar as mensagens à caixa de texto, em baixo. */}
      <main className="flex flex-1 flex-col px-5 pt-2 pb-24">{children}</main>
    </div>
  );
}
