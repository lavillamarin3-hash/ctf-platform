import { Challenge } from './client';
import { preparation, PreparationInput, PreparationStep } from './preparation';

type Roadmap = ReturnType<typeof preparation>;
export function PreparationBar({roadmap, challenge, challenges, select, open, synced}: {roadmap:Roadmap;challenge?:Challenge;challenges:Challenge[];select:(id:string)=>void;open:()=>void;synced:boolean}) {
  return <section className="fresh-roadmap" aria-label="Recorrido de preparación">
    <div className="fresh-section-head"><div><p className="fresh-kicker">PASO A PASO</p><strong>{roadmap.complete ? 'Preparación completa' : 'Camino a la publicación'}</strong></div><label>Reto en preparación<select value={challenge?.id ?? 'new'} onChange={e=>select(e.target.value)}><option value="new">Nuevo reto</option>{challenges.map(c=><option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label></div>
    <ol className="fresh-roadmap-steps">{roadmap.steps.map((s,i)=><li key={s.id} className={s.done ? 'done' : roadmap.next?.id === s.id ? 'current' : ''} aria-current={roadmap.next?.id === s.id ? 'step' : undefined}><span aria-hidden="true">{s.done ? '✓' : i+1}</span><span>{s.label}<small>{s.done ? 'Completado' : roadmap.next?.id === s.id ? 'Siguiente' : 'Pendiente'}</small></span></li>)}</ol>
    <div className="fresh-section-head"><p className="fresh-help">{synced ? `${roadmap.completed} de ${roadmap.steps.length} pasos completos · según el estado guardado en la plataforma.` : 'Estado sin actualizar. Recupera la conexión antes de continuar.'}</p><button className="fresh-secondary" onClick={open}>Gestionar preparación</button></div>
  </section>;
}

export function PreparationManager({input, roadmap, challenges, select, startNew, act, busy, synced}: {input:PreparationInput;roadmap:Roadmap;challenges:Challenge[];select:(id:string)=>void;startNew:()=>void;act:(step:PreparationStep)=>void;busy:boolean;synced:boolean}) {
  const actionLabel:Record<string,string> = {machines:'Revisar máquinas',labs:'Revisar laboratorios',draft:'Crear borrador',integration:'Ver requisitos',groups:'Asignar grupos',pilot:roadmap.pilotRunning ? 'Ver piloto en curso' : 'Ejecutar piloto',publish:'Publicar reto'};
  return <>
    <div className="fresh-section-head"><h2>{input.challenge ? input.challenge.name : 'Prepara un nuevo reto'}</h2><button disabled={busy} onClick={startNew}>+ Preparar otro reto</button></div>
    <p>Cada paso se comprueba con los datos de la plataforma. Al guardar el borrador se confirma su creación; la publicación requiere completar el recorrido.</p>
    {roadmap.complete && <p className="fresh-notice" role="status">Reto publicado y preparación completa según la plataforma.</p>}
    {roadmap.resourceBusy && <p className="fresh-notice">Hay recursos ocupados. Una nueva solicitud puede quedar en cola hasta que finalice su limpieza.</p>}
    <ol className="fresh-preparation-list">{roadmap.steps.map((s,i)=>{
      const disabled = busy || !synced || (s.id === 'draft' && s.done) || (s.id === 'groups' && !input.challenge) || (s.id === 'pilot' && !roadmap.pilotRunning && !roadmap.canPilot) || (s.id === 'publish' && !roadmap.canPublish);
      return <li className="fresh-card" key={s.id}><span className={`fresh-step-number ${s.done ? 'done' : ''}`}>{s.done ? '✓' : i+1}</span><div><h3>{s.label} <span className="fresh-badge">{s.done ? 'Completado' : 'Pendiente'}</span></h3><p>{s.detail}</p><button className="fresh-secondary" disabled={disabled} onClick={()=>act(s)}>{s.id === 'draft' && s.done ? 'Creado correctamente' : actionLabel[s.id]}</button></div></li>;
    })}</ol>
    <section className="fresh-card" id="preparation-requirements"><h2>Requisitos del escenario</h2><p>{input.challenge ? `${input.challenge.code} · ${input.challenge.strategy}` : 'Selecciona o crea un reto para revisar su integración.'}</p><p>Las máquinas y los laboratorios deben verificarse después de instalar sus servicios. El operador prepara el acceso, las cuentas técnicas y la evidencia; el piloto comprueba la creación y la limpieza.</p><p>Para una práctica gráfica, comprueba también el escritorio real desde Guacamole. Una prueba de puerto o un piloto SSH no certifica RDP. Windows A→B y FTP conservan su integración automática pendiente.</p></section>
    <section className="fresh-card"><h2>Seguimiento de todos los retos</h2><div className="fresh-table-wrap"><table><thead><tr><th>Reto</th><th>Avance</th><th>Siguiente paso</th><th>Acción</th></tr></thead><tbody>{challenges.map(c=>{const r=preparation({...input,challenge:c});return <tr key={c.id}><td>{c.code}<small>{c.name}</small></td><td>{r.completed}/{r.steps.length}</td><td>{r.next?.label ?? 'Completo'}</td><td><button className="fresh-secondary" onClick={()=>select(c.id)}>Continuar</button></td></tr>;})}</tbody></table></div>{!challenges.length && <p>Todavía no hay retos creados.</p>}</section>
  </>;
}
