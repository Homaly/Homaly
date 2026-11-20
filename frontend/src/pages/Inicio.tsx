import Layout from '../components/Layout';
import AnomaliaCard, { CLASSES } from '../components/AnomaliaCard';
import { EstadoCarregar, EstadoErro, EstadoVazio } from '../components/Estados';
import { useAnomaliasAtivas } from '../api/hooks';
import type { Anomalia } from '../types/contract';

/** Mais urgentes primeiro; na mesma classe, a mais recente primeiro. */
const porUrgencia = (a: Anomalia, b: Anomalia) =>
  CLASSES[a.classe].urgencia - CLASSES[b.classe].urgencia ||
  new Date(b.detetadaEm).getTime() - new Date(a.detetadaEm).getTime();

export default function Inicio() {
  const { data, isPending, isError, refetch } = useAnomaliasAtivas();

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
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">
            {data.length === 1 ? '1 coisa por responder' : `${data.length} coisas por responder`}
          </h2>
          {/* Por urgência e não só por hora: um alerta de segurança não fica abaixo de uma luz acesa. */}
          {[...data].sort(porUrgencia).map(a => (
            <AnomaliaCard key={a.id} anomalia={a} />
          ))}
        </section>
      )}
    </Layout>
  );
}
