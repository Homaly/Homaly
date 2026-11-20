import { useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useCalendario, useSincronizarCalendario } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import type { Calendario } from '../types/contract';
import Botao from './Botao';
import Grupo from './Grupo';
import Icone from './Icone';

const ligar = () => window.location.assign(api.urlLigarCalendario());

const hora = (iso: string) => new Date(iso).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });

/** Mostra "Calendário ligado" ou o erro quando a Google devolve a pessoa (?calendario=ligado|erro). */
function useResultadoDaLigacao() {
  const [params, setParams] = useSearchParams();
  const { showToast } = useToast();
  const mostrado = useRef(false);
  const resultado = params.get('calendario');

  useEffect(() => {
    if (!resultado || mostrado.current) return;
    mostrado.current = true;
    if (resultado === 'ligado') showToast('Calendário ligado', 'success');
    else showToast('Não foi possível ligar ao calendário', 'error');
    setParams({}, { replace: true });
  }, [resultado, setParams, showToast]);
}

function Ligado({ calendario }: { calendario: Calendario }) {
  const sincronizar = useSincronizarCalendario();
  const { showToast } = useToast();
  return (
    <div className="space-y-4">
      <p className="text-sm text-on-surface-variant">
        Ligado a <span className="font-medium text-on-surface">{calendario.email ?? 'uma conta Google'}</span>
        {calendario.lidoEm && <> · lido às {hora(calendario.lidoEm)}</>}
      </p>
      {calendario.erro && (
        <div className="space-y-2">
          <p role="alert" className="text-sm text-danger">
            {calendario.erro}
          </p>
          <Botao largo variante="contorno" onClick={ligar}>
            <Icone nome="calendar" className="size-5" />
            Ligar outra vez
          </Botao>
        </div>
      )}
      <div className="space-y-2 border-t border-outline-variant pt-4">
        <h3 className="text-sm font-semibold">O que a casa sabe pelo calendário</h3>
        {calendario.itens.length === 0 ? (
          <p className="text-sm text-muted">Nada por agora: não há férias, rotinas nem compromissos à vista.</p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {calendario.itens.map((item, i) => (
              <li key={i} className="flex gap-2">
                <span aria-hidden className="text-muted">•</span>
                <span>{item.texto}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <Botao
          variante="contorno"
          disabled={sincronizar.isPending}
          onClick={() =>
            sincronizar.mutate(undefined, {
              onError: () => showToast('Não foi possível atualizar o calendário', 'error'),
            })
          }
        >
          {sincronizar.isPending ? 'A atualizar…' : 'Atualizar'}
        </Botao>
        <Link
          to="/definicoes/calendario/remover"
          className="inline-flex min-h-12 items-center rounded-full px-3 font-semibold text-danger"
        >
          Remover calendário
        </Link>
      </div>
    </div>
  );
}

function PorLigar({ configurado }: { configurado: boolean }) {
  if (!configurado) {
    return <p className="text-sm text-muted">A ligação ao Google Calendar ainda não está configurada nesta casa.</p>;
  }
  // Contorno, não turquesa: o botão principal das Definições é o Guardar.
  return (
    <Botao largo variante="contorno" onClick={ligar}>
      <Icone nome="calendar" className="size-5" />
      Ligar ao Google Calendar
    </Botao>
  );
}

/** Definições → Calendário: ligar o Google Calendar, ver o que a casa sabe por ele e remover. */
export default function SecaoCalendario() {
  useResultadoDaLigacao();
  const { data, isPending, isError } = useCalendario();

  return (
    <Grupo titulo="Calendário" nota="A casa fica a saber das suas férias e rotinas sem ter de as dizer.">
      {isPending ? (
        <div className="h-12 motion-safe:animate-pulse rounded-full bg-surface-tonal" aria-label="A carregar" />
      ) : isError ? (
        <p className="text-sm text-danger">Não foi possível saber se o calendário está ligado.</p>
      ) : data.ligado ? (
        <Ligado calendario={data} />
      ) : (
        <PorLigar configurado={data.configurado} />
      )}
    </Grupo>
  );
}
