import type { Anomalia, Calendario, Definicoes, Evento, MensagemConversa } from '../types/contract';
import { apiFetch } from './client';
import { API_URL } from './enderecos';
import type { Api } from './types';

const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

export const realApi: Api = {
  listarAnomaliasAtivas: () => apiFetch<Anomalia[]>('/anomalias?estado=ativa'),
  obterAnomalia: id => apiFetch<Anomalia>(`/anomalias/${id}`),
  responderAnomalia: (id, texto) => apiFetch<Anomalia>(`/anomalias/${id}/resposta`, post({ texto })),
  decidirAcao: (id, aceitar) => apiFetch<Anomalia>(`/anomalias/${id}/acao`, post({ aceitar })),
  decidirSilencio: (id, aceitar) => apiFetch<Anomalia>(`/anomalias/${id}/silencio`, post({ aceitar })),
  listarEventos: () => apiFetch<Evento[]>('/eventos'),
  obterConversa: () => apiFetch<MensagemConversa[]>('/conversa'),
  enviarMensagem: texto => apiFetch<MensagemConversa>('/conversa', post({ texto })),
  obterDefinicoes: () => apiFetch<Definicoes>('/definicoes'),
  guardarDefinicoes: d =>
    apiFetch<Definicoes>('/definicoes', { method: 'PUT', body: JSON.stringify(d) }),
  obterCalendario: () => apiFetch<Calendario>('/calendario'),
  sincronizarCalendario: () => apiFetch<Calendario>('/calendario/sincronizar', { method: 'POST' }),
  removerCalendario: () => apiFetch<Calendario>('/calendario', { method: 'DELETE' }),
  urlLigarCalendario: (voltar = '/definicoes') =>
    `${API_URL}/calendario/google/ligar?voltar=${encodeURIComponent(voltar)}`,
};
