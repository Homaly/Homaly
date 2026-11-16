export function EstadoCarregar() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="A carregar">
      {[0, 1, 2].map(i => (
        <div key={i} className="h-20 rounded-xl bg-slate-200/70 dark:bg-card-dark animate-pulse" />
      ))}
    </div>
  );
}

export function EstadoErro({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <span className="material-symbols-outlined text-4xl text-red-500">cloud_off</span>
      <p className="text-sm text-slate-600 dark:text-slate-300">Não foi possível falar com a casa.</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 rounded-lg bg-primary text-background-dark font-semibold text-sm"
      >
        Tentar de novo
      </button>
    </div>
  );
}

export function EstadoVazio({ icon, texto }: { icon: string; texto: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <span className="material-symbols-outlined text-5xl text-accent-green">{icon}</span>
      <p className="text-base font-medium">{texto}</p>
    </div>
  );
}
