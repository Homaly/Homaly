import { useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useParams } from 'react-router-dom';
import { format } from 'date-fns';
import { pt } from 'date-fns/locale';
import Layout from '../components/Layout';
import { ClasseBadge } from '../components/AnomaliaCard';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import Botao from '../components/Botao';
import Icone from '../components/Icone';
import { useAnomalia, useDecidirAcao, useDecidirSilencio, useResponderAnomalia } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import { useReservarFundo } from '../hooks/useReservarFundo';
import type { PropostaSilencio } from '../types/contract';
import { cn } from '../lib/cn';

/** Um toque resolve o aviso; a casa não pede justificações (é ela que repara no que se repete). */
const RESPOSTA = 'Está tudo bem';

/**
 * Ações presas ao fundo, ao alcance do polegar: o detalhe não tem barra de baixo.
 * Por portal no body, fora do ecrã que entra animado (ver Layout); aparece sem deslizar.
 */
function BarraAcoes({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useReservarFundo(ref);
  return createPortal(
    <div ref={ref} className="animate-aparecer fixed inset-x-0 bottom-0 z-30 bg-surface/95 backdrop-blur-md">
      <div className="mx-auto max-w-md space-y-3 px-5 pt-3 pb-[calc(env(safe-area-inset-bottom)+1rem)]">
        {children}
      </div>
    </div>,
    document.body
  );
}

export default function Anomalia() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { data: a, isPending, isError, refetch } = useAnomalia(id);
  const responder = useResponderAnomalia(id);
  const decidir = useDecidirAcao(id);
  const silencio = useDecidirSilencio(id);
  const { showToast } = useToast();
  /** Só depois de responder neste ecrã: mostra o agradecimento e o que acontece a seguir. */
  const [enviado, setEnviado] = useState(false);
  /** A ação proposta foi feita neste ecrã. */
  const [agiu, setAgiu] = useState(false);

  const ocupado = responder.isPending || decidir.isPending || silencio.isPending;

  const enviarResposta = () =>
    responder.mutate(RESPOSTA, {
      onSuccess: () => setEnviado(true),
      onError: () => showToast('Não foi possível enviar a resposta', 'error'),
    });

  const fazerAcao = () =>
    decidir.mutate(true, {
      onSuccess: () => {
        setAgiu(true);
        showToast('Feito', 'success');
      },
      onError: () => showToast('A casa não conseguiu confirmar. Nada foi alterado.', 'error'),
    });

  const enviarSilencio = (aceitar: boolean) =>
    silencio.mutate(aceitar, {
      onError: () => showToast('A casa não conseguiu confirmar. Nada foi alterado.', 'error'),
    });

  return (
    // Sem título na barra: o título é o da anomalia, no conteúdo.
    <Layout showBack>
      {isPending ? (
        <EstadoCarregar />
      ) : isError ? (
        <EstadoErro onRetry={refetch} />
      ) : (
        // Espaço em baixo para o fim do texto não ficar por trás das ações presas ao fundo.
        <article className={cn('space-y-5', (a.estado === 'ativa' || enviado || agiu) && 'pb-16')}>
          <header className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <ClasseBadge classe={a.classe} />
              <span className="text-xs text-muted">
                {format(new Date(a.detetadaEm), "d MMM, HH:mm", { locale: pt })}
              </span>
            </div>
            {/* O título da anomalia é o título do ecrã. */}
            <h1 className="text-2xl font-bold leading-tight">{a.titulo}</h1>
          </header>

          {a.imagemUrl && (
            <img src={a.imagemUrl} alt="Imagem da câmara" className="w-full rounded-2xl" />
          )}

          <p className="leading-relaxed">{a.explicacao}</p>

          {a.estado === 'resolvida' ? (
            <div className="space-y-3">
              <div role="status" className="flex gap-3 rounded-2xl bg-accent-green/10 p-4">
                <Icone
                  nome="check_circle"
                  className={cn('size-7 text-accent-green', enviado && 'animate-check-pop')}
                />
                <div className="min-w-0 space-y-1">
                  <p className="font-semibold">{enviado ? 'Obrigado, fica registado' : 'Resolvida'}</p>
                  {a.resposta && (
                    <p className="text-sm">
                      {a.resposta.texto}
                      <span className="text-muted">
                        {' · '}
                        {format(new Date(a.resposta.em), 'HH:mm', { locale: pt })}
                      </span>
                    </p>
                  )}
                  {/* Como se resolveu (US06): "a porta fechou às 14:12", "Feito: Apagar a luz.".
                      Não se repete quando só diz outra vez a resposta. */}
                  {a.resolucao && !(a.resposta && a.resolucao.texto.includes(a.resposta.texto)) && (
                    <p className="text-sm first-letter:uppercase">
                      {a.resolucao.texto}
                      <span className="text-muted">
                        {' · '}
                        {format(new Date(a.resolucao.em), 'HH:mm', { locale: pt })}
                      </span>
                    </p>
                  )}
                  {/* Com proposta de silêncio, é ela que diz o que acontece a seguir. */}
                  {enviado && !a.propostaSilencio && (
                    <p className="text-sm text-muted">Se voltar a acontecer, a casa avisa outra vez.</p>
                  )}
                </div>
              </div>

              {a.propostaSilencio && (
                <Silencio
                  proposta={a.propostaSilencio}
                  ocupado={ocupado}
                  aConfirmar={silencio.isPending ? silencio.variables : undefined}
                  onDecidir={enviarSilencio}
                />
              )}

              {/* Respondeu agora: o passo seguinte é voltar. Com a proposta de silêncio por
                  decidir, fica o Sim/Não; aberta a partir do Histórico, chega a seta. */}
              {(enviado || agiu) && a.propostaSilencio?.estado !== 'pendente' && (
                <BarraAcoes>
                  <Botao largo onClick={() => navigate('/')}>
                    Voltar ao início
                  </Botao>
                </BarraAcoes>
              )}
            </div>
          ) : (
            <BarraAcoes>
              {/* Dois botões, não três: a ação que a casa propõe (com o nome dela) e "Está tudo
                  bem". Um "Recusar" à parte dizia o mesmo que "Está tudo bem". */}
              {a.acaoProposta && (
                <Botao largo onClick={fazerAcao} disabled={ocupado}>
                  {decidir.isPending ? 'A confirmar…' : a.acaoProposta.descricao}
                </Botao>
              )}

              {/* Uma ação principal por ecrã: com ação proposta, é ela; sem ela, é esta. */}
              <Botao
                variante={a.acaoProposta ? 'contorno' : 'primario'}
                largo
                onClick={enviarResposta}
                disabled={ocupado}
              >
                {responder.isPending ? 'A enviar…' : RESPOSTA}
              </Botao>
            </BarraAcoes>
          )}
        </article>
      )}
    </Layout>
  );
}

