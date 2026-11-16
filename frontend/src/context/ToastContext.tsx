import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

export type ToastType = 'success' | 'info' | 'warning' | 'error';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside ToastProvider');
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
  }, []);

  const showToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = crypto.randomUUID();
    setToasts(prev => [...prev.slice(-2), { id, message, type }]);
    const timer = setTimeout(() => dismiss(id), 4000);
    timers.current.set(id, timer);
  }, [dismiss]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-20 inset-x-0 z-50 flex flex-col items-center gap-2 px-4 pointer-events-none">
        {toasts.map(toast => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const TOAST_STYLES: Record<ToastType, { border: string; icon: string; iconColor: string }> = {
  success: { border: 'border-accent-green/40', icon: 'check_circle', iconColor: 'text-accent-green' },
  info: { border: 'border-primary/40', icon: 'info', iconColor: 'text-primary' },
  warning: { border: 'border-accent-orange/40', icon: 'warning', iconColor: 'text-accent-orange' },
  error: { border: 'border-red-500/40', icon: 'error', iconColor: 'text-red-500' },
};

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const { border, icon, iconColor } = TOAST_STYLES[toast.type];
  return (
    <div
      className={`animate-toast-in pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border ${border} bg-white dark:bg-card-dark shadow-lg w-full max-w-sm`}
    >
      <span className={`material-symbols-outlined text-xl shrink-0 ${iconColor}`}>{icon}</span>
      <span className="text-sm font-medium text-slate-800 dark:text-slate-100 flex-1">{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 shrink-0"
        aria-label="Fechar"
      >
        <span className="material-symbols-outlined text-base">close</span>
      </button>
    </div>
  );
}
