import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../lib/cn';
import Icone, { type NomeIcone } from './Icone';

const SEPARADORES: { to: string; icon: NomeIcone; label: string }[] = [
  { to: '/', icon: 'home', label: 'Início' },
  { to: '/conversa', icon: 'chat', label: 'Conversa' },
  { to: '/historico', icon: 'history', label: 'Histórico' },
  { to: '/definicoes', icon: 'settings', label: 'Definições' },
];

/**
 * Barra de baixo: 64 px de altura mais o contorno. A caixa da Conversa assenta em bottom-16.
 * Como na app Connected Home: o separador ativo fica no branco do texto, com traço mais grosso.
 */
export default function BottomNav() {
  const { pathname } = useLocation();
  // O detalhe da anomalia não é um separador: tem a seta de voltar e fica sem barra.
  if (pathname.startsWith('/anomalias/')) return null;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-outline-variant bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
      <ul className="mx-auto grid max-w-md grid-cols-4">
        {SEPARADORES.map(s => (
          <li key={s.to}>
            <NavLink
              to={s.to}
              end={s.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex h-16 flex-col items-center justify-center gap-1 text-[13px] transition-colors',
                  isActive ? 'font-semibold text-on-surface' : 'font-medium text-muted'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icone nome={s.icon} ativo={isActive} />
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
