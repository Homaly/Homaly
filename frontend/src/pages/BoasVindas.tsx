import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Botao from '../components/Botao';
import BarraProgresso from '../components/BarraProgresso';
import Campo from '../components/Campo';
import EscolhaGrande, { type OpcaoGrande } from '../components/EscolhaGrande';
import Icone from '../components/Icone';
import Linha from '../components/Linha';
import LogoAnimado, { Balao } from '../components/LogoAnimado';
import { EstadoCarregar, EstadoErro } from '../components/Estados';
import { useCalendario, useDefinicoes, useGuardarDefinicoes } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import { marcarBoasVindasVistas } from '../lib/boasVindas';
import { ligarCalendario } from '../lib/calendario';
import type { Definicoes } from '../types/contract';

type Passo = 'ola' | 'nome' | 'contacto' | 'espera' | 'calendario' | 'fim';

/**
 * Os ecrãs depois da abertura, por ordem: cada um enche a barra na mesma medida. O tempo de
 * espera só conta se houver contacto (sem ele não se pergunta), para não haver saltos maiores.
 */
const ecrasDaBarra = (comContacto: boolean): Passo[] =>
  comContacto ? ['nome', 'contacto', 'espera', 'calendario', 'fim'] : ['nome', 'contacto', 'calendario', 'fim'];

const ESPERAS: OpcaoGrande<number>[] = [
  { valor: 0.5, rotulo: '30 segundos' },
  { valor: 5, rotulo: '5 minutos' },
  { valor: 15, rotulo: '15 minutos' },
  { valor: 30, rotulo: '30 minutos' },
];

const rotuloEspera = (min: number) => ESPERAS.find(e => e.valor === min)?.rotulo ?? `${min} min`;

/** Ao voltar da Google (?calendario=ligado|erro), continua onde ficou. */
function passoInicial(resultado: string | null): Passo {
  if (resultado === 'ligado') return 'fim';
  if (resultado === 'erro') return 'calendario';
  return 'ola';
}

/** O cimo de cada passo: a casa a falar, num balão. */
function Fala({ batida, grande, salta, children }: { batida: number; grande?: boolean; salta?: boolean; children: ReactNode }) {
  if (grande) {
    // Abertura e fim: a casa grande e centrada, o balão por cima.
    return (
      <div className="flex flex-col items-center gap-8 pt-6 text-center">
        <Balao bico="baixo">
          <h1 className="text-xl">{children}</h1>
        </Balao>
        <LogoAnimado batida={batida} salta={salta} className="w-44 text-on-surface" />
      </div>
    );
  }
  return (
    <div className="flex items-start gap-3">
      <LogoAnimado batida={batida} className="w-24 shrink-0 text-on-surface" />
      <Balao>
        <h1 className="text-lg">{children}</h1>
      </Balao>
    </div>
  );
}

