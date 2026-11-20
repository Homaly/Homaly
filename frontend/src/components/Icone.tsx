import {
  ArrowLeft,
  Calendar,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  CloudOff,
  Heart,
  History,
  House,
  Info,
  Mic,
  MessageCircle,
  SendHorizontal,
  Settings,
  Shield,
  Square,
  Thermometer,
  TriangleAlert,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { useId, type ReactNode } from 'react';
import { cn } from '../lib/cn';

/** Os ícones da app (Lucide, traço fino como na app Connected Home). Para usar um novo, junte-o aqui. */
const ICONES = {
  arrow_back: ArrowLeft,
  calendar: Calendar,
  bolt: Zap,
  chat: MessageCircle,
  check_circle: CircleCheck,
  chevron_right: ChevronRight,
  expand_more: ChevronDown,
  close: X,
  cloud_off: CloudOff,
  error: CircleAlert,
  favorite: Heart,
  history: History,
  home: House,
  info: Info,
  mic: Mic,
  send: SendHorizontal,
  settings: Settings,
  shield: Shield,
  stop: Square,
  thermostat: Thermometer,
  warning: TriangleAlert,
} satisfies Record<string, LucideIcon>;

export type NomeIcone = keyof typeof ICONES;

const TRACO = 1.75;

/** Moldura comum das versões cheias: 24×24 como o Lucide, preenchidas e com o mesmo traço por fora. */
function SvgCheio({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      stroke="currentColor"
      strokeWidth={TRACO}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      {children}
    </svg>
  );
}

/**
 * Versões cheias dos ícones da barra de baixo, para o separador ativo. Desenhadas sobre os contornos
 * do Lucide 1.74 (house, message-circle, rotate-ccw-clock, settings), para trocarem sem mudar de
 * tamanho; o Lucide só tem ícones de traço. Os pormenores (porta, ponteiros, furo) ficam recortados.
 */
const CHEIOS: Partial<Record<NomeIcone, (props: { className?: string }) => ReactNode>> = {
  // A casa com a porta recortada, aberta em baixo.
  home: ({ className }) => (
    <SvgCheio className={className}>
      <path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2h-4v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8H5a2 2 0 0 1-2-2z" />
    </SvgCheio>
  ),
  chat: ({ className }) => (
    <SvgCheio className={className}>
      <path d="M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719z" />
    </SvgCheio>
  ),
  history: HistoricoCheio,
  // A roda dentada com o furo do meio (evenodd).
  settings: ({ className }) => (
    <SvgCheio className={className}>
      <path
        fillRule="evenodd"
        d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915zM15 12a3 3 0 1 0-6 0 3 3 0 1 0 6 0z"
      />
    </SvgCheio>
  ),
};

/**
 * O anel com a seta fica de traço, como no ícone normal (encher o anel apagava a seta), e o
 * mostrador do relógio fica cheio, com os ponteiros recortados por uma máscara (um id por ícone).
 * A ponta da seta é 1 px mais curta, para não tocar no mostrador.
 */
function HistoricoCheio({ className }: { className?: string }) {
  const mascara = `relogio-${useId().replace(/[^\w-]/g, '')}`;
  return (
    <SvgCheio className={className}>
      <defs>
        <mask id={mascara}>
          <rect width="24" height="24" fill="white" />
          <path d="M12 8.75v3.25l2.25 1.25" fill="none" stroke="black" />
        </mask>
      </defs>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" fill="none" />
      <path d="M3 3v5h4" fill="none" />
      <circle cx="12" cy="12" r="5.25" stroke="none" mask={`url(#${mascara})`} />
    </SvgCheio>
  );
}

type IconeProps = {
  nome: NomeIcone;
  /** Separador ativo da barra de baixo: a versão cheia, se houver; senão, traço mais grosso. */
  ativo?: boolean;
  /** Tamanho e cor por classes (`size-5`, `text-danger`); por omissão 24 px. */
  className?: string;
};

/**
 * Ícone decorativo: o leitor de ecrã não o lê.
 * Quando o ícone é a única informação, pôr texto ao lado em `sr-only`.
 */
export default function Icone({ nome, ativo, className }: IconeProps) {
  const classes = cn('size-6 shrink-0', className);
  const Cheio = ativo ? CHEIOS[nome] : undefined;
  if (Cheio) return <Cheio className={classes} />;
  const Svg = ICONES[nome];
  return <Svg aria-hidden="true" focusable="false" strokeWidth={ativo ? 2.25 : TRACO} className={classes} />;
}
