import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../lib/cn';
import Icone from './Icone';

const SEPARADORES = [
  { to: '/', icon: 'home', label: 'Início' },
  { to: '/conversa', icon: 'chat', label: 'Conversa' },
  { to: '/historico', icon: 'history', label: 'Histórico' },
  { to: '/definicoes', icon: 'settings', label: 'Definições' },
];

/** Barra de baixo: 64 px de altura mais o contorno. A caixa da Conversa assenta em bottom-16. */
export default function BottomNav() {
  const { pathname } = useLocation();
  // O detalhe da anomalia não é um separador: tem a seta de voltar e fica sem barra.
  if (pathname.startsWith('/anomalias/')) return null;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-outline-variant bg-surface-container/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
      <ul className="mx-auto grid max-w-md grid-cols-4">
        {SEPARADORES.map(s => (
          <li key={s.to}>
            <NavLink
              to={s.to}
              end={s.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex h-16 flex-col items-center justify-center gap-0.5 text-xs font-medium transition-colors',
                  isActive ? 'text-primary-ink' : 'text-muted'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icone nome={s.icon} preenchido={isActive} />
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
