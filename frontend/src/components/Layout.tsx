import { useLayoutEffect, type ReactNode } from 'react';
import { useRealtimeLigado } from '../context/RealtimeContext';
import { useTransicaoDeEcra } from '../hooks/useTransicaoDeEcra';
import { cn } from '../lib/cn';
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
  const transicao = useTransicaoDeEcra();
  // Cada ecrã abre no topo: o deslocamento é da janela e passava de um ecrã para o outro (descer na
  // Conversa abria o Histórico no fundo). Antes de pintar, para não se ver o salto; a Conversa desce
  // depois, no seu próprio efeito.
  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, []);
  return (
    // O ecrã inteiro entra animado (ver useTransicaoDeEcra); a barra de baixo fica parada, fora daqui.
    // Nada com `fixed` pode ficar cá dentro: a animação usa transform, que o prenderia a este div.
    // As barras presas ao fundo (ações do aviso, caixa da Conversa) vão por portal para o body.
    <div className={cn('mx-auto flex min-h-dvh max-w-md flex-col', transicao)}>
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
