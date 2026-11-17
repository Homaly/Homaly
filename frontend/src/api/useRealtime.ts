import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Anomalia, MensagemWs } from '../types/contract';
import { useToast } from '../context/ToastContext';
import { USE_MOCKS } from '.';
import { chaves, guardarAnomaliaNaCache } from './hooks';

const WS_URL = import.meta.env.VITE_WS_URL as string | undefined;

const URGENTES = new Set<Anomalia['classe']>(['seguranca', 'bem_estar']);

/**
 * Se uma anomalia que chega pelo WebSocket merece aviso no ecrã (US02): é nova e ativa,
 * ou passou a urgente (ex.: a US12 que vira US08). Uma atualização de texto não avisa.
 */
export function mereceAviso(anterior: Anomalia | undefined, nova: Anomalia): boolean {
  if (nova.estado !== 'ativa') return false;
  if (!anterior || anterior.estado !== 'ativa') return true;
  return URGENTES.has(nova.classe) && !URGENTES.has(anterior.classe);
}

/**
 * Liga ao WebSocket do backend e mantém as caches atualizadas. Uma anomalia nova mostra um
 * toast e faz vibrar o telemóvel, em qualquer ecrã (só com a app aberta, como no DECISIONS.md).
 * Devolve se está ligado.
 */
export function useRealtime(): boolean {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const ativo = !USE_MOCKS && !!WS_URL;
  const [ligado, setLigado] = useState(false);

  useEffect(() => {
    if (!ativo) return;
    let ws: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let tentativas = 0;
    let fechado = false;
    // O último estado visto de cada anomalia, para quando a lista ainda não está em cache.
    const vistas = new Map<string, Anomalia>();

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
        if (msg.tipo === 'anomalia') {
          const a = msg.anomalia;
          const anterior =
            vistas.get(a.id) ??
            qc.getQueryData<Anomalia>(chaves.anomalia(a.id)) ??
            qc.getQueryData<Anomalia[]>(chaves.anomaliasAtivas)?.find(x => x.id === a.id);
          vistas.set(a.id, a);
          guardarAnomaliaNaCache(qc, a);
          if (mereceAviso(anterior, a)) {
            const urgente = URGENTES.has(a.classe);
            showToast(a.titulo, urgente ? 'warning' : 'info');
            navigator.vibrate?.(urgente ? [200, 100, 200] : 150);
          }
        }
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
  }, [ativo, qc, showToast]);

  // Com mocks (ou sem URL) não há tempo real, e isso não é um erro a mostrar.
  return ativo ? ligado : true;
}
