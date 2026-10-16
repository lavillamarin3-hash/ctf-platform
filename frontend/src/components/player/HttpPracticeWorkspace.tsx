import { useEffect, useState } from 'react';
import type { Run } from '../../api';
import { request } from '../../services/api/client';
import { LaboratoryRunWorkspace } from './LaboratoryRunWorkspace';

type Result = { correct: boolean; challenge_completed: boolean; awarded_points: number; message: string };
type HttpPracticeInfo = {
  target: string;
  objective: string;
  commands: string[];
  note: string;
  username?: string;
  wordlist?: string[];
};

export function HttpPracticeWorkspace({ run, onClose, onSubmit }: {
  run: Run;
  onClose: (id: number) => Promise<void>;
  onSubmit: (code: string, value: string) => Promise<Result>;
}) {
  const [info, setInfo] = useState<HttpPracticeInfo | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const passwordExercise = run.workspace_strategy === 'http_password_lab';

  useEffect(() => {
    let alive = true;
    setInfo(null);
    setError('');
    request<HttpPracticeInfo>(`/runs/${run.id}/http-practice`)
      .then(data => { if (alive) setInfo(data); })
      .catch(error => {
        if (alive) setError(error instanceof Error ? error.message : 'No se pudieron cargar los pasos de la práctica.');
      });
    return () => { alive = false; };
  }, [run.id, attempt]);

  return <>
    <section className="instruction-box" aria-label="Pasos de la práctica web">
      <h3>{passwordExercise ? 'Adivinación de contraseña web' : 'Descubrimiento de archivos expuestos'}</h3>
      {!info && !error && <p role="status">Cargando los pasos de la práctica…</p>}
      {info && <>
        <p>{info.objective}</p>
        <p>Objetivo HTTP: <strong>{info.target}</strong>
          {info.username && <> · Usuario de práctica: <strong>{info.username}</strong></>}
        </p>
        <p>{info.note}</p>
        <p>Investiga el servicio desde Kali, analiza las respuestas y construye tus propias solicitudes. Puedes desbloquear pistas con descuento de puntos en el panel de ayudas.</p>
        {info.wordlist && info.wordlist.length > 0 && <details>
          <summary>{passwordExercise ? 'Ver diccionario de contraseñas de práctica' : 'Ver lista de rutas para investigar'}</summary>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{info.wordlist.join('\n')}</pre>
        </details>}
      </>}
      {error && <>
        <p role="alert">{error}</p>
        <button type="button" className="secondary-action" onClick={() => setAttempt(value => value + 1)}>Reintentar</button>
      </>}
    </section>
    <LaboratoryRunWorkspace run={run} onClose={onClose} onSubmit={onSubmit} />
  </>;
}
