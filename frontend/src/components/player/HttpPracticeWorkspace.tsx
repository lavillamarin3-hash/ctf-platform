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
  const [copyNotice, setCopyNotice] = useState('');
  const passwordExercise = run.workspace_strategy === 'http_password_lab';

  useEffect(() => {
    let alive = true;
    setInfo(null);
    setError('');
    setCopyNotice('');
    request<HttpPracticeInfo>(`/runs/${run.id}/http-practice`)
      .then(data => { if (alive) setInfo(data); })
      .catch(error => {
        if (alive) setError(error instanceof Error ? error.message : 'No se pudieron cargar los pasos de la práctica.');
      });
    return () => { alive = false; };
  }, [run.id, attempt]);

  const copyCommand = async (command: string, step: number) => {
    try {
      await navigator.clipboard.writeText(command);
      setCopyNotice(`Paso ${step} copiado. Pégalo en la terminal Kali.`);
    } catch {
      setCopyNotice('Selecciona el comando y cópialo manualmente con Ctrl+C.');
    }
  };

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
        <p>Ejecuta estos comandos en Kali, uno por uno. Revisa las respuestas del servicio, copia la flag encontrada y envíala abajo.</p>
        {info.commands.map((command, index) => <div key={index} style={{ margin: '0.75rem 0' }}>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{command}</pre>
          <button type="button" className="secondary-action" onClick={() => void copyCommand(command, index + 1)}>Copiar paso {index + 1}</button>
        </div>)}
        {info.wordlist && info.wordlist.length > 0 && <details>
          <summary>{passwordExercise ? 'Ver diccionario de contraseñas de práctica' : 'Ver lista de rutas para investigar'}</summary>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{info.wordlist.join('\n')}</pre>
        </details>}
        {copyNotice && <p role="status">{copyNotice}</p>}
      </>}
      {error && <>
        <p role="alert">{error}</p>
        <button type="button" className="secondary-action" onClick={() => setAttempt(value => value + 1)}>Reintentar</button>
      </>}
    </section>
    <LaboratoryRunWorkspace run={run} onClose={onClose} onSubmit={onSubmit} />
  </>;
}
