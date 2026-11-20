import { Link, Navigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Botao from '../components/Botao';
import Grupo from '../components/Grupo';
import Linha from '../components/Linha';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import { useCalendario, useSincronizarCalendario } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import { anonimizarEmail, hora, ligarCalendario } from '../lib/calendario';

/**
 * Definições → Calendário: a conta conectada (e-mail anonimizado) e, à parte, remover.
 * Como o detalhe de uma conta nas definições do telemóvel: grupos de linhas e a ação destrutiva à parte.
 */
export default function Calendario() {
  const { data, isPending, isError, refetch } = useCalendario();
  const sincronizar = useSincronizarCalendario();
  const { showToast } = useToast();

  const atualizar = () =>
    sincronizar.mutate(undefined, {
      onError: () => showToast('Não foi possível atualizar o calendário', 'error'),
    });

  return (
    <Layout title="Calendário" showBack>
      {isPending ? (
        <EstadoCarregar />
      ) : isError ? (
        <EstadoErro onRetry={refetch} />
      ) : !data.ligado ? (
        // Sem calendário não há detalhe: a linha das Definições é que liga.
        <Navigate to="/definicoes" replace />
      ) : (
        <div className="space-y-6">
          <Grupo titulo="Conta" lista>
            <Linha
              icone="calendar"
              titulo={data.email ? anonimizarEmail(data.email) : 'Conta Google'}
              descricao={
                sincronizar.isPending
                  ? 'A ler…'
                  : data.lidoEm
                    ? `Lido às ${hora(data.lidoEm)}`
                    : 'Ainda não foi lido'
              }
              fim={
                <button
                  type="button"
                  onClick={atualizar}
                  disabled={sincronizar.isPending}
                  className="-mr-2 min-h-12 shrink-0 px-2 font-semibold text-primary-ink disabled:opacity-50"
                >
                  Atualizar
                </button>
              }
            />
            {data.erro && (
              <div className="space-y-3 py-3">
                <p role="alert" className="text-sm text-danger first-letter:uppercase">
                  {data.erro}
                </p>
                <Botao largo variante="contorno" onClick={() => ligarCalendario()}>
                  Conectar outra vez
                </Botao>
              </div>
            )}
          </Grupo>

          {/* A ação destrutiva no seu próprio grupo, em baixo; a confirmação é o ecrã seguinte. */}
          <Grupo lista>
            <Link to="/definicoes/calendario/remover" className="block text-danger">
              <Linha titulo="Remover calendário" />
            </Link>
          </Grupo>
        </div>
      )}
    </Layout>
  );
}