/** US02: a casa propõe passar a contar com o que se repete; só se aplica depois do Sim. */
function Silencio({
  proposta,
  ocupado,
  aConfirmar,
  onDecidir,
}: {
  proposta: PropostaSilencio;
  ocupado: boolean;
  /** A escolha que está à espera do backend, se houver. */
  aConfirmar?: boolean;
  onDecidir: (aceitar: boolean) => void;
}) {
  if (proposta.estado === 'pendente') {
    return (
      <section className="space-y-3 rounded-2xl bg-surface-container p-4">
        <p className="font-semibold">{proposta.texto}</p>
        <div className="grid grid-cols-2 gap-2">
          <Botao onClick={() => onDecidir(true)} disabled={ocupado}>
            {aConfirmar === true ? 'A confirmar…' : 'Sim'}
          </Botao>
          <Botao variante="secundario" onClick={() => onDecidir(false)} disabled={ocupado}>
            {aConfirmar === false ? 'A confirmar…' : 'Não'}
          </Botao>
        </div>
      </section>
    );
  }
  return (
    <p role="status" className="text-sm text-on-surface-variant">
      {proposta.estado === 'aceite'
        ? 'Combinado. A casa passa a contar com isso.'
        : 'Combinado. A casa continua a avisar.'}
    </p>
  );
}
