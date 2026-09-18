/** Fila del ranking general. */
export type RankingRow = {
  position: number;
  username: string;
  total_points: number;
  challenges_completed: number;
};

/** Progreso de un estudiante dentro de un grupo. */
export type ProgressRow = {
  user_id: number;
  username: string;
  challenge_code: string;
  challenge_name: string;
  status: "Completado" | "No iniciado";
  points: number;
  attempts: number;
  completed_at: string | null;
};
