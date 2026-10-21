import type { ChallengeDeletionPreview } from "../models/challenge";

/** La confirmación es literal: no se corrigen espacios ni mayúsculas. */
export function canPermanentlyDeleteChallenge(input: {
  isAdmin: boolean;
  code: string;
  confirmation: string;
  preview: ChallengeDeletionPreview | null;
  loading: boolean;
  busy: boolean;
}): boolean {
  return input.isAdmin && !input.loading && !input.busy && input.code.length > 0 &&
    input.confirmation === input.code && input.preview?.code === input.code &&
    input.preview.can_delete === true && input.preview.blockers.length === 0;
}

export const challengeDeletionCountLabels: Record<string, string> = {
  flags: "Flags configuradas",
  run_flags: "Flags de corridas",
  instances: "Instancias de laboratorio",
  runs: "Corridas",
  completions: "Retos completados por estudiantes",
  submissions: "Envíos de respuestas",
  group_assignments: "Asignaciones a grupos",
  learning_progress: "Registros de aprendizaje",
  hint_reveals: "Pistas consultadas",
  remote_access_assignments: "Asignaciones de acceso remoto",
  awarded_points: "Puntos que se retirarán del ranking",
};
