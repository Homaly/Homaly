import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

/** O caminho do ecrã anterior; `null` ao abrir a app (aí não há transição: há a animação de arranque). */
let anterior: string | null = null;

/** 0 nos separadores ("/", "/conversa"…), 1 no detalhe ("/anomalias/a1"), 2 abaixo dele. */
const profundidade = (caminho: string) => Math.max(0, caminho.split('/').filter(Boolean).length - 1);

function classeDaTransicao(de: string | null, para: string) {
  if (de === null || de === para) return '';
  const a = profundidade(de);
  const b = profundidade(para);
  if (b > a) return 'ecra-frente';
  if (b < a) return 'ecra-tras';
  return 'ecra-separador';
}

/**
 * A classe da animação de entrada do ecrã, pela hierarquia e não pelo histórico: mais fundo entra
 * pela direita, mais acima pela esquerda (mesmo com "Voltar ao início", que avança no histórico),
 * e entre separadores aparece e cresce um pouco. Calcula-se uma vez, quando o ecrã monta.
 */
export function useTransicaoDeEcra() {
  const { pathname } = useLocation();
  const [classe] = useState(() => classeDaTransicao(anterior, pathname));
  useEffect(() => {
    anterior = pathname;
  }, [pathname]);
  return classe;
}
