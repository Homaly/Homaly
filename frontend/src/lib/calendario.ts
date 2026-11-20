import { api } from '../api';

/** Leva a pessoa à Google para conectar o calendário; a Google devolve-a às Definições (?calendario=ligado|erro). */
export const ligarCalendario = () => window.location.assign(api.urlLigarCalendario());

/** Tamanho do nome (antes do @) depois de anonimizado: igual para todos, para não dizer quão longo é. */
const TAMANHO_NOME = 8;

/**
 * O e-mail sem o mostrar todo: antes do @, os 2 primeiros e os 2 últimos caracteres com asteriscos
 * no meio, sempre com 8 de tamanho ("an****va@gmail.com"); o que vem depois do @ fica como está.
 * Nomes curtos mostram menos (1 e 1 até 4 caracteres, só o 1.º até 2), para não ficarem inteiros à vista.
 */
export function anonimizarEmail(email: string): string {
  const arroba = email.lastIndexOf('@');
  const nome = arroba < 0 ? email : email.slice(0, arroba);
  const dominio = arroba < 0 ? '' : email.slice(arroba);
  const [inicio, fim] = nome.length >= 5 ? [2, 2] : nome.length >= 3 ? [1, 1] : [Math.min(1, nome.length), 0];
  return nome.slice(0, inicio) + '*'.repeat(TAMANHO_NOME - inicio - fim) + nome.slice(nome.length - fim) + dominio;
}

export const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
