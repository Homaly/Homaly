import { useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useCalendario } from '../api/hooks';
import { useToast } from '../context/ToastContext';
import { anonimizarEmail, ligarCalendario } from '../lib/calendario';
import Grupo from './Grupo';
import Linha, { Seta } from './Linha';

/** Mostra "Calendário conectado" ou o erro quando a Google devolve a pessoa (?calendario=ligado|erro). */
function useResultadoDaLigacao() {
  const [params, setParams] = useSearchParams();
  const { showToast } = useToast();
  const mostrado = useRef(false);
  const resultado = params.get('calendario');

  useEffect(() => {
    if (!resultado || mostrado.current) return;
    mostrado.current = true;
    if (resultado === 'ligado') showToast('Calendário conectado', 'success');
    else showToast('Não foi possível conectar o calendário', 'error');
    setParams({}, { replace: true });
  }, [resultado, setParams, showToast]);
}

const TITULO = 'Google Calendar';

/**
 * Definições → Calendário: uma só linha, como as contas nas definições do telemóvel.
 * Conectado, abre o detalhe (`/definicoes/calendario`); por conectar, a linha toda conecta.
 * O e-mail aparece anonimizado (`anonimizarEmail`).
 */
export default function SecaoCalendario() {
  useResultadoDaLigacao();
  const { data, isPending, isError } = useCalendario();

  let linha;
  if (isPending) {
    linha = <Linha icone="calendar" titulo={TITULO} descricao="A carregar…" />;
  } else if (isError) {
    linha = (
      <Linha
        icone="calendar"
        titulo={TITULO}
        descricao={<span className="text-danger">Não foi possível saber se está conectado</span>}
      />
    );
  } else if (data.ligado) {
    linha = (
      <Link to="/definicoes/calendario" className="block">
        <Linha
          icone="calendar"
          titulo={TITULO}
          descricao={
            data.erro ? (
              <span className="text-danger">Não foi possível ler o calendário</span>
            ) : (
              (data.email ? anonimizarEmail(data.email) : 'Conectado')
            )
          }
          fim={<Seta />}
        />
      </Link>
    );
  } else if (data.configurado) {
    linha = (
      <button type="button" onClick={ligarCalendario} className="block w-full">
        <Linha
          icone="calendar"
          titulo={TITULO}
          descricao="Não conectado"
          fim={<span className="font-semibold text-primary-ink">Conectar</span>}
        />
      </button>
    );
  } else {
    linha = <Linha icone="calendar" titulo={TITULO} descricao="Ainda não está configurado nesta casa" />;
  }

  return (
    <Grupo titulo="Calendário" nota="A casa fica a saber das suas férias e rotinas sem ter de as dizer." lista>
      {linha}
    </Grupo>
  );
}
