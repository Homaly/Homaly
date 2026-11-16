import { useEffect, useRef, useState, type FormEvent } from 'react';
import Layout from '../components/Layout';
import { EstadoCarregar, EstadoErro, EstadoVazio } from '../components/Estados';
import { useConversa, useEnviarMensagem } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import { cn } from '../lib/cn';

export default function Conversa() {
  const { data, isPending, isError, refetch } = useConversa();
  const enviar = useEnviarMensagem();
  const { showToast } = useToast();
  const [texto, setTexto] = useState('');
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: 'smooth' });
  }, [data?.length, enviar.isPending]);

  const submeter = (e: FormEvent) => {
    e.preventDefault();
    const t = texto.trim();
    if (!t) return;
    setTexto('');
    enviar.mutate(t, { onError: () => showToast('A mensagem não chegou à casa', 'error') });
  };

  return (
    <Layout title="Conversa">
      {isPending ? (
        <EstadoCarregar />
      ) : isError ? (
        <EstadoErro onRetry={refetch} />
      ) : (
        <div className="space-y-2 pb-16">
          {data.length === 0 && (
            <EstadoVazio icon="chat" texto="Conte à casa o que vai mudar na rotina." />
          )}
          {data.map(m => (
            <div key={m.id} className={cn('flex', m.autor === 'pessoa' ? 'justify-end' : 'justify-start')}>
              <p
                className={cn(
                  'max-w-[80%] rounded-2xl px-3.5 py-2 text-sm',
                  m.autor === 'pessoa'
                    ? 'bg-primary text-background-dark rounded-br-sm'
                    : 'bg-white dark:bg-card-dark border border-slate-200 dark:border-primary/10 rounded-bl-sm'
                )}
              >
                {m.texto}
              </p>
            </div>
          ))}
          {enviar.isPending && <p className="text-xs text-slate-500 dark:text-slate-400">A casa está a pensar…</p>}
          <div ref={fim} />
        </div>
      )}

      <form
        onSubmit={submeter}
        className="fixed bottom-16 inset-x-0 z-30 mx-auto max-w-md flex gap-2 px-4 py-2 bg-background-light dark:bg-background-dark mb-[env(safe-area-inset-bottom)]"
      >
        <input
          value={texto}
          onChange={e => setTexto(e.target.value)}
          placeholder="Ex.: amanhã vamos de férias uma semana"
          className="flex-1 min-w-0 rounded-full border border-slate-200 dark:border-primary/20 bg-white dark:bg-card-dark px-4 py-2.5 text-sm focus:outline-none focus:border-primary"
        />
        <button
          type="submit"
          disabled={!texto.trim() || enviar.isPending}
          className="size-11 shrink-0 rounded-full bg-primary text-background-dark flex items-center justify-center disabled:opacity-50"
          aria-label="Enviar"
        >
          <span className="material-symbols-outlined">send</span>
        </button>
      </form>
    </Layout>
  );
}
