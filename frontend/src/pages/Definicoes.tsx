import { useState } from 'react';
import Layout from '../components/Layout';
import Botao from '../components/Botao';
import Campo from '../components/Campo';
import Grupo from '../components/Grupo';
import Segmentado, { type OpcaoSegmentado } from '../components/Segmentado';
import SecaoCalendario from '../components/SecaoCalendario';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import { useDefinicoes, useGuardarDefinicoes } from '../api/hooks';
import { useTheme, type Theme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';
import type { Definicoes as Defs } from '../types/contract';

/** Tempos de espera à escolha, em minutos: 0.5 são 30 segundos. */
const ESPERAS = [0.5, 5, 15, 30];

function rotuloEspera(min: number) {
  if (min === 0) return 'Logo';
  if (min < 1) return `${Math.round(min * 60)} s`;
  return min % 60 === 0 ? `${min / 60} h` : `${min} min`;
}

/** Um valor guardado fora da lista (o backend aceita até 1440) junta-se a ela, para não se perder. */
function opcoesEspera(guardado: number): OpcaoSegmentado<number>[] {
  const valores = ESPERAS.includes(guardado) ? ESPERAS : [...ESPERAS, guardado].sort((a, b) => a - b);
  return valores.map(v => ({ valor: v, rotulo: rotuloEspera(v) }));
}

const TEMAS: OpcaoSegmentado<Theme>[] = [
  { valor: 'system', rotulo: 'Automático' },
  { valor: 'light', rotulo: 'Claro' },
  { valor: 'dark', rotulo: 'Escuro' },
];

/** Contacto externo, tempo de espera e nome da casa: vão para o backend juntos, com o Guardar. */
function Formulario({ inicial }: { inicial: Defs }) {
  const guardar = useGuardarDefinicoes();
  const { showToast } = useToast();
  const [nome, setNome] = useState(inicial.contacto?.nome ?? '');
  const [telemovel, setTelemovel] = useState(inicial.contacto?.telemovel ?? '');
  const [espera, setEspera] = useState(inicial.esperaMinutos);
  const [nomeCasa, setNomeCasa] = useState(inicial.nomeCasa ?? '');
  const [esperas] = useState(() => opcoesEspera(inicial.esperaMinutos));

  const contactoIncompleto = (nome.trim() === '') !== (telemovel.trim() === '');

  const submeter = (contacto: Defs['contacto']) =>
    guardar.mutate(
      { contacto, esperaMinutos: espera, ...(nomeCasa.trim() ? { nomeCasa: nomeCasa.trim() } : {}) },
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
      <Grupo
        titulo="Contacto externo"
        nota="Recebe por SMS os alertas de segurança e de bem-estar quando não responde dentro do tempo de espera. Opcional."
      >
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Nome</span>
          <Campo value={nome} onChange={e => setNome(e.target.value)} placeholder="Vizinha Ana" maxLength={60} />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Telemóvel</span>
          <Campo
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={telemovel}
            onChange={e => setTelemovel(e.target.value)}
            placeholder="912 345 678"
          />
        </label>
        <div className="space-y-1.5">
          <p aria-hidden className="text-sm font-medium">
            Tempo de espera
          </p>
          <Segmentado rotulo="Tempo de espera" opcoes={esperas} valor={espera} onChange={setEspera} />
        </div>
        {inicial.contacto && (
          <Botao
            variante="perigo"
            disabled={guardar.isPending}
            onClick={() => {
              setNome('');
              setTelemovel('');
              submeter(null);
            }}
            className="-mb-2 -ml-3 px-3 text-sm"
          >
            Remover contacto
          </Botao>
        )}
      </Grupo>

      <Grupo titulo="Casa" nota="É assim que o contacto externo reconhece a casa na SMS. Opcional.">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Nome da casa</span>
          <Campo value={nomeCasa} onChange={e => setNomeCasa(e.target.value)} placeholder="Casa da D. Maria" maxLength={60} />
        </label>
      </Grupo>

      {contactoIncompleto && (
        <p className="text-sm text-danger">Preencha o nome e o telemóvel, ou deixe os dois vazios.</p>
      )}
      <Botao type="submit" largo disabled={guardar.isPending || contactoIncompleto}>
        {guardar.isPending ? 'A guardar…' : 'Guardar'}
      </Botao>
    </form>
  );
}

/** O tema fica neste telemóvel (não vai para o backend) e muda logo, sem Guardar. */
function Aparencia() {
  const [theme, setTheme] = useTheme();
  return (
    <Grupo titulo="Aparência" nota="Automático segue o tema do telemóvel.">
      <Segmentado rotulo="Tema" opcoes={TEMAS} valor={theme} onChange={setTheme} />
    </Grupo>
  );
}

export default function Definicoes() {
  const { data, isPending, isError, refetch } = useDefinicoes();
  return (
    <Layout title="Definições">
      {/* Primeiro o que se guarda com o botão; depois o que muda logo (calendário e tema). */}
      <div className="space-y-8">
        {isPending ? <EstadoCarregar /> : isError ? <EstadoErro onRetry={refetch} /> : <Formulario inicial={data} />}
        <SecaoCalendario />
        <Aparencia />
      </div>
    </Layout>
  );
}
