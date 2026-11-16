import { Link } from 'react-router-dom';
import { format, isToday, isYesterday } from 'date-fns';
import { pt } from 'date-fns/locale';
import Layout from '../components/Layout';
import { EstadoCarregar, EstadoErro, EstadoVazio } from '../components/Estados';
import { useEventos } from '../api/hooks';
import type { Evento } from '../types/contract';

function nomeDoDia(d: Date) {
  if (isToday(d)) return 'Hoje';
  if (isYesterday(d)) return 'Ontem';
  return format(d, "EEEE, d 'de' MMMM", { locale: pt });
}

function agruparPorDia(eventos: Evento[]) {
  const ordenados = [...eventos].sort((a, b) => b.em.localeCompare(a.em));
  const grupos = new Map<string, Evento[]>();
  for (const e of ordenados) {
    const dia = nomeDoDia(new Date(e.em));
    grupos.set(dia, [...(grupos.get(dia) ?? []), e]);
  }
  return [...grupos];
}

function LinhaEvento({ e }: { e: Evento }) {
  const conteudo = (
    <>
      <span className="w-12 shrink-0 text-xs tabular-nums text-slate-500 dark:text-slate-400">
        {format(new Date(e.em), 'HH:mm')}
      </span>
      <span className="flex-1 min-w-0">
        <span className="font-medium">{e.dispositivo}</span>
        <span className="text-slate-600 dark:text-slate-300"> · {e.descricao}</span>
      </span>
      {e.anomaliaId && <span className="material-symbols-outlined text-accent-orange text-lg">error</span>}
    </>
  );
  const classes = 'flex items-center gap-3 py-3 text-sm';
  return e.anomaliaId ? (
    <Link to={`/anomalias/${e.anomaliaId}`} className={classes}>
      {conteudo}
    </Link>
  ) : (
    <div className={classes}>{conteudo}</div>
  );
}

export default function Historico() {
  const { data, isPending, isError, refetch } = useEventos();

  return (
    <Layout title="Histórico">
      {isPending ? (
        <EstadoCarregar />
      ) : isError ? (
        <EstadoErro onRetry={refetch} />
      ) : data.length === 0 ? (
        <EstadoVazio icon="history" texto="Ainda não há eventos" />
      ) : (
        <div className="space-y-5">
          {agruparPorDia(data).map(([dia, eventos]) => (
            <section key={dia}>
              <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 first-letter:uppercase">
                {dia}
              </h2>
              <div className="divide-y divide-slate-200 dark:divide-primary/10">
                {eventos.map(e => (
                  <LinhaEvento key={e.id} e={e} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </Layout>
  );
}