/** O que diz por baixo do balão no passo do calendário (o erro de uma tentativa já vai no balão). */
function PassoCalendario() {
  const { data } = useCalendario();
  if (data?.ligado) {
    return (
      <p className="flex items-center gap-2 font-semibold text-accent-green">
        <Icone nome="check_circle" className="size-5" /> Já está conectado
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {data && !data.configurado ? (
        <p className="text-sm text-muted">O Google Calendar ainda não está configurado nesta casa. Pode ligá-lo mais tarde nas Definições.</p>
      ) : (
        <p className="text-sm text-muted">Abre a página da Google para dar autorização. Só se lê o calendário; nada é alterado.</p>
      )}
    </div>
  );
}

function Resumo({ nomeCasa, contacto, espera }: { nomeCasa: string; contacto: Definicoes['contacto']; espera: number }) {
  const { data: calendario } = useCalendario();
  const falta = <span className="text-muted">Por definir</span>;
  return (
    <div className="divide-y divide-outline-variant rounded-2xl bg-surface-container px-4">
      <Linha icone="home" titulo="Casa" descricao={nomeCasa || falta} />
      <Linha
        icone="chat"
        titulo="Contacto externo"
        descricao={contacto ? `${contacto.nome}, ao fim de ${rotuloEspera(espera)}` : falta}
      />
      <Linha icone="calendar" titulo="Google Calendar" descricao={calendario?.ligado ? 'Conectado' : falta} />
    </div>
  );
}

function Fluxo({ inicial }: { inicial: Definicoes }) {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const guardar = useGuardarDefinicoes();
  const { data: calendario } = useCalendario();
  const [params, setParams] = useSearchParams();
  const resultado = params.get('calendario');
  const [passo, setPasso] = useState<Passo>(() => passoInicial(resultado));
  const [erroCalendario] = useState(resultado === 'erro');
  const [nomeCasa, setNomeCasa] = useState(inicial.nomeCasa ?? '');
  const [nome, setNome] = useState(inicial.contacto?.nome ?? '');
  const [telemovel, setTelemovel] = useState(inicial.contacto?.telemovel ?? '');
  // "Agora não" marca o passo como saltado mas não apaga o que foi escrito: ao voltar atrás, está lá.
  const [saltouNome, setSaltouNome] = useState(false);
  const [saltouContacto, setSaltouContacto] = useState(false);
  const [espera, setEspera] = useState(ESPERAS.some(e => e.valor === inicial.esperaMinutos) ? inicial.esperaMinutos : 5);

  // O resultado já se vê no passo (balão ou resumo): só se limpa o endereço.
  useEffect(() => {
    if (resultado) setParams({}, { replace: true });
  }, [resultado, setParams]);

  /** O passo anterior; do calendário, salta o tempo de espera se não há contacto (não se perguntou). */
  const anterior: Partial<Record<Passo, Passo>> = {
    contacto: 'nome',
    espera: 'contacto',
    calendario: saltouContacto ? 'contacto' : 'espera',
    fim: 'calendario',
  };
  const voltar = anterior[passo];
  const ecras = ecrasDaBarra(!saltouContacto);
  const feitos = ecras.indexOf(passo) + 1; // a abertura não está na lista: 0

  const sair = () => {
    marcarBoasVindasVistas();
    navigate('/', { replace: true });
  };

  /** Guarda nome, contacto e tempo antes do calendário: a ida à Google sai da app e perde o que não foi guardado. */
  const nomeGuardado = saltouNome ? '' : nomeCasa.trim();
  const guardarESeguir = (contacto: Definicoes['contacto']) =>
    guardar.mutate(
      { contacto, esperaMinutos: espera, ...(nomeGuardado ? { nomeCasa: nomeGuardado } : {}) },
      {
        onSuccess: () => setPasso('calendario'),
        onError: () => {
          showToast('Não foi possível guardar. Confirme o número de telemóvel.', 'error');
          setPasso('contacto');
        },
      }
    );

  const contactoPreenchido = nome.trim() !== '' && telemovel.trim() !== '';
  const contactoIncompleto = (nome.trim() === '') !== (telemovel.trim() === '');
  const contacto = contactoPreenchido && !saltouContacto ? { nome: nome.trim(), telemovel: telemovel.trim() } : null;

  let fala: ReactNode;
  let corpo: ReactNode = null;
  let continuar = { rotulo: 'Continuar', acao: () => {}, desativado: false };
  let saltar: (() => void) | null = null;

  switch (passo) {
    case 'ola':
      fala = 'Olá! Sou a Homaly, a casa que repara. Vamos preparar tudo?';
      continuar = { rotulo: 'Começar', acao: () => setPasso('nome'), desativado: false };
      break;
    case 'nome':
      fala = 'Como se chama esta casa?';
      corpo = (
        <label className="block space-y-3">
          <span className="block text-sm text-muted">É assim que o seu contacto reconhece a casa nas mensagens.</span>
          <Campo autoFocus value={nomeCasa} onChange={e => setNomeCasa(e.target.value)} placeholder="Casa da D. Maria" maxLength={60} />
        </label>
      );
      continuar = {
        rotulo: 'Continuar',
        acao: () => {
          setSaltouNome(false);
          setPasso('contacto');
        },
        desativado: !nomeCasa.trim(),
      };
      saltar = () => {
        setSaltouNome(true);
        setPasso('contacto');
      };
      break;
    case 'contacto':
      fala = 'Se eu notar algo estranho e não me responder, a quem devo avisar por SMS?';
      corpo = (
        <div className="space-y-6">
          <label className="block space-y-3">
            <span className="block text-sm font-medium">Nome</span>
            <Campo autoFocus value={nome} onChange={e => setNome(e.target.value)} placeholder="Vizinha Ana" maxLength={60} />
          </label>
          <label className="block space-y-3">
            <span className="block text-sm font-medium">Telemóvel</span>
            <Campo type="tel" inputMode="tel" autoComplete="tel" value={telemovel} onChange={e => setTelemovel(e.target.value)} placeholder="912 345 678" />
          </label>
          {contactoIncompleto && <p className="text-sm text-danger">Preencha o nome e o telemóvel.</p>}
        </div>
      );
      continuar = {
        rotulo: 'Continuar',
        acao: () => {
          setSaltouContacto(false);
          setPasso('espera');
        },
        desativado: !contactoPreenchido,
      };
      saltar = () => {
        setSaltouContacto(true);
        guardarESeguir(null);
      };
      break;
    case 'espera':
      fala = `Quanto tempo espero pela sua resposta antes de mandar SMS a ${nome.trim()}?`;
      corpo = <EscolhaGrande rotulo="Tempo de espera" opcoes={ESPERAS} valor={espera} onChange={setEspera} />;
      continuar = { rotulo: guardar.isPending ? 'A guardar…' : 'Continuar', acao: () => guardarESeguir(contacto), desativado: guardar.isPending };
      break;
    case 'calendario':
      fala = erroCalendario
        ? 'Hum, não consegui ligar ao calendário. Quer tentar outra vez?'
        : 'Pode ligar o seu Google Calendar. Assim, férias, rotinas e visitas agendadas são tidas em conta e evitam-se alertas desnecessários.';
      corpo = <PassoCalendario />;
      if (calendario?.configurado && !calendario.ligado) {
        // Por conectar: a ação principal é ir à Google; "Agora não" segue sem ele.
        continuar = { rotulo: 'Conectar calendário', acao: () => ligarCalendario('/boas-vindas'), desativado: false };
        saltar = () => setPasso('fim');
      } else {
        continuar = { rotulo: 'Continuar', acao: () => setPasso('fim'), desativado: !calendario };
      }
      break;
    case 'fim':
      fala = 'Tudo pronto! A partir de agora, eu reparo por si.';
      corpo = <Resumo nomeCasa={nomeGuardado} contacto={contacto} espera={espera} />;
      continuar = { rotulo: 'Começar a usar', acao: sair, desativado: false };
      break;
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pt-[env(safe-area-inset-top)] pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <header className="flex min-h-12 items-center gap-3 py-4">
        {/* Voltar ao passo anterior, com o que já escreveu (para corrigir ou desfazer um "Agora não").
            No primeiro ecrã e no nome da casa não há anterior: a barra ocupa a largura toda. */}
        {voltar && (
          <button
            type="button"
            onClick={() => setPasso(voltar)}
            disabled={guardar.isPending}
            aria-label="Voltar ao passo anterior"
            className="-my-4 -ml-2 flex size-12 items-center justify-center rounded-full text-on-surface"
          >
            <Icone nome="arrow_back" className="size-6" />
          </button>
        )}
        <BarraProgresso valor={feitos} total={ecras.length} rotulo="Progresso da configuração" />
      </header>

      <form
        className="flex flex-1 flex-col"
        onSubmit={e => {
          e.preventDefault();
          if (!continuar.desativado) continuar.acao();
        }}
      >
        <section key={passo} className="ecra-frente flex-1 space-y-8 pt-4">
          <Fala batida={feitos} grande={passo === 'ola' || passo === 'fim'} salta={passo === 'fim'}>
            {fala}
          </Fala>
          {corpo}
        </section>

        <div className="space-y-2 pt-6">
          <Botao type="submit" largo disabled={continuar.desativado} className="botao-3d uppercase tracking-wide">
            {continuar.rotulo}
          </Botao>
          {saltar && (
            <Botao variante="texto" largo onClick={saltar} disabled={guardar.isPending}>
              Agora não
            </Botao>
          )}
        </div>
      </form>
    </div>
  );
}

/**
 * Boas-vindas, estilo Duolingo: o logótipo fala num balão e guia a pessoa por quatro
 * passos (nome da casa, contacto externo, tempo de espera, Google Calendar), com uma barra de
 * progresso em cima. Tudo é opcional ("Agora não") e a seta volta ao passo anterior. Depois de
 * terminar, não volta a aparecer neste telemóvel: o que ficou por definir faz-se nas Definições.
 */
export default function BoasVindas() {
  const { data, isPending, isError, refetch } = useDefinicoes();
  if (isPending) return <div className="mx-auto max-w-md p-5"><EstadoCarregar /></div>;
  if (isError) return <div className="mx-auto max-w-md p-5"><EstadoErro onRetry={refetch} /></div>;
  return <Fluxo inicial={data} />;
}
