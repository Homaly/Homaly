import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { pt } from 'date-fns/locale';
import type { Anomalia, Classe } from '../types/contract';
import { cn } from '../lib/cn';

export const CLASSES: Record<Classe, { nome: string; icon: string; cor: string }> = {
  seguranca: { nome: 'Segurança', icon: 'shield', cor: 'text-red-500 bg-red-500/10' },
  bem_estar: { nome: 'Bem-estar e rotina', icon: 'favorite', cor: 'text-accent-orange bg-accent-orange/10' },
  saude_conforto: { nome: 'Saúde e conforto', icon: 'thermostat', cor: 'text-primary bg-primary/10' },
  eficiencia: { nome: 'Eficiência energética', icon: 'bolt', cor: 'text-accent-green bg-accent-green/10' },
};

export function ClasseBadge({ classe }: { classe: Classe }) {
  const c = CLASSES[classe];
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold', c.cor)}>
      <span className="material-symbols-outlined text-sm">{c.icon}</span>
      {c.nome}
    </span>
  );
}

export default function AnomaliaCard({ anomalia }: { anomalia: Anomalia }) {
  return (
    <Link
      to={`/anomalias/${anomalia.id}`}
      className="block rounded-xl border border-slate-200 dark:border-primary/10 bg-white dark:bg-card-dark p-4 active:scale-[0.99] transition-transform"
    >
      <div className="flex items-center justify-between gap-2">
        <ClasseBadge classe={anomalia.classe} />
        <span className="text-xs text-slate-500 dark:text-slate-400 shrink-0">
          {formatDistanceToNow(new Date(anomalia.detetadaEm), { locale: pt, addSuffix: true })}
        </span>
      </div>
      <p className="mt-2 font-semibold">{anomalia.titulo}</p>
      {anomalia.acaoProposta && (
        <p className="mt-1 text-xs text-primary">Ação proposta: {anomalia.acaoProposta.descricao}</p>
      )}
    </Link>
  );
}
