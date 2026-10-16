import { FormEvent, useEffect, useRef, useState } from 'react';
import type { Run } from '../../api';
import { request } from '../../services/api/client';
import { KaliPanel } from './KaliPanel';

type SubmissionResult = {
  correct: boolean;
  challenge_completed: boolean;
  awarded_points: number;
  message: string;
};
type VmLogicInfo = {
  target: string;
  base_url: string;
  objective: string;
  answer_fields: Array<{ key: string; label: string; placeholder?: string }>;
  note: string;
};
type AnswerResult = { correct: boolean; flag: string | null; message: string };
type Notice = { kind: 'success' | 'error'; message: string } | null;

export function VmLogicWorkspace({ run, onClose, onSubmit }: {
  run: Run;
  onClose: (runId: number) => Promise<void>;
  onSubmit: (code: string, value: string) => Promise<SubmissionResult>;
}) {
  const currentRun = useRef(run.id);
  currentRun.current = run.id;
  const [info, setInfo] = useState<VmLogicInfo | null>(null);
  const [loadError, setLoadError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [validatedFlag, setValidatedFlag] = useState('');
  const [notice, setNotice] = useState<Notice>(null);
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState('');
  const [expired, setExpired] = useState(Date.parse(run.expires_at) <= Date.now());

  useEffect(() => {
    setAnswers({});
    setValidatedFlag('');
    setNotice(null);
    setResult(null);
    setBusy(false);
    setNotes('');
  }, [run.id]);

  useEffect(() => {
    let alive = true;
    setInfo(null);
    setLoadError('');
    request<VmLogicInfo>(`/runs/${run.id}/vm-logic`)
      .then(data => { if (alive) setInfo(data); })
      .catch(error => {
        if (alive) setLoadError(error instanceof Error ? error.message : 'No se pudo cargar el ejercicio.');
      });
    return () => { alive = false; };
  }, [run.id, attempt]);

  useEffect(() => {
    const check = () => setExpired(Date.parse(run.expires_at) <= Date.now());
    check();
    const timer = window.setInterval(check, 1000);
    return () => window.clearInterval(timer);
  }, [run.expires_at]);

  const perform = async (action: () => Promise<void>) => {
    const runId = run.id;
    setBusy(true);
    setNotice(null);
    try { await action(); }
    catch (error) {
      if (currentRun.current === runId) setNotice({ kind: 'error', message: error instanceof Error ? error.message : 'No se pudo completar la operación.' });
    } finally {
      if (currentRun.current === runId) setBusy(false);
    }
  };

  const validate = (event: FormEvent) => {
    event.preventDefault();
    if (busy || Date.parse(run.expires_at) <= Date.now()) return;
    const runId = run.id;
    setValidatedFlag('');
    setResult(null);
    void perform(async () => {
      const response = await request<AnswerResult>(`/runs/${runId}/vm-logic/answer`, {
        method: 'POST', body: JSON.stringify(answers),
      });
      if (currentRun.current !== runId) return;
      setNotice({ kind: response.correct ? 'success' : 'error', message: response.message });
      setValidatedFlag(response.correct ? response.flag ?? '' : '');
    });
  };

  const registerPoints = () => {
    if (busy || !validatedFlag || Date.parse(run.expires_at) <= Date.now()) return;
    const runId = run.id;
    void perform(async () => {
      const response = await onSubmit(run.challenge_code, validatedFlag);
      if (currentRun.current !== runId) return;
      setResult(response);
      setNotice({ kind: response.correct ? 'success' : 'error', message: response.message });
    });
  };

  return <article className="laboratory-run-workspace" aria-label="Investigación con máquinas virtuales">
    <header className="laboratory-run-heading">
      <div>
        <span className="eyebrow accent">INVESTIGACIÓN · CORRIDA {run.id}</span>
        <h2>{run.challenge_code}</h2>
        <p>Disponible hasta {new Date(run.expires_at).toLocaleString('es-ES')}</p>
      </div>
      <span className={`laboratory-state ${expired ? 'pending' : 'connected'}`}>
        <span className="status-dot" />{expired ? 'Tiempo agotado' : 'Práctica activa'}
      </span>
    </header>

    {!info && !loadError && <p role="status">Cargando el objetivo del ejercicio…</p>}
    {loadError && <div className="instruction-box">
      <p role="alert">{loadError}</p>
      <button type="button" className="secondary-action" disabled={busy || expired} onClick={() => setAttempt(value => value + 1)}>Reintentar</button>
    </div>}

    {info && <>
      <section className="instruction-box" aria-label="Objetivo de la investigación">
        <h3>Objetivo</h3>
        <p>{info.objective}</p>
        <p>Víctima: <strong>{info.target}</strong></p>
        <p style={{ overflowWrap: 'anywhere' }}>URL inicial: <code>{info.base_url}</code></p>
        {info.note && <p>{info.note}</p>}
      </section>

      {expired
        ? <section className="embedded-terminal-panel terminal-integration-notice"><h3>La corrida ha caducado</h3><p>La conexión remota se desconectó. Cierra el ejercicio para iniciar otra corrida.</p></section>
        : <KaliPanel key={run.id} run={run} />}

      <section className="laboratory-flag-workspace" aria-label="Resultados de la investigación">
        <form onSubmit={validate}>
          <span className="eyebrow accent">TU ANÁLISIS</span>
          <h3>Presenta tus resultados</h3>
          <p>Investiga desde Kali y completa los datos encontrados en el servicio de la víctima.</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
            {info.answer_fields.map(field => <label className="lab-notes-label" htmlFor={`vm-answer-${run.id}-${field.key}`} key={field.key}>
              {field.label}
              <input id={`vm-answer-${run.id}-${field.key}`} className="lab-flag-candidate" required maxLength={512}
                disabled={busy || expired || Boolean(result?.challenge_completed)} autoComplete="off" spellCheck={false}
                style={{ display: 'block', width: '100%' }} placeholder={field.placeholder} value={answers[field.key] ?? ''}
                onChange={event => {
                  setAnswers(previous => ({ ...previous, [field.key]: event.target.value }));
                  setValidatedFlag(''); setNotice(null); setResult(null);
                }} />
            </label>)}
          </div>
          <button type="submit" className="primary-action" style={{ marginTop: '1rem' }} disabled={busy || expired || !info.answer_fields.length || Boolean(result?.challenge_completed)}>
            {busy ? 'Procesando…' : 'Validar respuestas'}
          </button>
        </form>

        {validatedFlag && !result?.challenge_completed && <div className="instruction-box">
          <p>Respuestas correctas. Registra los puntos para completar el reto.</p>
          <button type="button" className="primary-action" disabled={busy || expired} onClick={registerPoints}>Registrar puntos</button>
        </div>}
        {notice && <p className={`laboratory-feedback ${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.message}</p>}
        {result?.challenge_completed && <p className="laboratory-completion">Reto completado · +{result.awarded_points} pts</p>}

        <label className="lab-notes-label" htmlFor={`vm-notes-${run.id}`}>Bloc de análisis (se descarta al salir)</label>
        <textarea id={`vm-notes-${run.id}`} className="lab-notebook" value={notes} onChange={event => setNotes(event.target.value)} placeholder="Anota tus observaciones y evidencias." />
      </section>
    </>}

    <footer className="laboratory-run-footer">
      <span>Al cerrar se desconecta el acceso y se limpia la práctica de esta corrida.</span>
      <button type="button" className="table-action danger" disabled={busy} onClick={() => void perform(() => onClose(run.id))}>Cerrar ejercicio</button>
    </footer>
  </article>;
}
