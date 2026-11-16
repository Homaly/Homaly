import { useState } from 'react';
import Layout from '../components/Layout';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import { useDefinicoes, useGuardarDefinicoes } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import type { Definicoes as Defs } from '../types/contract';

const campo =
  'w-full rounded-lg border border-slate-200 dark:border-primary/20 bg-white dark:bg-card-dark px-3 py-2.5 text-sm focus:outline-none focus:border-primary';

function Formulario({ inicial }: { inicial: Defs }) {
  const guardar = useGuardarDefinicoes();
  const { showToast } = useToast();
  const [nome, setNome] = useState(inicial.contacto?.nome ?? '');
  const [telegram, setTelegram] = useState(inicial.contacto?.telegram ?? '');
  const [espera, setEspera] = useState(String(inicial.esperaMinutos));

  const esperaNum = Number(espera);
  const esperaValida = espera !== '' && Number.isInteger(esperaNum) && esperaNum >= 0;
  const contactoIncompleto = (nome.trim() === '') !== (telegram.trim() === '');

  const submeter = (contacto: Defs['contacto']) =>
    guardar.mutate(
      { contacto, esperaMinutos: esperaNum },
      {
        onSuccess: () => showToast('Definições guardadas', 'success'),
        onError: () => showToast('Não foi possível guardar', 'error'),
      }
    );

  return (
    <form
      onSubmit={e => {
        e.preventDefault();
        submeter(nome.trim() ? { nome: nome.trim(), telegram: telegram.trim() } : null);
      }}
      className="space-y-6"
    >
      <section className="space-y-3">
        <div>
          <h2 className="font-semibold">Contacto externo</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Recebe no Telegram os alertas de segurança e de bem-estar quando não responde a tempo. Opcional.
          </p>
        </div>
        <label className="block space-y-1">
          <span className="text-sm">Nome</span>
          <input value={nome} onChange={e => setNome(e.target.value)} className={campo} placeholder="Ex.: Vizinha Ana" />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Telegram</span>
          <input value={telegram} onChange={e => setTelegram(e.target.value)} className={campo} />
        </label>
        {inicial.contacto && (
          <button
            type="button"
            disabled={guardar.isPending}
            onClick={() => {
              setNome('');
              setTelegram('');
              submeter(null);
            }}
            className="text-sm font-semibold text-red-500 disabled:opacity-50"
          >
            Remover contacto
          </button>
        )}
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="font-semibold">Tempo de espera</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Minutos antes de avisar o contacto externo. Zero avisa ao mesmo tempo.
          </p>
        </div>
        <input
          type="number"
          inputMode="numeric"
          min={0}
          step={1}
          value={espera}
          onChange={e => setEspera(e.target.value)}
          className={campo}
        />
      </section>

      {contactoIncompleto && (
        <p className="text-xs text-accent-orange">Preencha o nome e o Telegram, ou deixe os dois vazios.</p>
      )}
      <button
        type="submit"
        disabled={guardar.isPending || !esperaValida || contactoIncompleto}
        className="w-full py-2.5 rounded-lg bg-primary text-background-dark font-semibold disabled:opacity-50"
      >
        {guardar.isPending ? 'A guardar…' : 'Guardar'}
      </button>
    </form>
  );
}

export default function Definicoes() {
  const { data, isPending, isError, refetch } = useDefinicoes();
  return (
    <Layout title="Definições">
      {isPending ? <EstadoCarregar /> : isError ? <EstadoErro onRetry={refetch} /> : <Formulario inicial={data} />}
    </Layout>
  );
}
