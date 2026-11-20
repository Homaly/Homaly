import { api } from '../api';

/** Leva a pessoa à Google para ligar o calendário; a Google devolve-a às Definições (?calendario=ligado|erro). */
export const ligarCalendario = () => window.location.assign(api.urlLigarCalendario());

export const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
