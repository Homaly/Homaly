import { useCallback, useEffect, useRef, useState } from 'react';

// O que a app usa da Web Speech API. Os tipos não vêm em todas as versões do lib.dom, por isso ficam aqui.
interface ResultadoReconhecimento {
  readonly isFinal: boolean;
  readonly 0: { readonly transcript: string };
}
interface Reconhecedor {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((e: { readonly results: ArrayLike<ResultadoReconhecimento> }) => void) | null;
  onerror: ((e: { readonly error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type ConstrutorReconhecedor = new () => Reconhecedor;

function construtor(): ConstrutorReconhecedor | undefined {
  const w = window as unknown as {
    SpeechRecognition?: ConstrutorReconhecedor;
    webkitSpeechRecognition?: ConstrutorReconhecedor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

export type ErroDitado = 'sem-permissao' | 'sem-som' | 'sem-rede' | 'sem-microfone' | 'outro';

const ERROS: Record<string, ErroDitado> = {
  'not-allowed': 'sem-permissao',
  'service-not-allowed': 'sem-permissao',
  'no-speech': 'sem-som',
  network: 'sem-rede',
  'audio-capture': 'sem-microfone',
};

/**
 * Ditado pela Web Speech API do browser, em português de Portugal.
 * `onTexto` recebe tudo o que foi ouvido até agora; vai mudando enquanto a pessoa fala.
 * Para sozinho quando a pessoa se cala. No Firefox, ou fora de HTTPS e de localhost, `suportado` é false.
 */
export function useDitado(onTexto: (ouvido: string) => void, onErro: (erro: ErroDitado) => void) {
  const [suportado] = useState(() => !!construtor() && window.isSecureContext);
  const [aOuvir, setAOuvir] = useState(false);
  const rec = useRef<Reconhecedor | null>(null);
  // Os callbacks mudam a cada render; o reconhecedor chama sempre os mais recentes.
  const cbTexto = useRef(onTexto);
  const cbErro = useRef(onErro);
  useEffect(() => {
    cbTexto.current = onTexto;
    cbErro.current = onErro;
  });

  const comecar = useCallback(() => {
    const C = construtor();
    if (!C || rec.current) return;
    const r = new C();
    r.lang = 'pt-PT';
    r.interimResults = true;
    r.continuous = false;
    r.maxAlternatives = 1;
    r.onresult = e => {
      let ouvido = '';
      for (let i = 0; i < e.results.length; i++) ouvido += e.results[i][0].transcript;
      cbTexto.current(ouvido);
    };
    r.onerror = e => {
      if (e.error !== 'aborted') cbErro.current(ERROS[e.error] ?? 'outro');
    };
    r.onend = () => {
      rec.current = null;
      setAOuvir(false);
    };
    rec.current = r;
    try {
      r.start();
      setAOuvir(true);
    } catch {
      rec.current = null;
      cbErro.current('outro');
    }
  }, []);

  /** Para de ouvir; o que já foi dito ainda chega. */
  const parar = useCallback(() => rec.current?.stop(), []);

  /** Para e deita fora o que ainda não chegou (ao enviar a mensagem a meio do ditado). */
  const cancelar = useCallback(() => {
    const r = rec.current;
    if (!r) return;
    r.onresult = null;
    r.abort();
  }, []);

  useEffect(() => () => rec.current?.abort(), []);

  return { suportado, aOuvir, comecar, parar, cancelar };
}
