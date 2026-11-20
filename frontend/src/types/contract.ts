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
  /** Minutos antes de avisar o contacto externo (0 a 1440); aceita frações: 0.5 são 30 segundos. */
  esperaMinutos: number;
  /** Como o contacto externo reconhece a casa na SMS (ex.: "Casa da D. Maria"); sem ele, só "Homaly". */
  nomeCasa?: string;
}

/** O Google Calendar ligado à casa (GET /calendario). */
export interface Calendario {
  /** A app está registada na Google (GOOGLE_CLIENT_ID no .env do backend). */
  configurado: boolean;
  ligado: boolean;
  email: string | null;
  /** ISO 8601: a última leitura que correu bem. */
  lidoEm: string | null;
  /** O que correu mal na última leitura, já em português. */
  erro: string | null;
  /** O que a casa sabe pelo calendário, já escrito (ex.: "a empregada vem: terça-feira, às 10:00"). */
  itens: { tipo: 'ferias' | 'rotina' | 'compromisso'; texto: string }[];
}

/** US13: um veículo que a casa conhece (GET/POST /veiculos, DELETE /veiculos/{id}). */
export interface Veiculo {
  id: string;
  /** Ex.: "Peugeot 206 azul", ou o nome dado ("o carro do meu irmão"). */
  descricao: string;
  tipo?: string;
  cor?: string;
  /** Marca e modelo, se o modelo de visão os reconheceu. */
  marca?: string;
  /** Como se lê, ex.: "35-19-TA". */
  matricula?: string;
  /** ISO 8601. */
  criadoEm: string;
}

/** Mensagens que o servidor envia pelo WebSocket /ws. */
export type MensagemWs =
  | { tipo: 'anomalia'; anomalia: Anomalia }
  | { tipo: 'evento'; evento: Evento };
