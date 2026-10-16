import type { LearningPolicyDraft } from '../lib/learningPolicy';
import { remainingLearningPoints } from '../lib/learningPolicy';

export function LearningPolicyEditor({ value, points, onChange }: {
  value: LearningPolicyDraft; points: number; onChange: (next: LearningPolicyDraft) => void;
}) {
  const totalPenalty = value.hints.reduce((sum, hint) => sum + Number(hint.penalty_percent || 0), 0);
  const updateHint = (index: number, patch: Partial<LearningPolicyDraft['hints'][number]>) =>
    onChange({ ...value, hints: value.hints.map((hint, i) => i === index ? { ...hint, ...patch } : hint) });
  let cumulativePenalty = 0;
  return <fieldset className="learning-policy-editor">
    <legend>Tiempo, pistas y puntaje</legend>
    <p>El administrador y el instructor definen una duración común para este reto. El plazo de cada estudiante comienza al iniciar su primera práctica y se conserva al volver a abrirla.</p>
    <div className="form-grid">
      <label>Duración del reto (minutos)
        <input type="number" min="1" max="1440" step="1" required value={value.duration_minutes} onChange={event => onChange({ ...value, duration_minutes: event.target.value })} />
        <small className="field-help">Entre 1 minuto y 24 horas. La misma duración para todos.</small>
      </label>
      <label>Puntaje restante al vencer el tiempo (%)
        <input type="number" min="0" max="100" step="1" required value={value.expired_points_percent} onChange={event => onChange({ ...value, expired_points_percent: event.target.value })} />
        <small className="field-help">Se muestra la solución y quedan {remainingLearningPoints(points, Number(value.expired_points_percent))} de {points || 0} puntos base. Este porcentaje sustituye los descuentos de pistas.</small>
      </label>
    </div>
    <div className="learning-policy-hints-heading"><h4>Pistas en orden de desbloqueo</h4>
      <button type="button" className="secondary-action" disabled={value.hints.length >= 3} onClick={() => onChange({ ...value, hints: [...value.hints, { title: `Pista ${value.hints.length + 1}`, content: '', penalty_percent: '10' }] })}>+ Añadir pista</button>
    </div>
    <p className="field-help">Entre 1 y 3 pistas. Cada descuento se calcula sobre los puntos base; su suma no puede superar el 100%.</p>
    {value.hints.map((hint, index) => {
      cumulativePenalty += Number(hint.penalty_percent || 0);
      return <div className="learning-policy-hint" key={index}>
        <div className="learning-policy-hints-heading"><h4>Pista {index + 1}</h4>
          <button type="button" className="table-action danger" disabled={value.hints.length <= 1} onClick={() => onChange({ ...value, hints: value.hints.filter((_, i) => i !== index) })} aria-label={`Quitar pista ${index + 1}`}>Quitar pista</button>
        </div>
        <div className="form-grid">
          <label>Título de la pista {index + 1}<input required maxLength={120} value={hint.title} onChange={event => updateHint(index, { title: event.target.value })} /></label>
          <label>Descuento de la pista {index + 1} (%)<input type="number" min="0" max="100" step="1" required value={hint.penalty_percent} onChange={event => updateHint(index, { penalty_percent: event.target.value })} /></label>
        </div>
        <label className="form-full">Texto de la pista {index + 1}<textarea required maxLength={4000} rows={3} value={hint.content} onChange={event => updateHint(index, { content: event.target.value })} /></label>
        <small className="field-help">Después de abrir las pistas 1 a {index + 1}: {remainingLearningPoints(points, 100 - cumulativePenalty)} puntos disponibles.</small>
      </div>;
    })}
    <p className={`learning-policy-total${totalPenalty > 100 ? ' invalid' : ''}`} aria-live="polite">Descuento total por pistas: {totalPenalty}% · {remainingLearningPoints(points, 100 - totalPenalty)} puntos restantes.</p>
    <label className="form-full">Solución del instructor (opcional)
      <textarea rows={4} maxLength={12000} value={value.solution_text} onChange={event => onChange({ ...value, solution_text: event.target.value })} placeholder="Explica cómo resolver el reto. Este texto se mostrará cuando termine el plazo." />
      <small className="field-help">Si se deja vacío, se usa la solución automática disponible para el tipo de reto. Las pistas cerradas y esta solución no se envían al estudiante antes de tiempo.</small>
    </label>
    <p className="field-help">Los cambios se aplican a estudiantes que todavía no hayan iniciado este reto. Las prácticas iniciadas y los puntos ya obtenidos conservan sus reglas.</p>
  </fieldset>;
}
