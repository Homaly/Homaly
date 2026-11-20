/**
 * Tira a animação de arranque (#arranque, em index.html) quando a app já desenhou o primeiro ecrã,
 * mas nunca antes de a linha acabar de se desenhar: 250 ms de espera + 650 ms de traço, mais um
 * pouco para se ver completa. Com "reduzir movimento" sai logo. Chamar uma vez; repetir não faz mal.
 */
const LINHA_COMPLETA_MS = 1000;
const SAIDA_MS = 250;

let pedido = false;

export function esconderArranque() {
  if (pedido) return;
  pedido = true;
  const el = document.getElementById('arranque');
  if (!el) return;
  const reduzir = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // performance.now() conta desde que a página começou a carregar, como a animação.
  const falta = reduzir ? 0 : Math.max(0, LINHA_COMPLETA_MS - performance.now());
  window.setTimeout(() => {
    el.classList.add('a-sair');
    window.setTimeout(() => el.remove(), SAIDA_MS);
  }, falta);
}
