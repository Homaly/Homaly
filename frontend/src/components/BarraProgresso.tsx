/**
 * Barra de progresso grossa, em pílula, com um reflexo por cima (estilo Duolingo).
 * Enche a turquesa e desliza para o valor novo; com "reduzir movimento" muda sem deslizar.
 */
export default function BarraProgresso({ valor, total, rotulo }: { valor: number; total: number; rotulo: string }) {
  const percentagem = total > 0 ? Math.min(100, Math.max(0, (valor / total) * 100)) : 0;
  return (
    <div
      role="progressbar"
      aria-label={rotulo}
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={valor}
      aria-valuetext={`Passo ${valor} de ${total}`}
      className="h-4 flex-1 overflow-hidden rounded-full bg-surface-tonal"
    >
      <div
        className="relative h-full rounded-full bg-primary motion-safe:transition-[width] motion-safe:duration-500 motion-safe:ease-[var(--ease-emphasized)]"
        style={{ width: `${percentagem}%` }}
      >
        {percentagem > 6 && <span className="absolute inset-x-2 top-1 h-1 rounded-full bg-white/45" />}
      </div>
    </div>
  );
}
