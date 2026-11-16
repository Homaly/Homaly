// Contrato com o backend. Fonte: docs/frontend-design.md.
// Alterar aqui obriga a alterar o backend (e vice-versa).

export type Classe = 'seguranca' | 'bem_estar' | 'saude_conforto' | 'eficiencia';

export interface Anomalia {
  id: string;
  classe: Classe;
  titulo: string;
  /** Texto da IA: o que aconteceu e o que é habitual. */
  explicacao: string;
  /** ISO 8601 */
  detetadaEm: string;
  estado: 'ativa' | 'resolvida';
  acaoProposta?: { descricao: string };
  imagemUrl?: string;
  resposta?: { texto: string; em: string };
}

export interface Evento {
  id: string;
  em: string;
  dispositivo: string;
  descricao: string;
  anomaliaId?: string;
}

export interface MensagemConversa {
  id: string;
  autor: 'pessoa' | 'casa';
  texto: string;
  em: string;
}

export interface Definicoes {
  contacto: { nome: string; telegram: string } | null;
  esperaMinutos: number;
}

/** Mensagens que o servidor envia pelo WebSocket /ws. */
export type MensagemWs =
  | { tipo: 'anomalia'; anomalia: Anomalia }
  | { tipo: 'evento'; evento: Evento };
