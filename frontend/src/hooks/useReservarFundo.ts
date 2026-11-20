import { useLayoutEffect, type RefObject } from 'react';

/**
 * Diz aos toasts quanto do fundo do ecrã um elemento fixo ocupa (as ações do detalhe, a caixa da
 * Conversa), em `--fundo-ocupado`, para eles aparecerem por cima dele em vez de o taparem.
 * Sem nenhum, os toasts ficam por cima da barra de baixo (ver ToastContext).
 */
export function useReservarFundo(ref: RefObject<HTMLElement | null>) {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const raiz = document.documentElement;
    const medir = () =>
      raiz.style.setProperty('--fundo-ocupado', `${Math.max(0, window.innerHeight - el.getBoundingClientRect().top)}px`);
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(el);
    window.addEventListener('resize', medir);
    return () => {
      observador.disconnect();
      window.removeEventListener('resize', medir);
      raiz.style.removeProperty('--fundo-ocupado');
    };
  }, [ref]);
}
