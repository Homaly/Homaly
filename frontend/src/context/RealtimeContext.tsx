import { createContext, useContext, type ReactNode } from 'react';
import { useRealtime } from '../api/useRealtime';

const RealtimeContext = createContext(true);

/** Mantém uma só ligação WebSocket para toda a app. */
export function RealtimeProvider({ children }: { children: ReactNode }) {
  const ligado = useRealtime();
  return <RealtimeContext.Provider value={ligado}>{children}</RealtimeContext.Provider>;
}

export const useRealtimeLigado = () => useContext(RealtimeContext);
