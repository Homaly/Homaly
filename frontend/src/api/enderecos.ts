// Onde está o backend. Sem VITE_API_URL, é a máquina de onde veio a página, na porta 8000:
// no portátil dá http://localhost:8000; no telemóvel ligado à mesma rede, o IP do portátil.
// Assim a PWA abre no telemóvel da demo sem configurar o IP. VITE_API_URL e VITE_WS_URL
// sobrepõem-se a isto (por exemplo, com um túnel público).

const PORTA_DO_BACKEND = '8000';

function mesmaMaquina(): string {
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:${PORTA_DO_BACKEND}`;
}

export const API_URL: string = (import.meta.env.VITE_API_URL || mesmaMaquina()).replace(/\/+$/, '');

export const WS_URL: string = import.meta.env.VITE_WS_URL || `${API_URL.replace(/^http/, 'ws')}/ws`;
