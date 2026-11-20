import { Navigate } from 'react-router-dom';
import { useDefinicoes } from '../api/hooks';
import { boasVindasVistas, casaPorConfigurar } from '../lib/boasVindas';

/**
 * No Início: se a casa ainda não foi configurada (sem nome nem contacto) e este telemóvel ainda
 * não viu as boas-vindas, leva a pessoa para lá. Só no Início, para não desviar um link de aviso.
 */
export default function IrParaBoasVindas() {
  const { data } = useDefinicoes();
  if (!data || boasVindasVistas() || !casaPorConfigurar(data)) return null;
  return <Navigate to="/boas-vindas" replace />;
}
