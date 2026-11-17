import { useState } from 'react';
import Layout from '../components/Layout';
import Botao from '../components/Botao';
import Campo from '../components/Campo';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import { useDefinicoes, useGuardarDefinicoes } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import type { Definicoes as Defs } from '../types/contract';

function Formulario({ inicial }: { inicial: Defs }) {
  const guardar = useGuardarDefinicoes();
  const { showToast } = useToast();
  const [nome, setNome] = useState(inicial.contacto?.nome ?? '');
  const [telemovel, setTelemovel] = useState(inicial.contacto?.telemovel ?? '');
  const [espera, setEspera] = useState(String(inicial.esperaMinutos));
  const [nomeCasa, setNomeCasa] = useState(inicial.nomeCasa ?? '');

  const esperaNum = Number(espera);
  const esperaValida = espera !== '' && Number.isInteger(esperaNum) && esperaNum >= 0 && esperaNum <= 1440;
  const contactoIncompleto = (nome.trim() === '') !== (telemovel.trim() === '');

  const submeter = (contacto: Defs['contacto']) =>
    guardar.mutate(
      { contacto, esperaMinutos: esperaNum, ...(nomeCasa.trim() ? { nomeCasa: nomeCasa.trim() } : {}) },
      {
        onSuccess: () => showToast('Definições guardadas', 'success'),
        onError: () => showToast('Não foi possível guardar. Confirme o número de telemóvel.', 'error'),
      }
    );

  return (
    <form
      onSubmit={e => {
        e.preventDefault();
        submeter(nome.trim() ? { nome: nome.trim(), telemovel: telemovel.trim() } : null);
      }}
      className="space-y-6"
    >
      <section className="space-y-3">
        <div>
          <h2 className="font-semibold">Nome da casa</h2>
          <p className="text-sm text-muted">
            É assim que o contacto externo reconhece a casa na SMS. Opcional.
          </p>
        </div>
        <Campo
          value={nomeCasa}
          onChange={e => setNomeCasa(e.target.value)}
          placeholder="Casa da D. Maria"
          maxLength={60}
          aria-label="Nome da casa"
        />
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="font-semibold">Contacto externo</h2>
          <p className="text-sm text-muted">
            Recebe por SMS os alertas de segurança e de bem-estar quando não responde a tempo. Opcional.
          </p>
        </div>
        <label className="block space-y-1">
          <span className="text-sm">Nome</span>
          <Campo value={nome} onChange={e => setNome(e.target.value)} placeholder="Vizinha Ana" maxLength={60} />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Telemóvel</span>
          <Campo
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={telemovel}
            onChange={e => setTelemovel(e.target.value)}
            placeholder="912 345 678"
          />
        </label>
        {inicial.contacto && (
          <Botao
            variante="perigo"
            disabled={guardar.isPending}
            onClick={() => {
              setNome('');
              setTelemovel('');
              submeter(null);
            }}
            className="-ml-3 px-3 text-sm"
          >
            Remover contacto
          </Botao>
        )}
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="font-semibold">Tempo de espera</h2>
          <p className="text-sm text-muted">
            Minutos antes de avisar o contacto externo. Zero avisa ao mesmo tempo.
          </p>
        </div>
        <Campo
          type="number"
          inputMode="numeric"
          min={0}
          max={1440}
          step={1}
          value={espera}
          onChange={e => setEspera(e.target.value)}
          aria-label="Tempo de espera, em minutos"
        />
      </section>

      {contactoIncompleto && (
        <p className="text-sm text-danger">Preencha o nome e o telemóvel, ou deixe os dois vazios.</p>
      )}
      <Botao type="submit" largo disabled={guardar.isPending || !esperaValida || contactoIncompleto}>
        {guardar.isPending ? 'A guardar…' : 'Guardar'}
      </Botao>
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
