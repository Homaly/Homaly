import { useEffect, useRef, useState, type FormEvent } from 'react';
import Layout from '../components/Layout';
import Botao from '../components/Botao';
import Campo from '../components/Campo';
import Icone from '../components/Icone';
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
                    ? 'bg-primary text-on-primary rounded-br-sm'
                    : 'bg-surface-container border border-outline-variant rounded-bl-sm'
                )}
              >
                {m.texto}
              </p>
            </div>
          ))}
          {enviar.isPending && <p className="text-xs text-muted">A casa está a pensar…</p>}
          <div ref={fim} />
        </div>
      )}

      {/* Assenta em cima da barra de baixo (64 px), por baixo do contorno dela. */}
      <form
        onSubmit={submeter}
        className="fixed bottom-16 inset-x-0 z-30 mx-auto max-w-md flex gap-2 px-4 py-2 bg-surface mb-[env(safe-area-inset-bottom)]"
      >
        <Campo
          value={texto}
          onChange={e => setTexto(e.target.value)}
          placeholder="Amanhã vamos de férias uma semana"
          aria-label="Mensagem para a casa"
          className="flex-1 min-w-0 rounded-full"
        />
        <Botao
          type="submit"
          disabled={!texto.trim() || enviar.isPending}
          className="size-12 shrink-0 rounded-full px-0"
          aria-label="Enviar"
        >
          <Icone nome="send" />
        </Botao>
      </form>
    </Layout>
  );
}
