import { Component, FormEvent, ReactNode, useEffect, useState } from 'react';
import { api, token, User, Machine, Scenario, Challenge, Run, Group, Maintenance } from './client';
import { SelectorMaquina } from './SelectorMaquina';
import { FormularioReto } from './FormularioReto';
import { Terminal } from './Terminal';
import './style.css';

class ErrorBoundary extends Component<{children: ReactNode}, {failed: boolean}> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <main className="fresh"><h1>No se pudo mostrar esta vista</h1><button onClick={() => location.reload()}>Volver a cargar</button></main> : this.props.children; }
}

function FreshApp() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState(() => location.pathname.split('/')[2] || 'retos');
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [labs, setLabs] = useState<Group[]>([]);
  const [maintenance, setMaintenance] = useState<Maintenance[]>([]);
  const [ranking, setRanking] = useState<{username:string;points:number;completed:number}[]>([]);
  const [selected, setSelected] = useState<string | null>(() => location.pathname.split('/')[2] === 'retos' ? location.pathname.split('/')[3] || null : null);
  const [flag, setFlag] = useState('');
  const [notice, setNotice] = useState('');
  const [hintText, setHintText] = useState('');
  const [busy, setBusy] = useState(false);
  const [newChallenge, setNewChallenge] = useState(false);
  const manager = user?.role === 1 || user?.role === 2;
  useEffect(() => setHintText(''), [selected]);
  useEffect(() => { const pop = () => setTab(location.pathname.split('/')[2] || 'retos'); window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop); }, []);
  async function refresh() {
    if (!user || user.must_change_password) return;
    const [c, r, rank] = await Promise.all([api<Challenge[]>('/challenges'), api<Run[]>('/runs'), api<typeof ranking>('/ranking')]);
    setChallenges(c); setRuns(r); setRanking(rank);
    if (manager) {
      const [m, s, g, u, l, maintenance] = await Promise.all([api<Machine[]>('/machines'), api<Scenario[]>('/scenarios'), api<Group[]>('/groups'), api<User[]>('/users'), api<Group[]>('/laboratories'), api<Maintenance[]>('/maintenance')]);
      setMachines(m); setScenarios(s); setGroups(g); setUsers(u); setLabs(l); setMaintenance(maintenance);
    }
  }
  async function action(work: () => Promise<unknown>, success = 'Operación completada.') {
    setBusy(true); setError(''); setNotice('');
    try { await work(); setNotice(success); await refresh(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => {
    const logout = () => setUser(null); window.addEventListener('fresh-logout', logout);
    if (token.get()) api<User>('/auth/me').then(setUser).catch(() => token.clear()).finally(() => setLoading(false)); else setLoading(false);
    return () => window.removeEventListener('fresh-logout', logout);
  }, []);
  useEffect(() => {
    if (!user || user.must_change_password) return;
    void refresh().catch(e => setError(e.message));
    const timer = window.setInterval(() => { void refresh().catch(e => setError(e.message)); }, 5000);
    return () => clearInterval(timer);
  }, [user]);
  useEffect(() => {
    if (!user || user.must_change_password) return;
    let disposed = false;
    let socket: WebSocket | undefined;
    api('/ranking/ticket', {}).then(() => {
      if (disposed) return;
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/api/v1/ranking/ws`);
      socket.onmessage = () => { void api<typeof ranking>('/ranking').then(setRanking).catch(() => {}); };
    }).catch(() => { /* El refresco periódico mantiene la vista si Redis vuelve. */ });
    return () => { disposed = true; socket?.close(); };
  }, [user]);

  if (loading) return <main className="fresh"><p>Cargando sesión…</p></main>;
  if (!user) return <main className="fresh fresh-login"><section><p className="fresh-kicker">COCIBER / CYBER RANGE</p><h1>Investiga.<br/>Practica.<br/>Demuestra.</h1><p>Tu laboratorio de ciberseguridad, en un solo lugar.</p></section><form className="fresh-card" onSubmit={event => {
    event.preventDefault(); const data = new FormData(event.currentTarget); setError(''); setBusy(true);
    api<{access_token:string;user:User}>('/auth/login', { username:data.get('username'),password:data.get('password') }).then(result => { token.set(result.access_token); setUser(result.user); }).catch(e => setError(e.message)).finally(() => setBusy(false));
  }}><h2>Accede a tu espacio</h2><label>Usuario<input name="username" autoComplete="username" placeholder="Tu usuario asignado" required /></label><label>Contraseña<input name="password" type="password" autoComplete="current-password" required /></label>{error && <p role="alert" className="fresh-error">{error}</p>}<button disabled={busy}>{busy ? 'Validando…' : 'Entrar'}</button></form></main>;

  if (user.must_change_password) return <main className="fresh"><form className="fresh-card" onSubmit={event => {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    void action(async () => { const result = await api<{access_token:string;user:User}>('/auth/password', { current:data.get('current'),new:data.get('new') }); token.set(result.access_token); setUser(result.user); }, 'Contraseña actualizada.');
  }}><h1>Configura tu contraseña</h1><p>Antes de continuar, cambia la contraseña inicial que recibiste.</p><label>Contraseña actual<input type="password" name="current" autoComplete="current-password" required /></label><label>Nueva contraseña<input type="password" name="new" minLength={10} autoComplete="new-password" required /></label>{error && <p role="alert">{error}</p>}<button disabled={busy}>Guardar contraseña</button></form></main>;

  const challenge = challenges.find(c => c.id === selected);
  const activeRun = runs.find(r => r.challenge_id === selected && ['en_cola','reservada','activa','reiniciando'].includes(r.state));
  const tabs = manager ? ['retos','maquinas','laboratorios','grupos','usuarios','corridas','mantenimiento','ranking'] : ['retos','ranking'];
  return <div className="fresh"><header className="fresh-header"><a href="#" className="fresh-brand">COCIBER <span>CTF</span></a><div>{user.username} <button className="fresh-secondary" onClick={() => { void api('/auth/logout', {}).finally(() => { token.clear(); setUser(null); }); }}>Salir</button></div></header>
    <div className="fresh-layout"><nav aria-label="Navegación principal">{tabs.map(t => <button key={t} className={tab === t ? 'selected' : ''} onClick={() => { setTab(t); history.pushState({}, '', `${manager ? '/admin' : '/player'}/${t}`); setError(''); }}>{t === 'maquinas' ? 'Máquinas' : t}</button>)}</nav><main>
      <p className="fresh-kicker">{manager ? 'CONTROL DEL LABORATORIO' : 'TU ESPACIO DE PRÁCTICA'}</p><h1>{tab === 'retos' ? 'Retos de ciberseguridad' : tab}</h1>
      {error && <div role="alert" className="fresh-error">{error} <button onClick={() => void action(refresh, '')}>Reintentar</button></div>}{notice && <p role="status" className="fresh-notice">{notice}</p>}
      {tab === 'retos' && <>
        {manager && <button onClick={() => setNewChallenge(v => !v)}>{newChallenge ? 'Cerrar formulario' : '+ Nuevo reto'}</button>}
        {newChallenge && <FormularioReto machines={machines} scenarios={scenarios} onSaved={async () => { setNewChallenge(false); await refresh(); }} />}
        <div className="fresh-cards">{challenges.map(c => <button className={`fresh-card fresh-challenge ${selected === c.id ? 'selected' : ''}`} onClick={() => setSelected(c.id)} key={c.id}><span className="fresh-kicker">{c.code}</span><h2>{c.name}</h2><p>{c.description || c.strategy}</p><footer><span>{c.difficulty} · {c.points} pts</span><span>{manager ? c.state : c.availability}</span></footer></button>)}</div>
        {!challenges.length && <section className="fresh-card"><h2>{manager ? 'Empieza por el inventario' : 'Todavía no hay retos asignados'}</h2><p>{manager ? 'Confirma las máquinas, crea laboratorios y grupos; después configura un reto y ejecuta su piloto.' : 'Tu instructor publicará los retos disponibles para tu grupo.'}</p></section>}
        {challenge && <section className="fresh-card"><h2>{challenge.name}</h2><p className="fresh-instructions">{challenge.instructions || 'Consulta la guía del escenario con tu instructor.'}</p>
          {(challenge.resources ?? []).map(resource => <p key={resource.url}><a href={resource.url} target="_blank" rel="noreferrer">{resource.title}</a></p>)}
          {!manager && activeRun?.state === 'activa' && <><div className="fresh-actions">{(challenge.hints ?? []).map(hint => <button key={hint.order} disabled={busy} onClick={() => void action(async () => { const result = await api<{text:string}>(`/runs/${activeRun.id}/hints/${hint.order}`, {}); setHintText(result.text); }, '')}>Pista {hint.order}{hint.penalty ? ` (−${hint.penalty} pts)` : ''}</button>)}</div>{hintText && <p className="fresh-notice">{hintText}</p>}</>}
          {manager ? <><form className="fresh-inline" onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); void action(() => api(`/challenges/${challenge.id}/groups`, {groups:data.getAll('groups')}, 'PUT')); }}><label>Grupos<select name="groups" multiple required>{groups.map(g => <option value={g.id} key={g.id}>{g.code}</option>)}</select></label><button disabled={busy}>Asignar</button></form><div className="fresh-actions"><button disabled={busy} onClick={() => void action(() => api(`/challenges/${challenge.id}/pilot`, {}), 'Prueba en cola. Consulta Corridas para ver el resultado.')}>Ejecutar piloto</button><button disabled={busy || !challenge.pilot_passed} onClick={() => void action(() => api(`/challenges/${challenge.id}/publish`, {}))}>Publicar</button></div><p>Piloto: {challenge.pilot_passed ? 'aprobado y limpio' : 'pendiente'}</p></> : activeRun ? <>
            <p><strong>{activeRun.state}</strong> · Corrida {activeRun.id} · Hasta {new Date(activeRun.expires).toLocaleTimeString()}</p>
            {activeRun.state === 'activa' && <><Terminal runId={activeRun.id} /><form className="fresh-inline" onSubmit={event => { event.preventDefault(); void action(async () => { const result = await api<{correct:boolean;points:number}>(`/runs/${activeRun.id}/flag`, {flag}); if (!result.correct) throw new Error('La bandera no corresponde a esta corrida.'); setFlag(''); }, 'Reto resuelto; la limpieza se ejecutará automáticamente.'); }}><label>Bandera de tu corrida<input value={flag} onChange={e => setFlag(e.target.value)} placeholder="FLAG{...}" autoComplete="off" required /></label><button disabled={busy}>Enviar</button></form></>}
            <button className="fresh-secondary" disabled={busy} onClick={() => void action(() => api(`/runs/${activeRun.id}/close`, {}), 'Cierre solicitado.')}>Cerrar corrida</button>
          </> : <button disabled={busy || user.role !== 3} onClick={() => void action(() => api(`/challenges/${challenge.id}/start`, {}), 'Solicitud recibida. La consola aparecerá cuando el laboratorio esté listo.')}>Iniciar laboratorio</button>}
        </section>}
      </>}
      {tab === 'maquinas' && <section className="fresh-card"><p>Inventario conciliado por consola. Cupo efectivo: una corrida por atacante. Marcar disponible confirma tu verificación previa.</p><table><thead><tr><th>Máquina</th><th>Red</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{machines.map(vm => <tr key={vm.id}><td>{vm.name}</td><td>{vm.ip} · VLAN {vm.vlan}</td><td>{vm.state}{vm.busy ? ' · en uso' : ''}</td><td><button disabled={busy || vm.state === 'dirty'} onClick={() => void action(() => api(`/machines/${vm.id}`, {state:vm.state === 'ready' ? 'mantenimiento' : 'ready'}, 'PATCH'))}>{vm.state === 'ready' ? 'Drenar' : 'Disponible'}</button></td></tr>)}</tbody></table></section>}
      {tab === 'laboratorios' && <><LabForm machines={machines} save={body => action(() => api('/laboratories', body))} />{labs.map(l => <section className="fresh-card" key={l.id}><p>{l.code} · {l.name} · {l.state}</p><button disabled={busy} onClick={() => void action(() => api(`/laboratories/${l.id}`, {state:l.state === 'ready' ? 'mantenimiento' : 'ready'}, 'PATCH'))}>{l.state === 'ready' ? 'Poner en mantenimiento' : 'Confirmar disponible'}</button></section>)}</>}
      {tab === 'grupos' && <form className="fresh-card" onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); void action(() => api('/groups', {code:data.get('code'),name:data.get('name'),users:data.getAll('users')})); }}><h2>Nuevo grupo</h2><div className="fresh-grid"><label>Código<input name="code" placeholder="CTF-DEMO-2026" pattern="[A-Z0-9_-]{3,30}" required /></label><label>Nombre<input name="name" minLength={3} placeholder="Demostración técnica" required /></label><label>Jugadores<select multiple name="users">{users.filter(u => u.role === 3).map(u => <option key={u.id} value={u.id}>{u.username}</option>)}</select></label></div><button disabled={busy}>Crear grupo</button>{groups.map(g => <p key={g.id}>{g.code} · {g.name}</p>)}</form>}
      {tab === 'usuarios' && <section className="fresh-card"><h2>Usuarios</h2>{user.role === 1 && <form className="fresh-grid" onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); void action(() => api('/users', {username:data.get('username'),password:data.get('password'),role:Number(data.get('role'))})); }}><label>Usuario<input name="username" placeholder="demo.blue" pattern="[A-Za-z0-9._-]{3,50}" required /></label><label>Contraseña inicial<input name="password" type="password" minLength={10} autoComplete="new-password" required /></label><label>Rol<select name="role"><option value="3">Jugador</option><option value="2">Instructor</option><option value="4">Invitado</option></select></label><button disabled={busy}>Crear usuario</button></form>}{users.map(u => <p key={u.id}>{u.username} · {({1:'Administrador',2:'Instructor',3:'Jugador',4:'Invitado'})[u.role as 1]}</p>)}</section>}
      {tab === 'corridas' && <section className="fresh-card"><table><thead><tr><th>Corrida</th><th>Reto</th><th>Estado</th><th>Resultado</th></tr></thead><tbody>{runs.map(r => <tr key={r.id}><td>{r.id}{r.pilot ? ' · piloto' : ''}</td><td>{challenges.find(c => c.id === r.challenge_id)?.code}</td><td>{r.state}</td><td>{r.outcome ?? '—'}</td></tr>)}</tbody></table></section>}
      {tab === 'mantenimiento' && <section className="fresh-card"><p>Restaura el snapshot en Prism solo cuando no haya corridas vivas. Después ejecuta la prueba del inyector por consola y confirma aquí.</p>{maintenance.map(m => <article key={m.id}><h3>{machines.find(vm => vm.id === m.machine_id)?.name}</h3><p>{m.reason} · {m.state}</p><button disabled={busy || !m.tested || m.state === 'confirmado' || user.role !== 1} onClick={() => void action(() => api(`/maintenance/${m.id}/confirm`, {}))}>Confirmar restauración probada</button></article>)}{!maintenance.length && <p>No hay restauraciones pendientes.</p>}</section>}
      {tab === 'ranking' && <section className="fresh-card"><table><thead><tr><th>Posición</th><th>Jugador</th><th>Puntos</th><th>Retos</th></tr></thead><tbody>{ranking.map((r,i) => <tr key={r.username}><td>{i+1}</td><td>{r.username}</td><td>{r.points}</td><td>{r.completed}</td></tr>)}</tbody></table></section>}
    </main></div></div>;
}

function LabForm({ machines, save }: {machines: Machine[]; save: (body: unknown) => Promise<void>}) {
  const [segment, setSegment] = useState('VLAN30-10.10.30.0/24');
  const [selected, setSelected] = useState<string[]>([]);
  return <form className="fresh-card" onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); void save({code:data.get('code'),name:data.get('name'),segment,machines:selected}); }}><h2>Nuevo laboratorio</h2><div className="fresh-grid"><label>Código<input name="code" pattern="[A-Z0-9_-]{3,30}" placeholder="LAB-VICTIMAS" required /></label><label>Nombre<input name="name" minLength={3} placeholder="Laboratorio de víctimas" required /></label><label>Segmento<select value={segment} onChange={e => {setSegment(e.target.value); setSelected([]);}}><option>VLAN30-10.10.30.0/24</option><option>VLAN20-10.10.20.0/24</option></select></label><label>Máquinas existentes<SelectorMaquina machines={machines} tipo={segment.startsWith('VLAN20') ? 'atacante' : 'victima'} multiple value={selected} onChange={setSelected} /></label></div><button disabled={!selected.length}>Crear laboratorio</button></form>;
}

export default function FreshRoot() { return <ErrorBoundary><FreshApp /></ErrorBoundary>; }
