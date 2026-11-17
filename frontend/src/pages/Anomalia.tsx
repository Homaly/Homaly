import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { format } from 'date-fns';
import { pt } from 'date-fns/locale';
import Layout from '../components/Layout';
import { ClasseBadge } from '../components/AnomaliaCard';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import Botao from '../components/Botao';
import Campo from '../components/Campo';
import Icone from '../components/Icone';
import { useAnomalia, useDecidirAcao, useDecidirSilencio, useResponderAnomalia } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import type { PropostaSilencio } from '../types/contract';
import { cn } from '../lib/cn';

const RESPOSTA_SEM_MOTIVO = 'Está tudo bem';

export default function Anomalia() {
  const { id = '' } = useParams();
  const { data: a, isPending, isError, refetch } = useAnomalia(id);
  const responder = useResponderAnomalia(id);
  const decidir = useDecidirAcao(id);
  const silencio = useDecidirSilencio(id);
  const { showToast } = useToast();
  const [texto, setTexto] = useState('');
  const [aExplicar, setAExplicar] = useState(false);
  /** Só depois de responder neste ecrã: mostra o agradecimento e o que acontece a seguir. */
  const [enviado, setEnviado] = useState<{ semMotivo: boolean } | null>(null);

  const ocupado = responder.isPending || decidir.isPending || silencio.isPending;

  const enviarResposta = (t: string) =>
    responder.mutate(t, {
      onSuccess: () => {
        setEnviado({ semMotivo: t === RESPOSTA_SEM_MOTIVO });
        setTexto('');
        setAExplicar(false);
      },
      onError: () => showToast('Não foi possível enviar a resposta', 'error'),
    });

  const enviarDecisao = (aceitar: boolean) =>
    decidir.mutate(aceitar, {
      onSuccess: () => showToast(aceitar ? 'Feito' : 'A casa não vai agir', 'success'),
      onError: () => showToast('A casa não conseguiu confirmar. Nada foi alterado.', 'error'),
    });

  const enviarSilencio = (aceitar: boolean) =>
    silencio.mutate(aceitar, {
      onError: () => showToast('A casa não conseguiu confirmar. Nada foi alterado.', 'error'),
    });

  return (
    <Layout title="Anomalia" showBack>
      {isPending ? (
        <EstadoCarregar />
      ) : isError ? (
        <EstadoErro onRetry={refetch} />
      ) : (
        <article className="space-y-5">
          <header className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <ClasseBadge classe={a.classe} />
              <span className="text-xs text-muted">
                {format(new Date(a.detetadaEm), "d MMM, HH:mm", { locale: pt })}
              </span>
            </div>
            {/* O título da anomalia é o mais importante do ecrã: maior do que o "Anomalia" da barra. */}
            <h2 className="text-2xl font-bold leading-tight">{a.titulo}</h2>
          </header>

          {a.imagemUrl && (
            <img src={a.imagemUrl} alt="Imagem da câmara" className="w-full rounded-xl border border-outline-variant" />
          )}

          <p className="leading-relaxed">{a.explicacao}</p>

          {a.estado === 'resolvida' ? (
            <div className="space-y-3">
              <div role="status" className="flex gap-3 rounded-xl bg-accent-green/10 p-4">
                <Icone
                  nome="check_circle"
                  preenchido
                  className={cn('text-3xl text-accent-green', enviado && 'animate-check-pop')}
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
                    <p className="text-sm text-muted">
                      {enviado.semMotivo
                        ? 'Se voltar a acontecer, a casa avisa outra vez.'
                        : 'A casa vai ter isto em conta da próxima vez.'}
                    </p>
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
            </div>
          ) : (
            <>
              {a.acaoProposta && (
                <section className="space-y-3 rounded-xl border border-primary/30 p-4">
                  <p className="font-semibold">A casa propõe: {a.acaoProposta.descricao}</p>
                  <div className="grid grid-cols-2 gap-2">
                    <Botao onClick={() => enviarDecisao(true)} disabled={ocupado}>
                      {decidir.isPending && decidir.variables === true ? 'A confirmar…' : 'Aceitar'}
                    </Botao>
                    <Botao variante="secundario" onClick={() => enviarDecisao(false)} disabled={ocupado}>
                      Recusar
                    </Botao>
                  </div>
                </section>
              )}

              {!aExplicar ? (
                // Uma ação principal por ecrã: com ação proposta, é o Aceitar; sem ela, é esta.
                <Botao
                  variante={a.acaoProposta ? 'contorno' : 'primario'}
                  largo
                  onClick={() => setAExplicar(true)}
                  disabled={ocupado}
                >
                  Está tudo bem
                </Botao>
              ) : (
                <form
                  onSubmit={e => {
                    e.preventDefault();
                    enviarResposta(texto.trim() || RESPOSTA_SEM_MOTIVO);
                  }}
                  className="space-y-3"
                >
                  <label className="block space-y-2">
                    <span className="block">
                      <span className="font-semibold">Está tudo bem. Quer dizer porquê?</span>{' '}
                      <span className="text-sm text-muted">Opcional</span>
                    </span>
                    <Campo
                      autoFocus
                      enterKeyHint="send"
                      autoCapitalize="sentences"
                      value={texto}
                      onChange={e => setTexto(e.target.value)}
                      placeholder="Fiquei em casa doente"
                    />
                  </label>
                  <div className="space-y-1">
                    <Botao type="submit" largo disabled={ocupado}>
                      {responder.isPending
                        ? 'A enviar…'
                        : texto.trim()
                          ? 'Confirmar'
                          : 'Confirmar sem motivo'}
                    </Botao>
                    <Botao
                      variante="texto"
                      largo
                      onClick={() => {
                        setAExplicar(false);
                        setTexto('');
                      }}
                      disabled={ocupado}
                    >
                      Cancelar
                    </Botao>
                  </div>
                </form>
              )}
            </>
          )}
        </article>
      )}
    </Layout>
  );
}

/** US02: a casa diz o que vai deixar de avisar e até quando; só se aplica depois do Sim. */
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
      <section className="space-y-3 rounded-xl border border-primary/30 p-4">
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
      {proposta.estado === 'aceite' ? `Combinado. ${proposta.texto}` : 'Combinado. A casa continua a avisar.'}
    </p>
  );
}
