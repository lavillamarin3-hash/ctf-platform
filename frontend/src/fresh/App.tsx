import { Component, ReactNode, useEffect, useState } from 'react';
import { api, token, User, Machine, Scenario, Challenge, Run, Group, Maintenance } from './client';
import { SelectorMaquina } from './SelectorMaquina';
import { FormularioReto } from './FormularioReto';
import { Terminal } from './Terminal';
import './style.css';
import { Login, Shell, Theme, AccountPassword, stateLabel } from './Layout';
import { GuacamoleAdmin } from './GuacamoleAdmin';
import { Modal } from './Modal';
import { UsersAdmin } from './UsersAdmin';

class ErrorBoundary extends Component<{children: ReactNode}, {failed: boolean}> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <main className="fresh"><h1>No se pudo mostrar esta vista</h1><button onClick={() => location.reload()}>Volver a cargar</button></main> : this.props.children; }
}

function FreshApp() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState<Theme>(() => localStorage.getItem('ctf-theme') === 'light' ? 'light' : 'dark');
  function toggleTheme() { setTheme(value => value === 'dark' ? 'light' : 'dark'); }
  useEffect(() => {localStorage.setItem('ctf-theme', theme); document.documentElement.dataset.theme = theme; document.documentElement.style.colorScheme = theme;}, [theme]);
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
  const [form, setForm] = useState<'lab' | 'group' | 'assignment' | 'flag' | 'password' | null>(null);
  const manager = user?.role === 1 || user?.role === 2;
  useEffect(() => setHintText(''), [selected]);
  useEffect(() => { const pop = () => setTab(location.pathname.split('/')[2] || 'retos'); window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop); }, []);
  async function refresh() {
    if (!user || user.must_change_password) return;
    const accessToken = token.get();
    const [c, r, rank] = await Promise.all([api<Challenge[]>('/challenges'), api<Run[]>('/runs'), api<typeof ranking>('/ranking')]);
    if (token.get() !== accessToken) return;
    setChallenges(c); setRuns(r); setRanking(rank);
    if (manager) {
      const [m, s, g, u, l, maintenance] = await Promise.all([api<Machine[]>('/machines'), api<Scenario[]>('/scenarios'), api<Group[]>('/groups'), api<User[]>('/users'), api<Group[]>('/laboratories'), api<Maintenance[]>('/maintenance')]);
      if (token.get() !== accessToken) return;
      setMachines(m); setScenarios(s); setGroups(g); setUsers(u); setLabs(l); setMaintenance(maintenance);
    }
  }
  async function action(work: () => Promise<unknown>, success = 'Operación completada.') {
    setBusy(true); setError(''); setNotice('');
    try { await work(); setNotice(success); await refresh(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => {
    const logout = () => {setUser(null); setChallenges([]); setRuns([]); setMachines([]); setGroups([]); setUsers([]); setLabs([]); setScenarios([]); setMaintenance([]); setRanking([]); setSelected(null); setNewChallenge(false); setForm(null); setFlag(''); setHintText(''); setNotice('');}; window.addEventListener('fresh-logout', logout);
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
  if (!user) return <Login onLogin={setUser} theme={theme} toggleTheme={toggleTheme} />;
  if (user.must_change_password) return <main className="fresh fresh-password-setup" data-theme={theme}><p className="fresh-kicker">PRIMER ACCESO</p><h1>Configura tu contraseña</h1><p>Cambia la contraseña inicial para continuar.</p><AccountPassword onUpdated={setUser}/></main>;

  const challenge = challenges.find(c => c.id === selected);
  const scenarioEnabled = scenarios.some(s => s.strategy === challenge?.strategy && s.enabled);
  const activeRun = runs.find(r => r.challenge_id === selected && ['en_cola','reservada','activa','reiniciando'].includes(r.state));
  const tabs = manager ? ['retos','maquinas','laboratorios',...(user.role === 1 ? ['guacamole'] : []),'grupos','usuarios','corridas','mantenimiento','ranking'] : ['retos','ranking'];
  const activeTab = [...tabs,'cuenta'].includes(tab) ? tab : 'retos';
  function navigate(next:string) {setForm(null); setNewChallenge(false); setTab(next); history.pushState({}, '', `${manager ? '/admin' : '/player'}/${next}`); setError('');}
  return <Shell user={user} tab={activeTab} tabs={tabs} navigate={navigate} logout={() => {void api('/auth/logout', {}).catch(() => {}).finally(() => {token.clear(); window.dispatchEvent(new Event('fresh-logout'));});}} theme={theme} toggleTheme={toggleTheme} machineCount={machines.length} labCount={labs.length} readyLabs={labs.filter(l => l.state === 'ready').length} challengeCount={challenges.length} publishedCount={challenges.filter(c => c.state === 'published').length} liveRuns={runs.filter(r => ['en_cola','reservada','activa','reiniciando'].includes(r.state)).length} notice={notice}>
      {activeTab === 'guacamole' && user.role === 1 && <GuacamoleAdmin />}
      {activeTab === 'cuenta' && <section className="fresh-card"><h2>Mi cuenta</h2><p>{user.username}</p><button onClick={() => setForm('password')}>Cambiar contraseña</button></section>}
      {error && <div role="alert" className="fresh-error">{error} <button onClick={() => void action(refresh, '')}>Reintentar</button></div>}{notice && <p role="status" className="fresh-notice">{notice}</p>}
      {activeTab === 'retos' && <>
        {manager && <button onClick={() => {setError('');setNewChallenge(true);}}>+ Nuevo reto</button>}
        {newChallenge && <Modal title="Nuevo reto" busy={busy} onClose={() => setNewChallenge(false)}><FormularioReto machines={machines} scenarios={scenarios} onBusyChange={setBusy} onSaved={async () => { setNewChallenge(false); await refresh(); }} /></Modal>}
        <div className="fresh-cards">{challenges.map(c => <button className={`fresh-card fresh-challenge ${selected === c.id ? 'selected' : ''}`} onClick={() => setSelected(c.id)} key={c.id}><span className="fresh-kicker">{c.code}</span><h2>{c.name}</h2><p>{c.description || c.strategy}</p><footer><span>{c.difficulty} · {c.points} pts</span><span>{stateLabel(manager ? c.state : c.availability)}</span></footer></button>)}</div>
        {!challenges.length && <section className="fresh-card"><h2>{manager ? 'Empieza por el inventario' : 'Todavía no hay retos asignados'}</h2><p>{manager ? 'Confirma las máquinas, crea laboratorios y grupos; después configura un reto y ejecuta su piloto.' : 'Tu instructor publicará los retos disponibles para tu grupo.'}</p></section>}
        {challenge && <section className="fresh-card"><h2>{challenge.name}</h2><p className="fresh-instructions">{challenge.instructions || 'Consulta la guía del escenario con tu instructor.'}</p>
          {(challenge.resources ?? []).map(resource => <p key={resource.url}><a href={resource.url} target="_blank" rel="noreferrer">{resource.title}</a></p>)}
          {!manager && activeRun?.state === 'activa' && <><div className="fresh-actions">{(challenge.hints ?? []).map(hint => <button key={hint.order} disabled={busy} onClick={() => void action(async () => { const result = await api<{text:string}>(`/runs/${activeRun.id}/hints/${hint.order}`, {}); setHintText(result.text); }, '')}>Pista {hint.order}{hint.penalty ? ` (−${hint.penalty} pts)` : ''}</button>)}</div>{hintText && <p className="fresh-notice">{hintText}</p>}</>}
          {manager ? <><button className="fresh-secondary" onClick={() => {setError('');setForm('assignment');}}>Asignar grupos</button><div className="fresh-actions"><button disabled={busy || !scenarioEnabled} onClick={() => void action(() => api(`/challenges/${challenge.id}/pilot`, {}), 'Prueba en cola. Consulta Corridas para ver el resultado.')}>Ejecutar piloto</button><button disabled={busy || !scenarioEnabled || !challenge.pilot_passed} onClick={() => void action(() => api(`/challenges/${challenge.id}/publish`, {}))}>Publicar</button></div>{!scenarioEnabled && <p className="fresh-help">Integración pendiente: completa las guías de preparación antes de ejecutar un piloto o publicar.</p>}<p>Piloto: {challenge.pilot_passed ? 'aprobado y limpio' : 'pendiente'}</p></> : activeRun ? <>
            <p><strong>{stateLabel(activeRun.state)}</strong> · Corrida {activeRun.id} · Hasta {new Date(activeRun.expires).toLocaleTimeString()}</p>
            {activeRun.state === 'activa' && <><Terminal runId={activeRun.id} /><button onClick={() => {setError('');setForm('flag');}}>Enviar bandera</button></>}
            <button className="fresh-secondary" disabled={busy} onClick={() => void action(() => api(`/runs/${activeRun.id}/close`, {}), 'Cierre solicitado.')}>Cerrar corrida</button>
          </> : <button disabled={busy || user.role !== 3} onClick={() => void action(() => api(`/challenges/${challenge.id}/start`, {}), 'Solicitud recibida. La consola aparecerá cuando el laboratorio esté listo.')}>Iniciar laboratorio</button>}
        </section>}
      </>}
      {activeTab === 'maquinas' && <section className="fresh-card"><p>Inventario conciliado por consola. Cupo efectivo: una corrida por atacante. Marcar disponible confirma tu verificación previa.</p><table><thead><tr><th>Máquina</th><th>Red</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{machines.map(vm => <tr key={vm.id}><td>{vm.name}</td><td>{vm.ip} · VLAN {vm.vlan}</td><td>{stateLabel(vm.state)}{vm.busy ? ' · en uso' : ''}</td><td><button disabled={busy || vm.state === 'dirty'} onClick={() => void action(() => api(`/machines/${vm.id}`, {state:vm.state === 'ready' ? 'mantenimiento' : 'ready'}, 'PATCH'))}>{vm.state === 'ready' ? 'Drenar' : 'Disponible'}</button></td></tr>)}</tbody></table></section>}
      {activeTab === 'laboratorios' && <><button onClick={() => {setError('');setForm('lab');}}>+ Nuevo laboratorio</button>{labs.map(l => <section className="fresh-card" key={l.id}><p>{l.code} · {l.name} · {stateLabel(l.state ?? 'planned')}</p><button disabled={busy} onClick={() => void action(() => api(`/laboratories/${l.id}`, {state:l.state === 'ready' ? 'mantenimiento' : 'ready'}, 'PATCH'))}>{l.state === 'ready' ? 'Poner en mantenimiento' : 'Confirmar disponible'}</button></section>)}</>}
      {activeTab === 'grupos' && <section className="fresh-card"><div className="fresh-section-head"><h2>Grupos</h2><button onClick={() => {setError('');setForm('group');}}>+ Nuevo grupo</button></div>{groups.length ? groups.map(g => <p key={g.id}>{g.code} · {g.name}</p>) : <p>Todavía no hay grupos. Crea uno para asignar los retos a sus jugadores.</p>}</section>}
      {activeTab === 'usuarios' && <UsersAdmin users={users} administrator={user.role === 1} refresh={refresh} />}
      {activeTab === 'corridas' && <section className="fresh-card"><table><thead><tr><th>Corrida</th><th>Reto</th><th>Estado</th><th>Resultado</th></tr></thead><tbody>{runs.map(r => <tr key={r.id}><td>{r.id}{r.pilot ? ' · piloto' : ''}</td><td>{challenges.find(c => c.id === r.challenge_id)?.code}</td><td>{stateLabel(r.state)}</td><td>{r.outcome ? stateLabel(r.outcome) : '—'}</td></tr>)}</tbody></table></section>}
      {activeTab === 'mantenimiento' && <section className="fresh-card"><p>Restaura el snapshot en Prism solo cuando no haya corridas vivas. Después ejecuta la prueba del inyector por consola y confirma aquí.</p>{maintenance.map(m => <article key={m.id}><h3>{machines.find(vm => vm.id === m.machine_id)?.name}</h3><p>{m.reason} · {stateLabel(m.state)}</p><button disabled={busy || !m.tested || m.state === 'confirmado' || user.role !== 1} onClick={() => void action(() => api(`/maintenance/${m.id}/confirm`, {}))}>Confirmar restauración probada</button></article>)}{!maintenance.length && <p>No hay restauraciones pendientes.</p>}</section>}
      {activeTab === 'ranking' && <section className="fresh-card"><table><thead><tr><th>Posición</th><th>Jugador</th><th>Puntos</th><th>Retos</th></tr></thead><tbody>{ranking.map((r,i) => <tr key={r.username}><td>{i+1}</td><td>{r.username}</td><td>{r.points}</td><td>{r.completed}</td></tr>)}</tbody></table></section>}
      {form === 'lab' && <Modal title="Nuevo laboratorio" busy={busy} error={error} onClose={() => {setForm(null);setError('');}}><LabForm machines={machines} busy={busy} save={body => action(async () => {await api('/laboratories',body);setForm(null);})} /></Modal>}
      {form === 'group' && <Modal title="Nuevo grupo" busy={busy} error={error} onClose={() => {setForm(null);setError('');}}><form onSubmit={event => {event.preventDefault();const data = new FormData(event.currentTarget);void action(async () => {await api('/groups',{code:data.get('code'),name:data.get('name'),users:data.getAll('users')});setForm(null);});}}><fieldset disabled={busy} className="fresh-fields"><div className="fresh-grid"><label>Código<input name="code" placeholder="CTF-DEMO-2026" pattern="[A-Z0-9_-]{3,30}" required /></label><label>Nombre<input name="name" minLength={3} maxLength={100} required /></label><label>Jugadores activos<select multiple name="users">{users.filter(u => u.role === 3 && (!u.state || u.state === 'activo')).map(u => <option key={u.id} value={u.id}>{u.username}</option>)}</select></label></div><p className="fresh-help">Mantén Ctrl (o Cmd) para seleccionar varios jugadores.</p><button disabled={busy}>{busy ? 'Guardando…' : 'Crear grupo'}</button></fieldset></form></Modal>}
      {form === 'assignment' && challenge && <Modal title={`Grupos de ${challenge.code}`} busy={busy} error={error} onClose={() => {setForm(null);setError('');}}><form onSubmit={event => {event.preventDefault();const data = new FormData(event.currentTarget);void action(async () => {await api(`/challenges/${challenge.id}/groups`,{groups:data.getAll('groups')},'PUT');setForm(null);});}}><label>Grupos asignados<select name="groups" multiple defaultValue={challenge.groups ?? []} required disabled={busy}>{groups.map(g => <option value={g.id} key={g.id}>{g.code} · {g.name}</option>)}</select></label><p>Selecciona todos los grupos que deben conservar el acceso. Mantén Ctrl (o Cmd) para seleccionar varios.</p><button disabled={busy || !groups.length}>Guardar asignación</button></form></Modal>}
      {form === 'flag' && <Modal title="Enviar bandera" busy={busy} error={error} onClose={() => {setForm(null);setError('');}}>{activeRun?.state === 'activa' ? <form onSubmit={event => {event.preventDefault();void action(async () => {const result = await api<{correct:boolean;points:number}>(`/runs/${activeRun.id}/flag`,{flag});if (!result.correct) throw new Error('La bandera no corresponde a esta corrida.');setFlag('');setForm(null);},'Reto resuelto; la limpieza se ejecutará automáticamente.');}}><label>Bandera de tu corrida<input value={flag} onChange={event => setFlag(event.target.value)} autoComplete="off" placeholder="FLAG{...}" required disabled={busy}/></label><button disabled={busy}>Enviar</button></form> : <p>La corrida ya no está activa. Cierra esta ventana para revisar su estado.</p>}</Modal>}
      {form === 'password' && <Modal title="Cambiar contraseña" busy={busy} onClose={() => setForm(null)}><AccountPassword onBusyChange={setBusy} onUpdated={setUser}/></Modal>}
    </Shell>;
}

function LabForm({ machines, save, busy }: {machines: Machine[]; busy: boolean; save: (body: unknown) => Promise<void>}) {
  const [segment, setSegment] = useState('VLAN30-10.10.30.0/24');
  const [selected, setSelected] = useState<string[]>([]);
  return <form className="fresh-card" onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget); void save({code:data.get('code'),name:data.get('name'),segment,machines:selected}); }}><h2>Nuevo laboratorio</h2><div className="fresh-grid"><label>Código<input name="code" pattern="[A-Z0-9_-]{3,30}" placeholder="LAB-VICTIMAS" required /></label><label>Nombre<input name="name" minLength={3} placeholder="Laboratorio de víctimas" required /></label><label>Segmento<select value={segment} onChange={e => {setSegment(e.target.value); setSelected([]);}}><option>VLAN30-10.10.30.0/24</option><option>VLAN20-10.10.20.0/24</option></select></label><label>Máquinas existentes<SelectorMaquina machines={machines} tipo={segment.startsWith('VLAN20') ? 'atacante' : 'victima'} multiple value={selected} onChange={setSelected} /></label></div><button disabled={busy || !selected.length}>{busy ? 'Guardando…' : 'Crear laboratorio'}</button></form>;
}

export default function FreshRoot() { return <ErrorBoundary><FreshApp /></ErrorBoundary>; }
