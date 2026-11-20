import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { pt } from 'date-fns/locale';
import type { Anomalia, Classe } from '../types/contract';
import Icone, { type NomeIcone } from './Icone';

/**
 * As classes distinguem-se pelo ícone e pelo nome, não pela cor: a cor fica para o estado (erro, atenção, resolvido).
 * `urgencia` ordena o Início (1 primeiro): segurança e bem-estar são as que chegam ao contacto externo.
 */
export const CLASSES: Record<Classe, { nome: string; icon: NomeIcone; urgencia: number }> = {
  seguranca: { nome: 'Segurança', icon: 'shield', urgencia: 1 },
  bem_estar: { nome: 'Bem-estar e rotina', icon: 'favorite', urgencia: 2 },
  saude_conforto: { nome: 'Saúde e conforto', icon: 'thermostat', urgencia: 3 },
  eficiencia: { nome: 'Eficiência energética', icon: 'bolt', urgencia: 4 },
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

export default function AnomaliaCard({ anomalia }: { anomalia: Anomalia }) {
  return (
    <Link
      to={`/anomalias/${anomalia.id}`}
      className="block rounded-2xl bg-surface-container p-4 transition-transform motion-safe:active:scale-[0.99]"
    >
      <div className="flex items-center justify-between gap-2">
        <ClasseBadge classe={anomalia.classe} />
        <span className="shrink-0 text-xs text-muted">
          {formatDistanceToNow(new Date(anomalia.detetadaEm), { locale: pt, addSuffix: true })}
        </span>
      </div>
      <p className="mt-3 font-semibold">{anomalia.titulo}</p>
      {anomalia.acaoProposta && (
        <p className="mt-1 text-sm text-primary-ink">Ação proposta: {anomalia.acaoProposta.descricao}</p>
      )}
    </Link>
  );
}
