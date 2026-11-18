import {
  ArrowLeft,
  CircleAlert,
  CircleCheck,
  CloudOff,
  Heart,
  History,
  House,
  Info,
  Mic,
  MessageCircle,
  Moon,
  SendHorizontal,
  Settings,
  Shield,
  Square,
  Sun,
  Thermometer,
  TriangleAlert,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../lib/cn';

/** Os ícones da app (Lucide, traço fino como na app Connected Home). Para usar um novo, junte-o aqui. */
const ICONES = {
  arrow_back: ArrowLeft,
  bolt: Zap,
  chat: MessageCircle,
  check_circle: CircleCheck,
  close: X,
  cloud_off: CloudOff,
  dark_mode: Moon,
  error: CircleAlert,
  favorite: Heart,
  history: History,
  home: House,
  info: Info,
  light_mode: Sun,
  mic: Mic,
  send: SendHorizontal,
  settings: Settings,
  shield: Shield,
  stop: Square,
  thermostat: Thermometer,
  warning: TriangleAlert,
} satisfies Record<string, LucideIcon>;

export type NomeIcone = keyof typeof ICONES;

type IconeProps = {
  nome: NomeIcone;
  /** Traço mais grosso: separador ativo da barra de baixo. */
  ativo?: boolean;
  /** Tamanho e cor por classes (`size-5`, `text-danger`); por omissão 24 px. */
  className?: string;
};

/**
 * Ícone decorativo: o leitor de ecrã não o lê.
 * Quando o ícone é a única informação, pôr texto ao lado em `sr-only`.
 */
export default function Icone({ nome, ativo, className }: IconeProps) {
  const Svg = ICONES[nome];
  return (
    <Svg
      aria-hidden="true"
      focusable="false"
      strokeWidth={ativo ? 2.25 : 1.75}
      className={cn('size-6 shrink-0', className)}
    />
  );
}
