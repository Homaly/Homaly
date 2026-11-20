import Layout from '../components/Layout';
import AnomaliaCard, { AnomaliaLinha, CLASSES } from '../components/AnomaliaCard';
import { EstadoCarregar, EstadoErro, EstadoVazio } from '../components/Estados';
import { useAnomaliasAtivas } from '../api/hooks';
import type { Anomalia } from '../types/contract';

/** Mais urgentes primeiro; na mesma classe, a mais recente primeiro. */
const porUrgencia = (a: Anomalia, b: Anomalia) =>
  CLASSES[a.classe].urgencia - CLASSES[b.classe].urgencia ||
  new Date(b.detetadaEm).getTime() - new Date(a.detetadaEm).getTime();

/**
 * Título de grupo pequeno, como os das Definições (o título grande do ecrã é o "Homaly"), com o
 * número de avisos do grupo: "Urgente (2)".
 */
function TituloGrupo({ children, numero }: { children: string; numero: number }) {
  return (
    <h2 className="px-1 text-sm font-semibold text-on-surface-variant">
      {children}
      <span className="font-medium text-muted"> ({numero})</span>
    </h2>
  );
}

export default function Inicio() {
  const { data, isPending, isError, refetch } = useAnomaliasAtivas();
  // Por urgência e não só por hora: um alerta de segurança não fica abaixo de uma luz acesa.
  const ordenadas = [...(data ?? [])].sort(porUrgencia);
  const urgentes = ordenadas.filter(a => CLASSES[a.classe].urgente);
  const outras = ordenadas.filter(a => !CLASSES[a.classe].urgente);

  return (
    <Layout title="Homaly">
      {isPending ? (
        <EstadoCarregar />
      ) : isError ? (
        <EstadoErro onRetry={refetch} />
      ) : data.length === 0 ? (
        <EstadoVazio
          icon="check_circle"
          texto="Está tudo normal"
          descricao="A casa avisa quando alguma coisa fugir ao habitual."
          tudoBem
        />
      ) : (
        // A hierarquia vem do tamanho e do agrupamento, não da cor: os urgentes (os que chegam ao
        // contacto externo) têm cartão próprio; os outros ficam em linhas, num só cartão.
        // Entram em cascata (ver .cascata em index.css): os grupos e, dentro do Urgente, os cartões.
        <div className="cascata space-y-6">
          {urgentes.length > 0 && (
            <section className="space-y-2">
              <TituloGrupo numero={urgentes.length}>Urgente</TituloGrupo>
              <div className="cascata space-y-3">
                {urgentes.map(a => (
                  <AnomaliaCard key={a.id} anomalia={a} />
                ))}
              </div>
            </section>
          )}
          {outras.length > 0 && (
            <section className="space-y-2">
              <TituloGrupo numero={outras.length}>{urgentes.length > 0 ? 'Outros avisos' : 'Avisos'}</TituloGrupo>
              <div className="divide-y divide-outline-variant rounded-2xl bg-surface-container px-4">
                {outras.map(a => (
                  <AnomaliaLinha key={a.id} anomalia={a} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </Layout>
  );
}
