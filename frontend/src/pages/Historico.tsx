import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import { format, isToday, isYesterday } from 'date-fns';
import { pt } from 'date-fns/locale';
import Layout from '../components/Layout';
import Icone from '../components/Icone';
import { EstadoCarregar, EstadoErro, EstadoVazio } from '../components/Estados';
import { useEventos } from '../api/hooks';
import { cn } from '../lib/cn';
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
      <span className="w-12 shrink-0 text-sm tabular-nums text-muted">
        {format(new Date(e.em), 'HH:mm')}
      </span>
      <span className="flex-1 min-w-0">
        <span className="font-medium">{e.dispositivo}</span>
        <span className="text-on-surface-variant"> · {e.descricao}</span>
      </span>
      {e.anomaliaId && (
        <>
          <Icone nome="error" className="size-5 text-accent-orange" />
          <span className="sr-only">Ver anomalia</span>
        </>
      )}
    </>
  );
  const classes = 'flex min-h-14 items-center gap-3 py-3';
  return e.anomaliaId ? (
    <Link to={`/anomalias/${e.anomaliaId}`} className={classes}>
      {conteudo}
    </Link>
  ) : (
    <div className={classes}>{conteudo}</div>
  );
}

/**
 * Um dia do histórico, recolhível: o cabeçalho (nome do dia e número de eventos) abre e fecha a
 * lista. Só o "Hoje" começa aberto. Abre a deslizar (a altura anima de 0fr a 1fr); fechado, o
 * conteúdo fica `inert`, para o Tab e o leitor de ecrã não entrarem nas linhas escondidas.
 */
function Dia({ dia, eventos }: { dia: string; eventos: Evento[] }) {
  const [aberto, setAberto] = useState(dia === 'Hoje');
  const lista = useId();
  return (
    <section>
      <h2>
        <button
          type="button"
          aria-expanded={aberto}
          aria-controls={lista}
          onClick={() => setAberto(a => !a)}
          className="flex min-h-12 w-full items-center justify-between gap-3 text-left"
        >
          <span className="text-xl font-semibold first-letter:uppercase">
            {dia}
            <span className="text-base font-medium text-muted"> ({eventos.length})</span>
          </span>
          <Icone
            nome="expand_more"
            className={cn(
              'size-6 text-muted transition-transform duration-300 ease-emphasized motion-reduce:transition-none',
              aberto && 'rotate-180'
            )}
          />
        </button>
      </h2>
      <div
        id={lista}
        inert={!aberto}
        className={cn(
          'grid transition-[grid-template-rows] duration-300 ease-emphasized motion-reduce:transition-none',
          aberto ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        )}
      >
        <div className="overflow-hidden">
          <div className="mt-1 mb-3 divide-y divide-outline-variant rounded-2xl bg-surface-container px-4">
            {eventos.map(e => (
              <LinhaEvento key={e.id} e={e} />
            ))}
          </div>
        </div>
      </div>
    </section>
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
        <EstadoVazio icon="history" texto="Ainda não há eventos" descricao="Os eventos dos dispositivos aparecem aqui." />
      ) : (
        // Os dias entram em cascata (ver .cascata em index.css).
        <div className="cascata space-y-1">
          {agruparPorDia(data).map(([dia, eventos]) => (
            <Dia key={dia} dia={dia} eventos={eventos} />
          ))}
        </div>
      )}
    </Layout>
  );
}
