import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Anomalia, MensagemWs } from '../types/contract';
import { useToast } from '../context/ToastContext';
import { USE_MOCKS } from '.';
import { chaves, guardarAnomaliaNaCache } from './hooks';
import { WS_URL } from './enderecos';

const URGENTES = new Set<Anomalia['classe']>(['seguranca', 'bem_estar']);
/**
 * Quanto tempo sem ligação antes de mostrar "Sem ligação em tempo real". Ao abrir a app, ou ao
 * sair dela (por exemplo, para o login da Google), o WebSocket fecha-se por instantes: isso não é
 * uma falha e não deve piscar o aviso.
 */
const AVISO_MS = 3000;

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
  const [ligado, setLigado] = useState(true);

  useEffect(() => {
    if (!ativo) return;
    let ws: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let aviso: ReturnType<typeof setTimeout> | undefined;
    let tentativas = 0;
    let fechado = false;
    // O último estado visto de cada anomalia, para quando a lista ainda não está em cache.
    const vistas = new Map<string, Anomalia>();

    const avisarSeNaoLigar = () => {
      aviso ??= setTimeout(() => setLigado(false), AVISO_MS);
    };

    const ligar = () => {
      avisarSeNaoLigar();
      ws = new WebSocket(WS_URL!);
      ws.onopen = () => {
        tentativas = 0;
        clearTimeout(aviso);
        aviso = undefined;
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
        if (fechado) return;
        avisarSeNaoLigar();
        const atraso = Math.min(30_000, 1000 * 2 ** tentativas++);
        timer = setTimeout(ligar, atraso);
      };
    };

    ligar();
    return () => {
      fechado = true;
      clearTimeout(timer);
      clearTimeout(aviso);
      ws?.close();
    };
  }, [ativo, qc, showToast]);

  // Com mocks (ou sem URL) não há tempo real, e isso não é um erro a mostrar.
  return ativo ? ligado : true;
}
