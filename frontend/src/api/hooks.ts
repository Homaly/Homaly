import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Anomalia, Definicoes, MensagemConversa } from '../types/contract';
import { api } from '.';

export const chaves = {
  anomaliasAtivas: ['anomalias', 'ativas'] as const,
  anomalia: (id: string) => ['anomalia', id] as const,
  eventos: ['eventos'] as const,
  conversa: ['conversa'] as const,
  definicoes: ['definicoes'] as const,
};

export const useAnomaliasAtivas = () =>
  useQuery({ queryKey: chaves.anomaliasAtivas, queryFn: api.listarAnomaliasAtivas });

export const useAnomalia = (id: string) =>
  useQuery({ queryKey: chaves.anomalia(id), queryFn: () => api.obterAnomalia(id) });

export const useEventos = () => useQuery({ queryKey: chaves.eventos, queryFn: api.listarEventos });

export const useConversa = () => useQuery({ queryKey: chaves.conversa, queryFn: api.obterConversa });

export const useDefinicoes = () =>
  useQuery({ queryKey: chaves.definicoes, queryFn: api.obterDefinicoes });

/** Guarda a anomalia atualizada na cache do detalhe e na lista de ativas. */
export function guardarAnomaliaNaCache(qc: ReturnType<typeof useQueryClient>, a: Anomalia) {
  qc.setQueryData(chaves.anomalia(a.id), a);
  qc.setQueryData<Anomalia[]>(chaves.anomaliasAtivas, lista => {
    if (!lista) return lista;
    const semEla = lista.filter(x => x.id !== a.id);
    return a.estado === 'ativa' ? [a, ...semEla] : semEla;
  });
}

export function useResponderAnomalia(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (texto: string) => api.responderAnomalia(id, texto),
    onSuccess: a => guardarAnomaliaNaCache(qc, a),
  });
}

export function useDecidirAcao(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (aceitar: boolean) => api.decidirAcao(id, aceitar),
    onSuccess: a => guardarAnomaliaNaCache(qc, a),
  });
}

export function useEnviarMensagem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (texto: string) => api.enviarMensagem(texto),
    onMutate: texto => {
      const minha: MensagemConversa = {
        id: crypto.randomUUID(),
        autor: 'pessoa',
        texto,
        em: new Date().toISOString(),
      };
      qc.setQueryData<MensagemConversa[]>(chaves.conversa, l => [...(l ?? []), minha]);
    },
    onSuccess: resposta =>
      qc.setQueryData<MensagemConversa[]>(chaves.conversa, l => [...(l ?? []), resposta]),
    onError: () => qc.invalidateQueries({ queryKey: chaves.conversa }),
  });
}

export function useGuardarDefinicoes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (d: Definicoes) => api.guardarDefinicoes(d),
    onSuccess: d => qc.setQueryData(chaves.definicoes, d),
  });
}
