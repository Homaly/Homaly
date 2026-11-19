import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Botao from '../components/Botao';
import Icone from '../components/Icone';
import { useCalendario, useRemoverCalendario } from '../api/hooks';
import { useToast } from '../context/ToastContext';

/** Confirmação antes de remover o calendário: apaga tudo o que a casa sabe por ele. */
export default function RemoverCalendario() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { data } = useCalendario();
  const remover = useRemoverCalendario();
  const quantos = data?.itens.length ?? 0;

  const apagar = () =>
    remover.mutate(undefined, {
      onSuccess: () => {
        showToast('Calendário removido', 'success');
        navigate('/definicoes', { replace: true });
      },
      onError: () => showToast('Não foi possível remover o calendário. Tente de novo.', 'error'),
    });

  return (
    <Layout title="Remover calendário" showBack>
      <div className="flex flex-col items-center gap-4 py-8 text-center">
        <span className="flex size-16 items-center justify-center rounded-full bg-danger/10">
          <Icone nome="calendar" className="size-8 text-danger" />
        </span>
        <h2 className="text-xl font-semibold">Remover o calendário?</h2>
        <p className="text-on-surface-variant">
          Vai perder tudo o que a casa sabe pelo calendário
          {quantos > 0 && <> ({quantos === 1 ? '1 coisa' : `${quantos} coisas`})</>}: férias, rotinas e compromissos.
          O que disse na conversa fica.
        </p>
        {data?.email && <p className="text-sm text-muted">Conta: {data.email}</p>}
      </div>
      <div className="space-y-3">
        <Botao largo variante="contorno" className="border-danger text-danger" disabled={remover.isPending} onClick={apagar}>
          {remover.isPending ? 'A apagar…' : 'Apagar'}
        </Botao>
        <Botao largo variante="secundario" disabled={remover.isPending} onClick={() => navigate('/definicoes')}>
          Cancelar
        </Botao>
      </div>
    </Layout>
  );
}
