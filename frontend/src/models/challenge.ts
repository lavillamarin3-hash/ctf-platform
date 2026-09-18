/** Bandera asociada a un reto. */
export type Flag = {
  id: number;
  label: string;
  flag_order: number;
  is_active: boolean;
  mode?: "static" | "dynamic";
  template?: string | null;
};

/** Reto visible en la plataforma CTF. */
export type Challenge = {
  id: number;
  code: string;
  name: string;
  description: string;
  instructions: string;
  difficulty: "Básico" | "Medio" | "Avanzado";
  category: string;
  scenario?: string | null;
  mitre_technique: string;
  asset_references: string[];
  points: number;
  is_published: boolean;
  flag_count: number;
  completed: boolean;
  flags?: Flag[];
};
