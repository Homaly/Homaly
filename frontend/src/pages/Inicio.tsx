import Layout from '../components/Layout';
import AnomaliaCard from '../components/AnomaliaCard';
import { EstadoCarregar, EstadoErro, EstadoVazio } from '../components/Estados';
import { useAnomaliasAtivas } from '../api/hooks';

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
          {data.map(a => (
            <AnomaliaCard key={a.id} anomalia={a} />
          ))}
        </section>
      )}
    </Layout>
  );
}
