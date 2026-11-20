import { Link } from 'react-router-dom';
import type { Anomalia, Classe } from '../types/contract';
import Icone, { type NomeIcone } from './Icone';

/**
 * As classes distinguem-se pelo ícone e pelo nome, não pela cor: a cor fica para o estado (erro, atenção, resolvido).
 * `urgencia` ordena o Início (1 primeiro). `urgente`: segurança e bem-estar, as que chegam ao contacto externo;
 * no Início têm cartão próprio, as outras ficam em linhas.
 */
export const CLASSES: Record<Classe, { nome: string; icon: NomeIcone; urgencia: number; urgente: boolean }> = {
  seguranca: { nome: 'Segurança', icon: 'shield', urgencia: 1, urgente: true },
  bem_estar: { nome: 'Bem-estar e rotina', icon: 'favorite', urgencia: 2, urgente: true },
  saude_conforto: { nome: 'Saúde e conforto', icon: 'thermostat', urgencia: 3, urgente: false },
  eficiencia: { nome: 'Eficiência energética', icon: 'bolt', urgencia: 4, urgente: false },
};

export function ClasseBadge({ classe }: { classe: Classe }) {
  const c = CLASSES[classe];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-tonal px-2.5 py-1 text-xs font-semibold text-on-surface-variant">
      <Icone nome={c.icon} className="size-3.5" />
      {c.nome}
    </span>
  );
}

/** "agora", "há 5 min", "há 9 h", "há 2 dias": curto, para não disputar o lugar ao título. */
function haQuanto(iso: string) {
  const min = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  if (min < 1) return 'agora';
  if (min < 60) return `há ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `há ${h} h`;
  const d = Math.floor(h / 24);
  return `há ${d} ${d === 1 ? 'dia' : 'dias'}`;
}

/** Ícone da classe num círculo, à esquerda: a classe lê-se de relance sem passar à frente do título. */
function IconeClasse({ classe }: { classe: Classe }) {
  return (
    <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-tonal text-on-surface">
      <Icone nome={CLASSES[classe].icon} className="size-5" />
    </span>
  );
}

/** Classe e hora numa linha discreta, por baixo do resto. */
function Meta({ anomalia }: { anomalia: Anomalia }) {
  return (
    <p className="text-xs text-muted">
      {CLASSES[anomalia.classe].nome} · {haQuanto(anomalia.detetadaEm)}
    </p>
  );
}

function AcaoProposta({ anomalia }: { anomalia: Anomalia }) {
  if (!anomalia.acaoProposta) return null;
  return <p className="text-sm text-primary-ink">Ação proposta: {anomalia.acaoProposta.descricao}</p>;
}

/**
 * Aviso urgente: cartão próprio, título maior e o começo da explicação, para decidir sem abrir.
 * Ordem de leitura: o quê (título), porquê (explicação), e só depois a classe e a hora.
 */
export default function AnomaliaCard({ anomalia }: { anomalia: Anomalia }) {
  return (
    <Link
      to={`/anomalias/${anomalia.id}`}
      className="flex gap-3 rounded-2xl bg-surface-container p-4 transition-transform motion-safe:active:scale-[0.99]"
    >
      <IconeClasse classe={anomalia.classe} />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-lg font-semibold leading-snug">{anomalia.titulo}</p>
        <p className="line-clamp-2 text-sm text-on-surface-variant">{anomalia.explicacao}</p>
        <AcaoProposta anomalia={anomalia} />
        <div className="pt-1">
          <Meta anomalia={anomalia} />
        </div>
      </div>
    </Link>
  );
}

/** Aviso que não é urgente: linha compacta, dentro de um só cartão com as outras (como no Histórico). */
export function AnomaliaLinha({ anomalia }: { anomalia: Anomalia }) {
  return (
    <Link to={`/anomalias/${anomalia.id}`} className="flex min-h-14 gap-3 py-3">
      <IconeClasse classe={anomalia.classe} />
      <div className="min-w-0 flex-1 space-y-0.5">
        <p className="font-medium leading-snug">{anomalia.titulo}</p>
        <AcaoProposta anomalia={anomalia} />
        <Meta anomalia={anomalia} />
      </div>
    </Link>
  );
}
