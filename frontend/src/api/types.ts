import type { Anomalia, Calendario, Definicoes, Evento, MensagemConversa } from '../types/contract';

/** Ecrãs a que a Google pode devolver a pessoa (o backend só aceita estes). */
export type DestinoCalendario = '/definicoes' | '/boas-vindas';

export interface Api {
  listarAnomaliasAtivas(): Promise<Anomalia[]>;
  obterAnomalia(id: string): Promise<Anomalia>;
  /** Devolve a anomalia atualizada. */
  responderAnomalia(id: string, texto: string): Promise<Anomalia>;
  /** Devolve a anomalia atualizada, depois de a casa confirmar a ação. */
  decidirAcao(id: string, aceitar: boolean): Promise<Anomalia>;
  /** US02: aceita ou recusa a proposta de silêncio. Devolve a anomalia atualizada. */
  decidirSilencio(id: string, aceitar: boolean): Promise<Anomalia>;
  listarEventos(): Promise<Evento[]>;
  obterConversa(): Promise<MensagemConversa[]>;
  /** Devolve a resposta da casa. */
  enviarMensagem(texto: string): Promise<MensagemConversa>;
  obterDefinicoes(): Promise<Definicoes>;
  guardarDefinicoes(d: Definicoes): Promise<Definicoes>;
  obterCalendario(): Promise<Calendario>;
  /** Lê o calendário outra vez. Devolve o estado novo. */
  sincronizarCalendario(): Promise<Calendario>;
  /** Desliga o calendário e apaga o que veio dele. Devolve o estado novo. */
  removerCalendario(): Promise<Calendario>;
  /** Para onde navegar para ligar à Google; volta a `voltar` (por omissão /definicoes) com ?calendario=ligado|erro. */
  urlLigarCalendario(voltar?: DestinoCalendario): string;
}
