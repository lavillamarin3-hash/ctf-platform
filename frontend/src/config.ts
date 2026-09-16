// ============================================================
// CONFIGURACIÓN Y TIPOS COMPARTIDOS
// Responsabilidad: concentrar tipos, opciones e inventario estático.
// No contiene lógica de presentación ni acceso a APIs.
// ============================================================

import type { Challenge, RankingRow, User } from "./api";
export type { Challenge, RankingRow, User } from "./api";

export type Theme = "dark" | "light";

export type ThemePreference = "system" | "dark" | "light";

export type PlayerView =
  | "dashboard"
  | "categories"
  | "challenges"
  | "progress"
  | "ranking"
  | "laboratory";

export type ManagementView =
  | "dashboard"
  | "challenges"
  | "users"
  | "laboratory"
  | "ranking"
  | "groups"
  | "monitoring"
  | "guacamole";

export type LabVM = {
  id: string;
  name: string;
  ip: string;
  operatingSystem: string;
  profile: "Vulnerable" | "Standard" | "Hardened";
  networkRole?: "Atacantes" | "Víctimas";
  vlan?: string;
  subnet?: string;
  guacamoleConnectionId?: string;
  guacamoleProtocol?: string;
  guacamoleUrl?: string;
};

export type Laboratory = {
  id: string;
  code: string;
  name: string;
  description: string;
  status: "Disponible" | "Mantenimiento" | "Planificado";
  environment: string;
  vms: LabVM[];
};

export type UserFunction =
  | "Estudiante"
  | "Instructor"
  | "Tutor"
  | "Analista SOC"
  | "Red Team"
  | "Blue Team"
  | "Administrador de laboratorio"
  | "Coordinador"
  | "Otro";

export type ManagedUser = User & {
  full_name: string;
  user_function: UserFunction;
  organization: string;
  demo?: boolean;
};

export const USER_FUNCTIONS: UserFunction[] = [
  "Estudiante",
  "Instructor",
  "Tutor",
  "Analista SOC",
  "Red Team",
  "Blue Team",
  "Administrador de laboratorio",
  "Coordinador",
  "Otro",
];

export const DEMO_USERS: ManagedUser[] = [];

export const difficultyStyle: Record<
  Challenge["difficulty"],
  string
> = {
  Básico:
    "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  Medio:
    "border-amber-400/30 bg-amber-400/10 text-amber-300",
  Avanzado:
    "border-rose-400/30 bg-rose-400/10 text-rose-300",
};

export const categoryMeta: Record<
  string,
  { icon: string; tone: string }
> = {
  WEB: { icon: "⌁", tone: "blue" },
  CRIPTOGRAFÍA: { icon: "◈", tone: "amber" },
  FORENSE: { icon: "⌕", tone: "green" },
  REVERSING: { icon: "</>", tone: "violet" },
  "PWN / EXPLOITING": { icon: "›_", tone: "red" },
  OSINT: { icon: "◎", tone: "cyan" },
  ESTEGANOGRAFÍA: { icon: "▧", tone: "pink" },
  MISC: { icon: "✦", tone: "slate" },
};

export const demoLabCount = 11;

export const VM_OS_OPTIONS = [
  "Windows 10 (ES)",
  "Ubuntu Server 26.04",
  "Linux Mint",
  "Kali Linux Purple 2026.2",
  "Kali Linux 2026.2",
] as const;

export const NETWORK_IPS = {
  // Inventario real disponible para la demostración actual.
  // El formulario de VM solo permite seleccionar estas IPs.
  Atacantes: ["192.168.146.134"],
  Víctimas: ["192.168.164.137"],
} as const;

export const LAB_NETWORK_METADATA = {
  Atacantes: { label: "Atacante", segment: "Red actual · 192.168.146.134" },
  Víctimas: { label: "Víctima", segment: "Red actual · 192.168.164.137" },
} as const;

export const DEFAULT_LABORATORIES: Laboratory[] = [];

export const DEMO_RANKING: RankingRow[] = [
  {
    position: 1,
    username: "CyberNinja",
    total_points: 14850,
    challenges_completed: 19,
  },
  {
    position: 2,
    username: "RootMaster",
    total_points: 13980,
    challenges_completed: 18,
  },
  {
    position: 3,
    username: "HackMaster",
    total_points: 12750,
    challenges_completed: 16,
  },
  {
    position: 4,
    username: "ZeroDay",
    total_points: 11540,
    challenges_completed: 15,
  },
  {
    position: 5,
    username: "PacketHunter",
    total_points: 10920,
    challenges_completed: 14,
  },
  {
    position: 6,
    username: "BlueFox",
    total_points: 9640,
    challenges_completed: 13,
  },
  {
    position: 7,
    username: "ShellRunner",
    total_points: 8210,
    challenges_completed: 11,
  },
  {
    position: 8,
    username: "NetGhost",
    total_points: 7350,
    challenges_completed: 10,
  },
  {
    position: 9,
    username: "ByteBreaker",
    total_points: 6280,
    challenges_completed: 9,
  },
  {
    position: 10,
    username: "TraceLab",
    total_points: 5140,
    challenges_completed: 8,
  },
];
