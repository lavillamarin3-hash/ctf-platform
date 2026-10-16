import type { ChallengeLearningPolicy } from '../models/challenge';

export type LearningPolicyDraft = {
  duration_minutes: string;
  expired_points_percent: string;
  hints: Array<{ title: string; content: string; penalty_percent: string }>;
  solution_text: string;
};

export function learningPolicyDraft(policy?: ChallengeLearningPolicy | null): LearningPolicyDraft {
  return {
    duration_minutes: String(policy?.duration_minutes ?? 60),
    expired_points_percent: String(policy?.expired_points_percent ?? 25),
    hints: policy?.hints.map(hint => ({ ...hint, penalty_percent: String(hint.penalty_percent) }))
      ?? [1, 2, 3].map(number => ({ title: `Pista ${number}`, content: '', penalty_percent: '10' })),
    solution_text: policy?.solution_text ?? '',
  };
}

function integer(value: string, minimum: number, maximum: number, label: string): number {
  if (!/^\d+$/.test(value.trim())) throw new Error(`${label}: introduce un número entero.`);
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new Error(`${label}: usa un valor entre ${minimum} y ${maximum}.`);
  }
  return parsed;
}

export function serializeLearningPolicy(draft: LearningPolicyDraft): ChallengeLearningPolicy {
  const duration_minutes = integer(draft.duration_minutes, 1, 1440, 'Duración');
  const expired_points_percent = integer(draft.expired_points_percent, 0, 100, 'Puntaje al vencer el tiempo');
  if (draft.hints.length < 1 || draft.hints.length > 3) throw new Error('Configura entre una y tres pistas.');
  const hints = draft.hints.map((hint, index) => {
    const title = hint.title.trim();
    const content = hint.content.trim();
    if (!title || !content) throw new Error(`Completa el título y el texto de la pista ${index + 1}.`);
    if (title.length > 120 || content.length > 4000) throw new Error(`La pista ${index + 1} admite hasta 120 caracteres de título y 4000 de texto.`);
    return { title, content, penalty_percent: integer(hint.penalty_percent, 0, 100, `Descuento de la pista ${index + 1}`) };
  });
  if (hints.reduce((sum, hint) => sum + hint.penalty_percent, 0) > 100) {
    throw new Error('La suma de los descuentos de las pistas no puede superar el 100%.');
  }
  const solution_text = draft.solution_text.trim();
  if (solution_text.length > 12000) throw new Error('La solución admite hasta 12000 caracteres.');
  return { duration_minutes, expired_points_percent, hints, solution_text: solution_text || null };
}

export function remainingLearningPoints(base: number, percent: number): number {
  return Math.floor(Math.max(0, Number.isFinite(base) ? base : 0) * Math.min(100, Math.max(0, Number.isFinite(percent) ? percent : 0)) / 100);
}
