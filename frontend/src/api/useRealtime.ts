import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { MensagemWs } from '../types/contract';
import { USE_MOCKS } from '.';
import { chaves, guardarAnomaliaNaCache } from './hooks';

const WS_URL = import.meta.env.VITE_WS_URL as string | undefined;

/** Liga ao WebSocket do backend e mantém as caches atualizadas. Devolve se está ligado. */
export function useRealtime(): boolean {
  const qc = useQueryClient();
  const ativo = !USE_MOCKS && !!WS_URL;
  const [ligado, setLigado] = useState(false);

  useEffect(() => {
    if (!ativo) return;
    let ws: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let tentativas = 0;
    let fechado = false;

    const ligar = () => {
      ws = new WebSocket(WS_URL!);
      ws.onopen = () => {
        tentativas = 0;
        setLigado(true);
        // Pode ter-se perdido algo enquanto estava em baixo.
        qc.invalidateQueries();
      };
      ws.onmessage = e => {
        const msg = JSON.parse(e.data) as MensagemWs;
        if (msg.tipo === 'anomalia') guardarAnomaliaNaCache(qc, msg.anomalia);
        else if (msg.tipo === 'evento') qc.invalidateQueries({ queryKey: chaves.eventos });
      };
      ws.onclose = () => {
        setLigado(false);
        if (fechado) return;
        const atraso = Math.min(30_000, 1000 * 2 ** tentativas++);
        timer = setTimeout(ligar, atraso);
      };
    };

    ligar();
    return () => {
      fechado = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [ativo, qc]);

  // Com mocks (ou sem URL) não há tempo real, e isso não é um erro a mostrar.
  return ativo ? ligado : true;
}
