import { useEffect, useState } from 'react';
import type { Run } from '../../api';
import { request } from '../../services/api/client';
import { LaboratoryRunWorkspace } from './LaboratoryRunWorkspace';

type PortalInfo = {
  title: string;
  portal_url?: string | null;
  mode: string;
  objective: string;
  note: string;
  terminal_required?: boolean;
  target_host?: string;
  port_scope?: string;
};
type Result = { correct: boolean; challenge_completed: boolean; awarded_points: number; message: string };

export function ExternalWebWorkspace({ run, onClose, onSubmit }: {
  run: Run;
  onClose: (id: number) => Promise<void>;
  onSubmit: (code: string, value: string) => Promise<Result>;
}) {
  const [info, setInfo] = useState<PortalInfo | null>(null);
  const [flag, setFlag] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const [now, setNow] = useState(Date.now());
  const expired = new Date(run.expires_at).getTime() <= now;

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let alive = true;
    setInfo(null);
    setError('');
    request<PortalInfo>(`/runs/${run.id}/external-web`)
      .then(data => { if (alive) setInfo(data); })
      .catch(e => { if (alive) setError(e instanceof Error ? e.message : 'No se pudo cargar el portal.'); });
    return () => { alive = false; };
  }, [run.id, retry]);

  async function perform(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError('');
    setMessage('');
    try { await action(); }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudo completar la operación.'); }
    finally { setBusy(false); }
  }

  if (!info) return <section className="glass-panel external-web-workspace" aria-label="Ejercicio Operación Cóndor">
    <h3>Operación Cóndor</h3>
    {error ? <p role="alert">{error}</p> : <p role="status">Preparando las instrucciones del ejercicio…</p>}
    <div className="row-actions">
      {error && !expired && <button type="button" className="secondary-action" disabled={busy} onClick={() => setRetry(value => value + 1)}>Reintentar carga</button>}
      <button type="button" className="secondary-action" disabled={busy} onClick={() => void perform(() => onClose(run.id))}>Cerrar ejercicio</button>
    </div>
  </section>;

  if (info.terminal_required) return <div className="external-web-ssh-layout">
    <section className="glass-panel external-web-workspace external-web-mission" aria-label="Misión de reconocimiento Operación Cóndor">
      <div className="external-web-heading">
        <div><span className="eyebrow accent">MISIÓN WEB DESDE KALI · CORRIDA {run.id}</span><h3>{info.title}</h3></div>
        <span className="muted-chip">{expired ? 'Tiempo agotado' : 'Investiga desde SSH'}</span>
      </div>
      <p>{info.objective}</p>
      <dl className="external-web-target">
        <div><dt>Única IP autorizada</dt><dd><code>{info.target_host || 'No disponible'}</code></dd></div>
        <div><dt>Puertos autorizados</dt><dd><code>{info.port_scope || 'No disponible'}</code></dd></div>
      </dl>
      <ol className="external-web-steps">
        <li>Abre la terminal SSH de Kali que aparece debajo.</li>
        <li>Identifica el servicio HTTP únicamente en la IP y los puertos asignados.</li>
        <li>Investiga la página y sus pistas; descubre cómo acceder al centro de mando.</li>
        <li>Publica un comunicado, copia la flag y envíala en el panel del laboratorio.</li>
      </ol>
      {info.target_host && info.port_scope ? <details className="external-web-discovery">
        <summary>Comandos para empezar el reconocimiento</summary>
        <p>Ejecuta en Kali y revisa qué puerto responde con un servicio web:</p>
        <pre><code>{`nmap -sV -p ${info.port_scope} ${info.target_host}`}</code></pre>
        <p>Sustituye PUERTO por el que identifiques en el resultado para consultar la página:</p>
        <pre><code>{`curl -i http://${info.target_host}:PUERTO/`}</code></pre>
        <p>Puedes continuar con herramientas de terminal o abrir esa dirección en el navegador de un equipo conectado al laboratorio.</p>
      </details> : <p role="alert">No están disponibles los datos del objetivo. Consulta al instructor antes de investigar.</p>}
      <p className="external-web-note">{info.note}</p>
      {expired && <p role="status">El plazo terminó. Consulta la solución y el puntaje de repaso en el panel de ayudas.</p>}
    </section>
    <LaboratoryRunWorkspace run={run} onClose={onClose} onSubmit={onSubmit} />
  </div>;

  return <section className="glass-panel external-web-workspace" aria-label="Ejercicio Operación Cóndor">
    <div className="external-web-heading">
      <div><span className="eyebrow accent">PORTAL WEB · CORRIDA {run.id}</span><h3>{info?.title ?? 'Operación Cóndor'}</h3></div>
      <span className="muted-chip">{expired ? 'Tiempo agotado' : 'Sesión del ejercicio activa'}</span>
    </div>
    {info && <>
      <p>{info.objective}</p>
      <p>{info.note}</p>
      {!expired && info.portal_url && <a className="primary-action" href={info.portal_url} target="_blank" rel="noopener noreferrer">Abrir Operación Cóndor ↗</a>}
      {info.portal_url && <p className="external-web-address">Dirección del portal: <code>{info.portal_url}</code></p>}
      <ol className="external-web-steps">
        <li>Explora las noticias del portal y encuentra las pistas de acceso.</li>
        <li>Prueba las candidatas del laboratorio e ingresa al centro de mando.</li>
        <li>Publica un comunicado y copia la flag que aparece después.</li>
        <li>Regresa a esta pestaña y registra la flag para obtener los puntos.</li>
      </ol>
    </>}
    {expired && <p role="status">El plazo terminó. Consulta la solución y el puntaje de repaso en el panel de ayudas.</p>}
    <form onSubmit={event => {
      event.preventDefault();
      if (expired || !flag.trim()) return;
      void perform(async () => {
        const result = await onSubmit(run.challenge_code, flag.trim());
        setMessage(result.message);
      });
    }}>
      <label htmlFor={`external-flag-${run.id}`}>Flag obtenida después de publicar</label>
      <input id={`external-flag-${run.id}`} value={flag} onChange={event => setFlag(event.target.value)} required maxLength={2000} autoComplete="off" spellCheck={false} disabled={busy || expired} placeholder="COCIBER{…}" />
      <div className="row-actions">
        <button className="primary-action" disabled={busy || expired || !flag.trim()}>Registrar flag</button>
        <button type="button" className="secondary-action" disabled={busy} onClick={() => void perform(() => onClose(run.id))}>Cerrar ejercicio</button>
      </div>
    </form>
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
