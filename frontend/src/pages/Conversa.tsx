import { useEffect, useRef, useState, type FormEvent } from 'react';
import Layout from '../components/Layout';
import Botao from '../components/Botao';
import Campo from '../components/Campo';
import Icone from '../components/Icone';
import { EstadoCarregar, EstadoErro, EstadoVazio } from '../components/Estados';
import { useConversa, useEnviarMensagem } from '../api/hooks';
import { useToast, type ToastType } from '../context/ToastContext';
import { useDitado, type ErroDitado } from '../hooks/useDitado';
import { cn } from '../lib/cn';

const ERROS_DITADO: Record<ErroDitado, [string, ToastType]> = {
  'sem-permissao': ['Sem acesso ao microfone. Autorize-o nas definições do browser.', 'error'],
  'sem-som': ['Não ouvi nada. Toque no microfone e fale.', 'info'],
  'sem-rede': ['O ditado precisa de ligação à internet.', 'error'],
  'sem-microfone': ['Não encontrei nenhum microfone.', 'error'],
  outro: ['O ditado não funcionou. Escreva a mensagem.', 'error'],
};

/** O que foi ditado, a começar com maiúscula. */
function comMaiuscula(ouvido: string) {
  const o = ouvido.trimStart();
  return o.charAt(0).toUpperCase() + o.slice(1);
}

export default function Conversa() {
  const { data, isPending, isError, refetch } = useConversa();
  const enviar = useEnviarMensagem();
  const { showToast } = useToast();
  const [texto, setTexto] = useState('');
  const fim = useRef<HTMLDivElement>(null);
  /** O que estava na caixa quando o ditado começou; volta se o ditado falhar sem ter ouvido nada. */
  const antesDoDitado = useRef('');
  const ditado = useDitado(
    ouvido => setTexto(comMaiuscula(ouvido)),
    erro => {
      setTexto(t => t || antesDoDitado.current);
      showToast(...ERROS_DITADO[erro]);
    }
  );

  // Ditar substitui o que estava na caixa.
  const alternarDitado = () => {
    if (ditado.aOuvir) return ditado.parar();
    antesDoDitado.current = texto;
    setTexto('');
    ditado.comecar();
  };

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: 'smooth' });
  }, [data?.length, enviar.isPending]);

  const submeter = (e: FormEvent) => {
    e.preventDefault();
    const t = texto.trim();
    if (!t) return;
    ditado.cancelar();
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
                  'max-w-[80%] rounded-2xl px-4 py-2.5 text-[15px]',
                  m.autor === 'pessoa'
                    ? 'bg-primary text-on-primary rounded-br-sm'
                    : 'bg-surface-container rounded-bl-sm'
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
        className="fixed bottom-16 inset-x-0 z-30 mx-auto max-w-md flex gap-2 px-5 py-2 bg-surface mb-[env(safe-area-inset-bottom)]"
      >
        <div className="relative min-w-0 flex-1">
          <Campo
            value={texto}
            onChange={e => setTexto(e.target.value)}
            readOnly={ditado.aOuvir}
            placeholder={ditado.aOuvir ? 'A ouvir…' : 'Amanhã vamos de férias uma semana'}
            aria-label="Mensagem para a casa"
            className={cn('rounded-full', ditado.suportado && 'pr-12', ditado.aOuvir && 'border-primary-ink')}
          />
          {/* Ditado: o texto ouvido aparece na caixa e não é enviado sozinho; a pessoa revê e envia. */}
          {ditado.suportado && (
            // 48 px de toque; o círculo que se vê tem 36 px, para ficar por dentro do contorno da caixa.
            <button
              type="button"
              onClick={alternarDitado}
              aria-label="Ditar mensagem"
              aria-pressed={ditado.aOuvir}
              className="group absolute inset-y-0 right-0 flex w-12 items-center justify-center rounded-full"
            >
              <span
                className={cn(
                  'flex size-9 items-center justify-center rounded-full transition-colors',
                  ditado.aOuvir
                    ? 'bg-primary text-on-primary'
                    : 'text-on-surface-variant group-hover:bg-surface-tonal'
                )}
              >
                <Icone
                  nome={ditado.aOuvir ? 'stop' : 'mic'}
                  className={cn('size-5', ditado.aOuvir && 'fill-current motion-safe:animate-pulse')}
                />
              </span>
            </button>
          )}
        </div>
        <Botao
          type="submit"
          disabled={!texto.trim() || enviar.isPending}
          className="size-12 shrink-0 rounded-full px-0"
          aria-label="Enviar"
        >
          <Icone nome="send" className="size-5" />
        </Botao>
      </form>
    </Layout>
  );
}
