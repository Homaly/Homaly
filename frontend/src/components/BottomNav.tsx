import { NavLink } from 'react-router-dom';
import { cn } from '../lib/cn';

const SEPARADORES = [
  { to: '/', icon: 'home', label: 'Início' },
  { to: '/conversa', icon: 'chat', label: 'Conversa' },
  { to: '/historico', icon: 'history', label: 'Histórico' },
  { to: '/definicoes', icon: 'settings', label: 'Definições' },
];

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 inset-x-0 z-40 border-t border-slate-200 dark:border-primary/10 bg-white/95 dark:bg-card-dark/95 backdrop-blur-md pb-[env(safe-area-inset-bottom)]">
      <ul className="mx-auto max-w-md grid grid-cols-4">
        {SEPARADORES.map(s => (
          <li key={s.to}>
            <NavLink
              to={s.to}
              end={s.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex flex-col items-center gap-0.5 py-2 text-xs font-medium transition-colors',
                  isActive ? 'text-primary' : 'text-slate-500 dark:text-slate-400'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className="material-symbols-outlined"
                    style={{ fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}
                  >
                    {s.icon}
                  </span>
                  {s.label}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
