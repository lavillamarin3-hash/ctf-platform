// ============================================================ 
// CONFIGURACIÓN Y TIPOS COMPARTIDOS 
// Responsabilidad: concentrar tipos, opciones e inventario estático. 
// No contiene lógica de presentación ni acceso a APIs. 
// 
// ORGANIZACIÓN:
// 1. Tipos globales y navegación
// 2. Modelos de laboratorio
// 3. Funciones de usuario
// 4. Catálogo de demostración compatible
// 5. Metadatos de retos
// 6. Inventario de red real
// 7. Laboratorios de respaldo
// ============================================================ 

import type { Challenge, User } from "./api"; 
export type { Challenge, User } from "./api"; 

// ============================================================
// 1. TEMA Y NAVEGACIÓN
// ============================================================

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
  | "groups" 
  | "laboratory" 
  | "ranking" 
  | "monitoring" 
  | "guacamole"; 

// ============================================================
// 2. MODELOS DE LABORATORIO
// ============================================================

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

// ============================================================
// 3. FUNCIONES DE USUARIO
// ============================================================

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

// ============================================================
// 4. DATOS DEMO DE COMPATIBILIDAD
// ============================================================
// Se conservan para componentes antiguos. La pantalla de administración
// actual no debe utilizarlos como sustituto de datos reales.

export const DEMO_USERS: ManagedUser[] = [ 
  { 
    id: -1, 
    username: "admin.demo", 
    email: "admin.demo@cyberlab.local", 
    role: "admin", 
    is_active: true, 
    full_name: "Administrador Demo", 
    user_function: "Administrador de laboratorio", 
    organization: "Cyber Lab", 
    demo: true, 
  }, 
  { 
    id: -2, 
    username: "instructor.demo", 
    email: "instructor.demo@cyberlab.local", 
    role: "instructor", 
    is_active: true, 
    full_name: "Instructor Demo", 
    user_function: "Instructor", 
    organization: "Cyber Lab", 
    demo: true, 
  }, 
  { 
    id: -3, 
    username: "estudiante.demo", 
    email: "estudiante.demo@cyberlab.local", 
    role: "player", 
    is_active: true, 
    full_name: "Estudiante Demo", 
    user_function: "Estudiante", 
    organization: "Universidad Demo", 
    demo: true, 
  }, 
  { 
    id: -4, 
    username: "redteam.demo", 
    email: "redteam.demo@cyberlab.local", 
    role: "player", 
    is_active: true, 
    full_name: "Red Team Demo", 
    user_function: "Red Team", 
    organization: "Cyber Lab", 
    demo: true, 
  }, 
  { 
    id: -5, 
    username: "blueteam.demo", 
    email: "blueteam.demo@cyberlab.local", 
    role: "player", 
    is_active: true, 
    full_name: "Blue Team Demo", 
    user_function: "Blue Team", 
    organization: "Cyber Lab", 
    demo: true, 
  }, 
  { 
    id: -6, 
    username: "soc.demo", 
    email: "soc.demo@cyberlab.local", 
    role: "instructor", 
    is_active: true, 
    full_name: "Analista SOC Demo", 
    user_function: "Analista SOC", 
    organization: "SOC Demo", 
    demo: true, 
  }, 
  { 
    id: -7, 
    username: "guest.demo", 
    email: "guest.demo@cyberlab.local", 
    role: "guest", 
    is_active: true, 
    full_name: "Invitado Demo", 
    user_function: "Otro", 
    organization: "Externo", 
    demo: true, 
  }, 
]; 

// ============================================================
// 5. METADATOS DE RETOS
// ============================================================

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

// ============================================================
// 6. INVENTARIO DE RED REAL
// ============================================================
// IPs disponibles para la demostración real actual.
// Atacante: 192.168.146.134
// Víctima:  192.168.146.137

export const NETWORK_IPS = { 
  Atacantes: ["192.168.146.134"], 
  Víctimas: ["192.168.146.137"], 
} as const; 

