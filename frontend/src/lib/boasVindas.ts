import type { Definicoes } from '../types/contract';

/** Neste telemóvel, a pessoa já terminou ou saltou as boas-vindas. Fica só no browser. */
const CHAVE = 'homaly-boas-vindas-vistas';

export function boasVindasVistas(): boolean {
  try {
    return localStorage.getItem(CHAVE) === '1';
  } catch {
    return false; // sem armazenamento (janela privada): mostra-se outra vez, não faz mal
  }
}

export function marcarBoasVindasVistas(): void {
  try {
    localStorage.setItem(CHAVE, '1');
  } catch {
    // sem armazenamento: na próxima vez a casa volta a cumprimentar
  }
}

/** A casa ainda não tem nome nem contacto externo: ninguém a configurou. */
export const casaPorConfigurar = (d: Definicoes) => !d.contacto && !d.nomeCasa?.trim();
