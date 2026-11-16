// Dados falsos fixos, só para popular os ecrãs enquanto o backend não responde.
// Ativos com VITE_USE_MOCKS=true. As escritas alteram os dados em memória.
import type { Anomalia, Definicoes, Evento, MensagemConversa } from '../types/contract';
import type { Api } from './types';

const agora = Date.now();
const haMin = (min: number) => new Date(agora - min * 60_000).toISOString();

const IMAGEM_VEICULO =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180"><rect width="320" height="180" fill="#1a2e35"/>' +
      '<text x="160" y="95" fill="#06bcf9" font-family="sans-serif" font-size="16" text-anchor="middle">Imagem da câmara (mock)</text></svg>'
  );

let anomalias: Anomalia[] = [
  {
    id: 'a1',
    classe: 'seguranca',
    titulo: 'Porta da rua aberta há 7 minutos',
    explicacao:
      'A porta da rua abriu às ' +
      new Date(agora - 7 * 60_000).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' }) +
      ' e ainda não fechou. Normalmente fecha em menos de um minuto.',
    detetadaEm: haMin(2),
    estado: 'ativa',
  },
  {
    id: 'a2',
    classe: 'eficiencia',
    titulo: 'Luz da sala acesa há 5 horas',
    explicacao:
      'A luz da sala está acesa há cinco horas e a porta abriu e fechou depois disso. Ainda estão a usar?',
    detetadaEm: haMin(15),
    estado: 'ativa',
    acaoProposta: { descricao: 'Apagar a luz da sala' },
  },
  {
    id: 'a3',
    classe: 'seguranca',
    titulo: 'Veículo desconhecido na entrada',
    explicacao:
      'Um carro cinzento está parado na entrada de veículos há 3 minutos e não corresponde a nenhum dos veículos conhecidos.',
    detetadaEm: haMin(40),
    estado: 'ativa',
    imagemUrl: IMAGEM_VEICULO,
  },
];

const eventos: Evento[] = [
  { id: 'e1', em: haMin(7), dispositivo: 'Porta da rua', descricao: 'Abriu', anomaliaId: 'a1' },
  { id: 'e2', em: haMin(40), dispositivo: 'Câmara da entrada', descricao: 'Veículo detetado', anomaliaId: 'a3' },
  { id: 'e3', em: haMin(90), dispositivo: 'Sala', descricao: '19,5 °C' },
  { id: 'e4', em: haMin(180), dispositivo: 'Porta da rua', descricao: 'Fechou' },
  { id: 'e5', em: haMin(181), dispositivo: 'Porta da rua', descricao: 'Abriu' },
  { id: 'e6', em: haMin(300), dispositivo: 'Luz da sala', descricao: 'Acendeu', anomaliaId: 'a2' },
  { id: 'e7', em: haMin(60 * 26), dispositivo: 'Sala', descricao: '20,1 °C' },
];

let conversa: MensagemConversa[] = [
  { id: 'm1', autor: 'pessoa', texto: 'A empregada vem às terças à tarde.', em: haMin(60 * 24) },
  {
    id: 'm2',
    autor: 'casa',
    texto: 'Percebido: às terças à tarde não vou estranhar a porta a abrir.',
    em: haMin(60 * 24 - 1),
  },
];

let definicoes: Definicoes = { contacto: null, esperaMinutos: 5 };

const espera = <T,>(valor: T) => new Promise<T>(r => setTimeout(() => r(structuredClone(valor)), 300));

function atualizar(id: string, mudar: (a: Anomalia) => Anomalia): Promise<Anomalia> {
  const a = anomalias.find(x => x.id === id);
  if (!a) return Promise.reject(new Error('Anomalia não encontrada'));
  const nova = mudar(a);
  anomalias = anomalias.map(x => (x.id === id ? nova : x));
  return espera(nova);
}

export const mockApi: Api = {
  listarAnomaliasAtivas: () => espera(anomalias.filter(a => a.estado === 'ativa')),
  obterAnomalia: id => {
    const a = anomalias.find(x => x.id === id);
    return a ? espera(a) : Promise.reject(new Error('Anomalia não encontrada'));
  },
  responderAnomalia: (id, texto) =>
    atualizar(id, a => ({ ...a, estado: 'resolvida', resposta: { texto, em: new Date().toISOString() } })),
  decidirAcao: (id, aceitar) =>
    atualizar(id, a => ({
      ...a,
      estado: 'resolvida',
      resposta: {
        texto: aceitar ? `Ação feita: ${a.acaoProposta?.descricao}` : 'Ação recusada',
        em: new Date().toISOString(),
      },
    })),
  listarEventos: () => espera(eventos),
  obterConversa: () => espera(conversa),
  enviarMensagem: texto => {
    const em = new Date().toISOString();
    const resposta: MensagemConversa = {
      id: crypto.randomUUID(),
      autor: 'casa',
      texto: `(mock) Registei: "${texto}"`,
      em,
    };
    conversa = [...conversa, { id: crypto.randomUUID(), autor: 'pessoa', texto, em }, resposta];
    return espera(resposta);
  },
  obterDefinicoes: () => espera(definicoes),
  guardarDefinicoes: d => {
    definicoes = d;
    return espera(definicoes);
  },
};
