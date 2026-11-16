import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { format } from 'date-fns';
import { pt } from 'date-fns/locale';
import Layout from '../components/Layout';
import { ClasseBadge } from '../components/AnomaliaCard';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import { useAnomalia, useDecidirAcao, useResponderAnomalia } from '../api/hooks';
import { useToast } from '../context/ToastContext';

export default function Anomalia() {
  const { id = '' } = useParams();
  const { data: a, isPending, isError, refetch } = useAnomalia(id);
  const responder = useResponderAnomalia(id);
  const decidir = useDecidirAcao(id);
  const { showToast } = useToast();
  const [texto, setTexto] = useState('');

  const ocupado = responder.isPending || decidir.isPending;

  const enviarResposta = (t: string) =>
    responder.mutate(t, {
      onSuccess: () => {
        setTexto('');
        showToast('Resposta registada', 'success');
      },
      onError: () => showToast('Não foi possível enviar a resposta', 'error'),
    });

  const enviarDecisao = (aceitar: boolean) =>
    decidir.mutate(aceitar, {
      onSuccess: () => showToast(aceitar ? 'Feito' : 'A casa não vai agir', 'success'),
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
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {format(new Date(a.detetadaEm), "d MMM, HH:mm", { locale: pt })}
              </span>
            </div>
            <h2 className="text-lg font-bold">{a.titulo}</h2>
          </header>

          {a.imagemUrl && (
            <img src={a.imagemUrl} alt="Imagem da câmara" className="w-full rounded-xl border border-slate-200 dark:border-primary/10" />
          )}

          <p className="text-slate-700 dark:text-slate-200 leading-relaxed">{a.explicacao}</p>

          {a.estado === 'resolvida' ? (
            <div className="rounded-xl bg-accent-green/10 p-4 text-sm">
              <p className="font-semibold text-accent-green">Resolvida</p>
              {a.resposta && (
                <p className="mt-1">
                  {a.resposta.texto}
                  <span className="text-slate-500 dark:text-slate-400">
                    {' · '}
                    {format(new Date(a.resposta.em), 'HH:mm', { locale: pt })}
                  </span>
                </p>
              )}
            </div>
          ) : (
            <>
              {a.acaoProposta && (
                <section className="rounded-xl border border-primary/30 p-4 space-y-3">
                  <p className="text-sm font-semibold">A casa propõe: {a.acaoProposta.descricao}</p>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => enviarDecisao(true)}
                      disabled={ocupado}
                      className="py-2.5 rounded-lg bg-primary text-background-dark font-semibold disabled:opacity-50"
                    >
                      {decidir.isPending && decidir.variables === true ? 'A confirmar…' : 'Aceitar'}
                    </button>
                    <button
                      onClick={() => enviarDecisao(false)}
                      disabled={ocupado}
                      className="py-2.5 rounded-lg bg-slate-200 dark:bg-primary/10 font-semibold disabled:opacity-50"
                    >
                      Recusar
                    </button>
                  </div>
                </section>
              )}

              <section className="space-y-3">
                <button
                  onClick={() => enviarResposta('Está tudo bem')}
                  disabled={ocupado}
                  className="w-full py-2.5 rounded-lg bg-accent-green/15 text-accent-green font-semibold disabled:opacity-50"
                >
                  Está tudo bem
                </button>
                <form
                  onSubmit={e => {
                    e.preventDefault();
                    if (texto.trim()) enviarResposta(texto.trim());
                  }}
                  className="flex gap-2"
                >
                  <input
                    value={texto}
                    onChange={e => setTexto(e.target.value)}
                    placeholder="Explicar o que se passa…"
                    className="flex-1 min-w-0 rounded-lg border border-slate-200 dark:border-primary/20 bg-white dark:bg-card-dark px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
                  />
                  <button
                    type="submit"
                    disabled={ocupado || !texto.trim()}
                    className="px-4 rounded-lg bg-primary text-background-dark font-semibold disabled:opacity-50"
                    aria-label="Enviar"
                  >
                    <span className="material-symbols-outlined">send</span>
                  </button>
                </form>
              </section>
            </>
          )}
        </article>
      )}
    </Layout>
  );
}
