import type { LearningPolicyDraft } from '../lib/learningPolicy';
import { remainingLearningPoints } from '../lib/learningPolicy';

/** The timer and the guidance are independently configured. */
export function LearningPolicyEditor({
  value, points, onChange, showTimer = true, showHints = true,
}: {
  value: LearningPolicyDraft;
  points: number;
  onChange: (next: LearningPolicyDraft) => void;
  showTimer?: boolean;
  showHints?: boolean;
}) {
  const totalPenalty = value.hints.reduce((sum, hint) => sum + Number(hint.penalty_percent || 0), 0);
  const updateHint = (index: number, patch: Partial<LearningPolicyDraft['hints'][number]>) =>
    onChange({ ...value, hints: value.hints.map((hint, i) => i === index ? { ...hint, ...patch } : hint) });
  let cumulativePenalty = 0;

  return (
    <fieldset className="learning-policy-editor">
      <legend>Configuración educativa</legend>
      {showTimer ? (
        <section className="ctf-learning-subsection">
          <h4>Temporizador y puntuación</h4>
          <p className="field-help">El plazo comienza al iniciar el reto. Al agotarse, aplica el porcentaje de puntos indicado.</p>
          <div className="form-grid">
            <label>Duración del reto (minutos)
              <input type="number" min="1" max="1440" step="1" required
                value={value.duration_minutes}
                onChange={event => onChange({ ...value, duration_minutes: event.target.value })} />
              <small className="field-help">Entre 1 y 1440 minutos.</small>
            </label>
            <label>Puntaje restante al vencer el tiempo (%)
              <input type="number" min="0" max="100" step="1" required
                value={value.expired_points_percent}
                onChange={event => onChange({ ...value, expired_points_percent: event.target.value })} />
              <small className="field-help">Quedan {remainingLearningPoints(points, Number(value.expired_points_percent))} de {points || 0} puntos.</small>
            </label>
          </div>
        </section>
      ) : (
        <p className="ctf-optional-note" role="status">Temporizador académico desactivado: no se muestra el reloj ni se penalizan puntos por vencimiento. La ejecución remota conserva un límite técnico de seguridad.</p>
      )}
      {showHints ? (
        <section className="ctf-learning-subsection">
          <div className="learning-policy-hints-heading">
            <h4>Pistas en orden de desbloqueo</h4>
            <button type="button" className="secondary-action" disabled={value.hints.length >= 3}
              onClick={() => onChange({ ...value, hints: [...value.hints, { title: `Pista ${value.hints.length + 1}`, content: '', penalty_percent: '10' }] })}>+ Añadir pista</button>
          </div>
          <p className="field-help">Hasta tres pistas. La suma de descuentos no puede superar el 100 %.</p>
          {value.hints.map((hint, index) => {
            cumulativePenalty += Number(hint.penalty_percent || 0);
            return <div className="learning-policy-hint" key={index}>
              <div className="learning-policy-hints-heading">
                <h4>Pista {index + 1}</h4>
                <button type="button" className="table-action danger"
                  onClick={() => onChange({ ...value, hints: value.hints.filter((_, i) => i !== index) })}
                  aria-label={`Quitar pista ${index + 1}`}>Quitar pista</button>
              </div>
              <div className="form-grid">
                <label>Título de la pista {index + 1}
                  <input required maxLength={120} value={hint.title} onChange={event => updateHint(index, { title: event.target.value })} />
                </label>
                <label>Descuento de la pista {index + 1} (%)
                  <input type="number" min="0" max="100" step="1" required
                    value={hint.penalty_percent} onChange={event => updateHint(index, { penalty_percent: event.target.value })} />
                </label>
              </div>
              <label className="form-full">Texto de la pista {index + 1}
                <textarea required maxLength={4000} rows={3} value={hint.content}
                  onChange={event => updateHint(index, { content: event.target.value })} />
              </label>
              <small className="field-help">Después de abrir pistas 1 a {index + 1}: {remainingLearningPoints(points, 100 - cumulativePenalty)} puntos disponibles.</small>
            </div>;
          })}
          <p className={`learning-policy-total${totalPenalty > 100 ? ' invalid' : ''}`} aria-live="polite">
            Descuento acumulado: {totalPenalty}% · {remainingLearningPoints(points, 100 - totalPenalty)} puntos restantes.
          </p>
          <label className="form-full">Solución del instructor (opcional)
            <textarea rows={4} maxLength={12000} value={value.solution_text}
              onChange={event => onChange({ ...value, solution_text: event.target.value })}
              placeholder="Describe cómo se resuelve el reto. No incluir secretos de producción." />
          </label>
          <p className="field-help">Las pistas y soluciones solo se revelan cuando el backend autoriza su consulta. Los resultados ya registrados conservan las reglas originales.</p>
        </section>
      ) : (
        <p className="ctf-optional-note">Pistas desactivadas para este reto. El estudiante podrá resolverlo directamente con sus instrucciones.</p>
      )}
    </fieldset>
  );
}