export const LAB_NETWORK_METADATA = { 
  Atacantes: { 
    label: "Atacante", 
    segment: "Red actual · 192.168.146.134", 
  }, 
  Víctimas: { 
    label: "Víctima", 
    segment: "Red actual · 192.168.146.137", 
  }, 
} as const; 

// ============================================================
// 7. LABORATORIOS DE RESPALDO
// ============================================================
// Este inventario se usa solo como respaldo local cuando el backend
// no devuelve laboratorios. El inventario persistente se obtiene del API.

export const DEFAULT_LABORATORIES: Laboratory[] = [ 
  { 
    id: "lab-atacantes", 
    code: "LAB-ATACANTES", 
    name: "Laboratorio de Atacantes", 
    description: 
      "Segmento ofensivo del cyber range para ejercicios controlados.", 
    status: "Disponible", 
    environment: 
      "Red actual · 192.168.146.0/24 · Nutanix AHV · Guacamole", 
    vms: [ 
      { 
        id: "vm-kali", 
        name: "LAB-KALI", 
        ip: "192.168.146.134", 
        operatingSystem: "Kali Linux 2026.2", 
        profile: "Standard", 
        networkRole: "Atacantes", 
        vlan: "Red actual", 
        subnet: "192.168.146.0/24", 
      }, 
      { 
        id: "vm-kali-purple", 
        name: "LAB-KALI-PURPLE", 
        ip: "10.10.20.11", 
        operatingSystem: "Kali Linux Purple 2026.2", 
        profile: "Standard", 
        networkRole: "Atacantes", 
        vlan: "VLAN 20", 
        subnet: "10.10.20.0/24", 
      }, 
      { 
        id: "vm-kali-blue", 
        name: "LAB-KALI-BLUE", 
        ip: "10.10.20.12", 
        operatingSystem: "Linux Mint", 
        profile: "Standard", 
        networkRole: "Atacantes", 
        vlan: "VLAN 20", 
        subnet: "10.10.20.0/24", 
      }, 
    ], 
  }, 
  { 
    id: "lab-victimas", 
    code: "LAB-VICTIMAS", 
    name: "Laboratorio de Víctimas", 
    description: 
      "Segmento objetivo para escenarios de ataque, explotación y movimiento lateral.", 
    status: "Disponible", 
    environment: 
      "Red actual · 192.168.146.0/24 · Nutanix AHV · Guacamole", 
    vms: [ 
      { 
        id: "vm-win-a", 
        name: "LAB-WINVICT-A", 
        ip: "10.10.30.10", 
        operatingSystem: "Windows 10 (ES)", 
        profile: "Vulnerable", 
        networkRole: "Víctimas", 
        vlan: "VLAN 30", 
        subnet: "10.10.30.0/24", 
      }, 
      { 
        id: "vm-win-b", 
        name: "LAB-WINVICT-B", 
        ip: "10.10.30.11", 
        operatingSystem: "Windows 10 (ES)", 
        profile: "Vulnerable", 
        networkRole: "Víctimas", 
        vlan: "VLAN 30", 
        subnet: "10.10.30.0/24", 
      }, 
      { 
        id: "vm-lnx", 
        name: "LAB-LNXVICT", 
        ip: "192.168.146.137", 
        operatingSystem: "Ubuntu Server 26.04", 
        profile: "Vulnerable", 
        networkRole: "Víctimas", 
        vlan: "Red actual", 
        subnet: "192.168.146.0/24", 
      }, 
      { 
        id: "vm-web", 
        name: "LAB-SRVWEB", 
        ip: "10.10.30.20", 
        operatingSystem: "Ubuntu Server 26.04", 
        profile: "Vulnerable", 
        networkRole: "Víctimas", 
        vlan: "VLAN 30", 
        subnet: "10.10.30.0/24", 
      }, 
      { 
        id: "vm-fsad", 
        name: "LAB-SRVFSAD", 
        ip: "10.10.30.21", 
        operatingSystem: "Ubuntu Server 26.04", 
        profile: "Vulnerable", 
        networkRole: "Víctimas", 
        vlan: "VLAN 30", 
        subnet: "10.10.30.0/24", 
      }, 
    ], 
  }, 
];