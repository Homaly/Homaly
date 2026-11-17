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
  /** US02: a casa propõe deixar de avisar até uma hora; só se aplica depois de aceite. */
  propostaSilencio?: PropostaSilencio;
  /** Como se resolveu (ex.: "a porta fechou às 14:12"); só com estado 'resolvida'. */
  resolucao?: { texto: string; em: string };
}

export interface PropostaSilencio {
  /** Ex.: "Não volto a avisar sobre a porta até ao fim do dia." */
  texto: string;
  /** ISO 8601: até quando a casa deixa de avisar. */
  ate: string;
  estado: 'pendente' | 'aceite' | 'recusada';
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
  contacto: { nome: string; telemovel: string } | null;
  esperaMinutos: number;
  /** Como o contacto externo reconhece a casa na SMS (ex.: "Casa da D. Maria"); sem ele, só "Homaly". */
  nomeCasa?: string;
}

/** Mensagens que o servidor envia pelo WebSocket /ws. */
export type MensagemWs =
  | { tipo: 'anomalia'; anomalia: Anomalia }
  | { tipo: 'evento'; evento: Evento };
