import { FormEvent, useEffect, useState } from 'react';
import { api } from './client';
import { Modal } from './Modal';

type Connection = {identifier:string;name:string;protocol:string;hostname:string;port:string;username:string;domain:string;active_connections:number;protected:boolean;supported:boolean};
type RemoteUser = {username:string;disabled:boolean;protected:boolean};
type Inventory = {verified:boolean;connections:Connection[];users:RemoteUser[];targets:{hostname:string;name:string}[];ports:Record<string,number[]>};
const base = '/admin/guacamole';

export function GuacamoleAdmin() {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [verified, setVerified] = useState('');
  const [search, setSearch] = useState('');
  const [protocol, setProtocol] = useState('all');
  const [editor, setEditor] = useState<Connection | 'new' | null>(null);
  const [deleting, setDeleting] = useState<Connection | null>(null);
  const [confirmation, setConfirmation] = useState('');
  const [newUser, setNewUser] = useState(false);
  const [access, setAccess] = useState<{username:string;connections:string[];administrator:boolean} | null>(null);
  async function load() {
    setLoading(true); setError('');
    try { setInventory(await api<Inventory>(`${base}/inventory`)); setVerified(new Date().toLocaleTimeString('es-EC')); }
    catch(e) { setError((e as Error).message); setVerified(''); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  async function act(work:() => Promise<unknown>, message = '', refresh = false) {
    setBusy(true); setError(''); setNotice('');
    try { await work(); if (message) setNotice(message); if (refresh) await load(); }
    catch(e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const connections = (inventory?.connections ?? []).filter(c => (protocol === 'all' || c.protocol === protocol) && `${c.name} ${c.hostname}`.toLowerCase().includes(search.toLowerCase()));
  const locked = loading || busy || !verified;
  return <section aria-label="Administración de Guacamole">
    <div className="fresh-toolbar"><div><p>Gestiona el acceso remoto antes de preparar los laboratorios.</p><small>{verified ? `Inventario consultado a las ${verified}` : 'Inventario pendiente de verificación'}</small></div><div className="fresh-actions"><button className="fresh-secondary" disabled={busy || loading} onClick={() => void load()}>{loading ? 'Consultando…' : 'Actualizar inventario'}</button><button disabled={locked} onClick={() => {setEditor('new'); setDeleting(null);}}>+ Nueva conexión</button></div></div>
    {error && <div className="fresh-error" role="alert"><strong>No se pudo completar la consulta u operación.</strong><p>{error}</p><p>Actualiza el inventario antes de repetir una creación. Las conexiones existentes no se han eliminado.</p><button className="fresh-secondary" disabled={busy || loading} onClick={() => void load()}>Reintentar</button></div>}
    {notice && <p className="fresh-notice" role="status">{notice}</p>}
    <div className="fresh-stats"><div><span>Integración</span><strong>{loading ? 'Consultando' : verified ? 'API verificada' : 'Sin verificar'}</strong></div><div><span>Conexiones</span><strong>{inventory?.connections.length ?? '—'}</strong></div><div><span>Cuentas remotas</span><strong>{inventory?.users.length ?? '—'}</strong></div></div>
    {editor && inventory && <Modal title={editor === 'new' ? 'Nueva conexión' : 'Editar conexión'} busy={busy} error={error} onClose={() => {setEditor(null);setError('');}}><ConnectionForm key={editor === 'new' ? 'new' : editor.identifier} current={editor === 'new' ? null : editor} inventory={inventory} busy={locked} close={() => setEditor(null)} save={body => act(async () => { await api(`${base}/connections${editor === 'new' ? '' : `/${encodeURIComponent(editor.identifier)}`}`, body, editor === 'new' ? 'POST' : 'PUT'); setEditor(null); }, 'Conexión guardada en Guacamole. No se modificó el estado de ninguna máquina.', true)} /></Modal>}
    {deleting && <Modal title="Eliminar conexión" busy={busy} error={error} onClose={() => {setDeleting(null);setError('');}}><form className="fresh-card fresh-confirm" onSubmit={e => { e.preventDefault(); void act(async () => { await api(`${base}/connections/${encodeURIComponent(deleting.identifier)}`, {confirmation}, 'DELETE'); setDeleting(null); setConfirmation(''); }, 'Conexión eliminada de Guacamole.', true); }}><h2>Eliminar {deleting.name}</h2><p>Se eliminará esta conexión remota. La máquina virtual se conserva.</p><label>Escribe el nombre exacto<input autoFocus value={confirmation} onChange={e => setConfirmation(e.target.value)} autoComplete="off" /></label><div className="fresh-actions"><button className="fresh-danger" disabled={locked || confirmation !== deleting.name}>Eliminar conexión</button><button type="button" className="fresh-secondary" disabled={busy} onClick={() => setDeleting(null)}>Cancelar</button></div></form></Modal>}
    <section className="fresh-card"><div className="fresh-section-head"><div><p className="fresh-kicker">INVENTARIO REMOTO</p><h2>Conexiones</h2></div><span className="fresh-badge">{connections.length} resultados</span></div>
      <div className="fresh-grid"><label>Buscar conexión<input type="search" placeholder="Nombre o dirección IP" value={search} onChange={e => setSearch(e.target.value)} /></label><label>Protocolo<select value={protocol} onChange={e => setProtocol(e.target.value)}><option value="all">Todos los protocolos</option><option value="ssh">SSH</option><option value="rdp">RDP</option><option value="vnc">VNC (consulta)</option></select></label></div>
      <div className="fresh-table-wrap"><table><thead><tr><th>Conexión</th><th>Destino</th><th>Sesiones</th><th>Acciones</th></tr></thead><tbody>{connections.map(c => <tr key={c.identifier}><td><strong>{c.name}</strong><small>{c.protocol.toUpperCase()}{c.protected ? ' · Automática de corrida' : !c.supported ? ' · Solo consulta' : ''}</small></td><td>{c.hostname || 'Sin detalle'}<small>Puerto {c.port || 'sin detalle'}</small></td><td>{c.active_connections}</td><td><div className="fresh-row-actions"><button className="fresh-secondary" disabled={locked || !c.supported} onClick={() => void act(async () => { const result = await api<{reachable:boolean;message:string}>(`${base}/connections/${encodeURIComponent(c.identifier)}/check`, {}); setNotice(`${c.name}: ${result.message}`); })}>Probar puerto</button><button className="fresh-secondary" disabled={locked || c.protected || !c.supported || c.active_connections > 0} onClick={() => {setEditor(c); setDeleting(null);}}>Editar</button><button className="fresh-text-danger" disabled={locked || c.protected || !c.supported || c.active_connections > 0} onClick={() => {setDeleting(c); setConfirmation(''); setEditor(null);}}>Eliminar</button></div></td></tr>)}</tbody></table></div>
      {!loading && !connections.length && <div className="fresh-empty"><h3>{inventory?.connections.length ? 'No hay coincidencias' : verified ? 'Aún no hay conexiones' : 'Esperando el inventario remoto'}</h3><p>{verified ? 'Puedes crear una conexión SSH o RDP para una máquina del laboratorio.' : 'Comprueba la conexión con Guacamole para ver sus datos reales.'}</p></div>}
      <p className="fresh-help">«Probar puerto» comprueba conectividad desde la API. No verifica credenciales ni el acceso desde guacd y no habilita laboratorios.</p>
    </section>
    <section className="fresh-card"><div className="fresh-section-head"><div><p className="fresh-kicker">ACCESO REMOTO</p><h2>Usuarios de Guacamole</h2></div><button className="fresh-secondary" disabled={locked} onClick={() => setNewUser(v => !v)}>{newUser ? 'Cerrar formulario' : '+ Cuenta remota'}</button></div><p>Estas cuentas pertenecen a Guacamole. Los jugadores del CTF reciben su acceso temporal al iniciar una corrida.</p>
      {newUser && <Modal title="Nueva cuenta remota" busy={busy} error={error} onClose={() => {setNewUser(false);setError('');}}><form className="fresh-grid" onSubmit={e => {e.preventDefault(); const data = new FormData(e.currentTarget); void act(async () => {await api(`${base}/users`, {username:data.get('username'),password:data.get('password')}); setNewUser(false);}, 'Cuenta remota creada. Asigna las conexiones que podrá usar.', true);}}><label>Usuario remoto<input name="username" autoComplete="off" pattern="[A-Za-z0-9][A-Za-z0-9._-]{2,49}" placeholder="operador.demo" required /></label><label>Contraseña<input name="password" type="password" minLength={10} autoComplete="new-password" required /></label><button disabled={locked}>Crear cuenta remota</button></form></Modal>}
      <div className="fresh-table-wrap"><table><thead><tr><th>Usuario</th><th>Tipo / estado</th><th>Acceso</th></tr></thead><tbody>{inventory?.users.map(u => <tr key={u.username}><td>{u.username}</td><td>{u.protected ? 'Cuenta protegida' : u.disabled ? 'Deshabilitada' : 'Activa'}</td><td><button className="fresh-secondary" disabled={locked || u.protected} onClick={() => void act(async () => {const result = await api<{connections:string[];administrator:boolean}>(`${base}/users/${encodeURIComponent(u.username)}/access`); setAccess({...result,username:u.username});})}>Ver permisos</button></td></tr>)}</tbody></table></div>
      {access && <Modal title={`Permisos de ${access.username}`} busy={busy} error={error} onClose={() => {setAccess(null);setError('');}}><form className="fresh-access" onSubmit={e => {e.preventDefault(); const allowed = inventory?.connections.filter(c => c.supported && !c.protected).map(c => c.identifier) ?? []; void act(async () => {await api(`${base}/users/${encodeURIComponent(access.username)}/access`, {connections:access.connections.filter(id => allowed.includes(id))}, 'PUT'); setAccess(null);}, 'Permisos de acceso guardados.');}}><h3>Conexiones de {access.username}</h3>{access.administrator ? <p>Esta cuenta administra Guacamole. Sus permisos globales se revisan en el servidor.</p> : <><p>Selecciona las conexiones que podrá abrir. Se conservan sus demás permisos.</p>{inventory?.connections.filter(c => !c.protected && c.supported).map(c => <label className="fresh-check" key={c.identifier}><input type="checkbox" checked={access.connections.includes(c.identifier)} onChange={e => setAccess({...access,connections:e.target.checked ? [...access.connections,c.identifier] : access.connections.filter(id => id !== c.identifier)})}/>{c.name}</label>)}</>}<div className="fresh-actions"><button disabled={locked || access.administrator}>Guardar acceso</button><button className="fresh-secondary" type="button" disabled={busy} onClick={() => setAccess(null)}>Cerrar</button></div></form></Modal>}
    </section>
  </section>;
}

function ConnectionForm({current,inventory,busy,close,save}:{current:Connection|null;inventory:Inventory;busy:boolean;close:()=>void;save:(body:unknown)=>Promise<void>}) {
  const [name, setName] = useState(current?.name ?? '');
  const [host, setHost] = useState(current?.hostname ?? '');
  const valid = name.trim().length >= 3 && !name.trim().toLowerCase().startsWith('ctf_') && inventory.targets.some(t => t.hostname === host);
  const [protocol, setProtocol] = useState(current?.protocol ?? 'ssh');
  const [port, setPort] = useState(Number(current?.port ?? 22));
  function submit(e:FormEvent<HTMLFormElement>) {
    e.preventDefault(); const data = new FormData(e.currentTarget);
    void save({name:data.get('name'),hostname:data.get('hostname'),protocol,port,username:data.get('username') || null,password:data.get('password') || null,domain:data.get('domain') || null});
  }
  return <section className="fresh-card fresh-editor"><p className="fresh-kicker">{current ? 'EDITAR CONEXIÓN' : 'NUEVA CONEXIÓN'}</p><h2>{current?.name ?? 'Configura el acceso a una máquina'}</h2><form onSubmit={submit}><div className="fresh-grid"><label>Nombre<input name="name" value={name} onChange={e => setName(e.target.value)} minLength={3} maxLength={80} placeholder="LAB-KALI-BLUE · SSH" autoFocus required /></label><label>Máquina<select name="hostname" value={host} onChange={e => setHost(e.target.value)} required><option value="" disabled>Selecciona una máquina</option>{inventory.targets.map(t => <option key={t.hostname} value={t.hostname}>{t.name} · {t.hostname}</option>)}</select></label><label>Protocolo<select value={protocol} onChange={e => {setProtocol(e.target.value); setPort(e.target.value === 'rdp' ? 3389 : 22);}}><option value="ssh">SSH · terminal</option><option value="rdp">RDP · escritorio</option></select></label><label>Puerto<select value={port} onChange={e => setPort(Number(e.target.value))}>{(inventory.ports[protocol] ?? []).map(p => <option key={p} value={p}>{p}{p === 2222 ? ' · práctica LNXVICT' : ''}</option>)}</select></label><label>Usuario remoto<input name="username" autoComplete="off" defaultValue={current?.username} placeholder="Usuario de la VM" maxLength={100} /></label><label>Contraseña remota<input name="password" type="password" autoComplete="new-password" placeholder={current ? 'Vacío: conservar la contraseña actual' : 'Opcional; puede solicitarse al conectar'} /></label>{protocol === 'rdp' && <label>Dominio (opcional)<input name="domain" defaultValue={current?.domain} maxLength={100}/></label>}</div><p className="fresh-help">La contraseña se envía al servidor de Guacamole y nunca se devuelve al inventario. Las conexiones de corrida se administran automáticamente.</p><div className="fresh-actions"><button disabled={busy || !valid}>{busy ? 'Guardando…' : 'Guardar conexión'}</button><button className="fresh-secondary" type="button" disabled={busy} onClick={close}>Cancelar</button></div></form></section>;
}
