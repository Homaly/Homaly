import type { Anomalia, Definicoes, Evento, MensagemConversa } from '../types/contract';

export interface Api {
  listarAnomaliasAtivas(): Promise<Anomalia[]>;
  obterAnomalia(id: string): Promise<Anomalia>;
  /** Devolve a anomalia atualizada. */
  responderAnomalia(id: string, texto: string): Promise<Anomalia>;
  /** Devolve a anomalia atualizada, depois de a casa confirmar a ação. */
  decidirAcao(id: string, aceitar: boolean): Promise<Anomalia>;
  listarEventos(): Promise<Evento[]>;
  obterConversa(): Promise<MensagemConversa[]>;
  /** Devolve a resposta da casa. */
  enviarMensagem(texto: string): Promise<MensagemConversa>;
  obterDefinicoes(): Promise<Definicoes>;
  guardarDefinicoes(d: Definicoes): Promise<Definicoes>;
}
