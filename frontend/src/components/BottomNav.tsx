import { NavLink, useLocation } from 'react-router-dom';
import { useAnomaliasAtivas } from '../api/hooks';
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
 * O separador ativo tem uma pílula turquesa clara atrás do ícone, letra a negrito e traço mais grosso.
 * O Início mostra quantos avisos estão por responder, para se ver a partir de qualquer separador.
 */
export default function BottomNav() {
  const { pathname } = useLocation();
  const { data: ativas } = useAnomaliasAtivas();
  const porResponder = ativas?.length ?? 0;

  // O detalhe da anomalia não é um separador: tem a seta de voltar e fica sem barra.
  if (pathname.startsWith('/anomalias/')) return null;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-outline-variant bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
      <ul className="mx-auto grid max-w-md grid-cols-4">
        {SEPARADORES.map(s => {
          const contador = s.to === '/' ? porResponder : 0;
          return (
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
                    <span
                      className={cn(
                        'relative flex h-8 w-14 items-center justify-center rounded-full transition-colors',
                        isActive && 'bg-primary/25'
                      )}
                    >
                      <Icone nome={s.icon} ativo={isActive} />
                      {contador > 0 && (
                        // Laranja: pede atenção. O contorno separa-o do ícone.
                        <span
                          aria-hidden
                          className="absolute -top-0.5 left-[calc(50%+4px)] flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-accent-orange px-1 text-[11px] font-bold leading-none text-on-accent-orange ring-2 ring-surface"
                        >
                          {contador > 9 ? '9+' : contador}
                        </span>
                      )}
                    </span>
                    {s.label}
                    {contador > 0 && (
                      <span className="sr-only">
                        , {contador === 1 ? '1 aviso por responder' : `${contador} avisos por responder`}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
