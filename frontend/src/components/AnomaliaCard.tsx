import { Link } from 'react-router-dom';
import { cn } from '../lib/cn';
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

/**
 * Ícone da classe num círculo, à esquerda: a classe lê-se de relance sem passar à frente do título.
 * Nos urgentes (os que chegam ao contacto externo) é laranja, a cor de "pede atenção": a cor diz a
 * urgência, não a classe, por isso segurança e bem-estar têm a mesma. Os outros ficam neutros.
 */
function IconeClasse({ classe }: { classe: Classe }) {
  return (
    <span
      className={cn(
        'flex size-10 shrink-0 items-center justify-center rounded-full',
        CLASSES[classe].urgente ? 'bg-accent-orange/15 text-accent-orange' : 'bg-surface-tonal text-on-surface'
      )}
    >
      <Icone nome={CLASSES[classe].icon} className="size-5" />
    </span>
  );
}

/**
 * Cabeçalho pequeno por cima do título, como o de uma notificação no telemóvel: a classe e a hora.
 * Em cima, e não por baixo, para não ficar colado à explicação, que também é cinzenta.
 * "Avisou" diz de que hora se trata: o título pode trazer outro tempo ("Porta da rua aberta há 7 minutos").
 */
function Cabecalho({ anomalia }: { anomalia: Anomalia }) {
  return (
    <p className="text-xs leading-4 text-muted">
      <span className="font-semibold text-on-surface-variant">{CLASSES[anomalia.classe].nome}</span>
      {' · '}avisou {haQuanto(anomalia.detetadaEm)}
    </p>
  );
}

function AcaoProposta({ anomalia, className }: { anomalia: Anomalia; className?: string }) {
  if (!anomalia.acaoProposta) return null;
  return (
    <p className={cn('text-sm text-primary-ink', className)}>Ação proposta: {anomalia.acaoProposta.descricao}</p>
  );
}

/**
 * Aviso urgente: cartão próprio, título maior e o começo da explicação, para decidir sem abrir.
 * Três níveis: cabeçalho pequeno (classe e hora), título forte, explicação em texto de apoio.
 */
export default function AnomaliaCard({ anomalia }: { anomalia: Anomalia }) {
  return (
    <Link
      to={`/anomalias/${anomalia.id}`}
      className="flex gap-3 rounded-2xl bg-surface-container p-4 transition-transform motion-safe:active:scale-[0.99]"
    >
      <IconeClasse classe={anomalia.classe} />
      <div className="min-w-0 flex-1">
        <Cabecalho anomalia={anomalia} />
        <p className="mt-1 text-lg font-semibold leading-snug">{anomalia.titulo}</p>
        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-on-surface-variant">{anomalia.explicacao}</p>
        <AcaoProposta anomalia={anomalia} className="mt-1.5" />
      </div>
    </Link>
  );
}

/** Aviso que não é urgente: linha compacta, dentro de um só cartão com as outras (como no Histórico). */
export function AnomaliaLinha({ anomalia }: { anomalia: Anomalia }) {
  return (
    <Link to={`/anomalias/${anomalia.id}`} className="flex min-h-14 gap-3 py-3">
      <IconeClasse classe={anomalia.classe} />
      <div className="min-w-0 flex-1">
        <Cabecalho anomalia={anomalia} />
        <p className="mt-0.5 font-medium leading-snug">{anomalia.titulo}</p>
        <AcaoProposta anomalia={anomalia} className="mt-0.5" />
      </div>
    </Link>
  );
}
