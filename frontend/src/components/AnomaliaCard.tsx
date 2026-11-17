import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { pt } from 'date-fns/locale';
import type { Anomalia, Classe } from '../types/contract';
import Icone from './Icone';

/** As classes distinguem-se pelo ícone e pelo nome, não pela cor: a cor fica para o estado (erro, atenção, resolvido). */
export const CLASSES: Record<Classe, { nome: string; icon: string }> = {
  seguranca: { nome: 'Segurança', icon: 'shield' },
  bem_estar: { nome: 'Bem-estar e rotina', icon: 'favorite' },
  saude_conforto: { nome: 'Saúde e conforto', icon: 'thermostat' },
  eficiencia: { nome: 'Eficiência energética', icon: 'bolt' },
};

export function ClasseBadge({ classe }: { classe: Classe }) {
  const c = CLASSES[classe];
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-surface-tonal px-2 py-0.5 text-xs font-semibold text-on-surface-variant">
      <Icone nome={c.icon} className="text-sm" />
      {c.nome}
    </span>
  );
}

export default function AnomaliaCard({ anomalia }: { anomalia: Anomalia }) {
  return (
    <Link
      to={`/anomalias/${anomalia.id}`}
      className="block rounded-xl border border-outline-variant bg-surface-container p-4 transition-transform motion-safe:active:scale-[0.99]"
    >
      <div className="flex items-center justify-between gap-2">
        <ClasseBadge classe={anomalia.classe} />
        <span className="shrink-0 text-xs text-muted">
          {formatDistanceToNow(new Date(anomalia.detetadaEm), { locale: pt, addSuffix: true })}
        </span>
      </div>
      <p className="mt-2 font-semibold">{anomalia.titulo}</p>
      {anomalia.acaoProposta && (
        <p className="mt-1 text-xs text-primary-ink">Ação proposta: {anomalia.acaoProposta.descricao}</p>
      )}
    </Link>
  );
}
