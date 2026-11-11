import { FormEvent, useState } from 'react';
import { api, User } from './client';
import { Modal } from './Modal';

const roleNames: Record<number,string> = {1:'Administrador',2:'Instructor',3:'Jugador',4:'Invitado'};
const stateNames: Record<string,string> = {activo:'Activo',inactivo:'Inactivo',bloqueado:'Bloqueado'};

export function UsersAdmin({users, administrator, refresh}: {users: User[]; administrator: boolean; refresh: () => Promise<void>}) {
  const [editor, setEditor] = useState<User | 'new' | null>(null);
  const [deleting, setDeleting] = useState<User | null>(null);
  const [confirmation, setConfirmation] = useState('');
  const [search, setSearch] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const visible = users.filter(user => `${user.username} ${roleNames[user.role]}`.toLowerCase().includes(search.toLowerCase()));
  function close() { if (!busy) {setEditor(null); setDeleting(null); setError('');} }
  async function mutate(work: () => Promise<unknown>, message: string) {
    setBusy(true); setError(''); setNotice('');
    try {
      await work(); setEditor(null); setDeleting(null); setNotice(message);
      await refresh();
    } catch (e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  return <section className="fresh-card">
    <div className="fresh-section-head"><div><p className="fresh-kicker">CUENTAS DE LA PLATAFORMA</p><h2>Usuarios</h2></div>{administrator && <button onClick={() => {setError('');setEditor('new');}}>+ Nuevo usuario</button>}</div>
    <p>Una única cuenta administradora. Los demás usuarios pueden ser instructores, jugadores o invitados.</p>
    {notice && <p role="status" className="fresh-notice">{notice}</p>}
    {error && !editor && !deleting && <p role="alert" className="fresh-error">{error}</p>}
    <label>Buscar usuario<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Nombre de usuario o rol" /></label>
    <div className="fresh-table-wrap"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th>{administrator && <th>Acciones</th>}</tr></thead><tbody>{visible.map(user => <tr key={user.id}>
      <td><strong>{user.username}</strong>{user.must_change_password && <small>Cambio de contraseña pendiente</small>}</td><td>{roleNames[user.role]}</td><td>{stateNames[user.state ?? 'activo']}</td>
      {administrator && <td>{user.role === 1 ? <span className="fresh-badge">Cuenta protegida</span> : <div className="fresh-row-actions"><button className="fresh-secondary" disabled={busy} onClick={() => {setError('');setEditor(user);}}>Editar</button><button className="fresh-text-danger" disabled={busy} onClick={() => {setError('');setConfirmation('');setDeleting(user);}}>Eliminar</button></div>}</td>}
    </tr>)}</tbody></table></div>
    {!visible.length && <p>No hay usuarios que coincidan con la búsqueda.</p>}
    {editor && <Modal title={editor === 'new' ? 'Crear usuario' : `Editar ${editor.username}`} onClose={close} busy={busy} error={error}>
      <UserForm key={editor === 'new' ? 'new' : editor.id} current={editor === 'new' ? null : editor} busy={busy} save={body => mutate(() => api(`/users${editor === 'new' ? '' : `/${editor.id}`}`,body,editor === 'new' ? 'POST' : 'PATCH'), editor === 'new' ? 'Usuario creado. Debe cambiar la contraseña al entrar.' : 'Usuario actualizado. Los cambios cierran sus sesiones anteriores.')} />
    </Modal>}
    {deleting && <Modal title={`Eliminar ${deleting.username}`} onClose={close} busy={busy} error={error}>
      <p>La eliminación es permanente. Si tiene historial, la plataforma conservará la cuenta y te indicará que la desactives desde Editar. Sus corridas deben estar cerradas y limpias.</p>
      <form onSubmit={event => {event.preventDefault(); void mutate(() => api(`/users/${deleting.id}`,{confirmation},'DELETE'),'Usuario eliminado.');}}>
        <label>Escribe el nombre exacto<input value={confirmation} onChange={event => setConfirmation(event.target.value)} autoComplete="off" required disabled={busy}/></label>
        <button className="fresh-danger" disabled={busy || confirmation !== deleting.username}>{busy ? 'Eliminando…' : 'Eliminar usuario'}</button>
      </form>
    </Modal>}
  </section>;
}

function UserForm({current,busy,save}:{current:User|null;busy:boolean;save:(body:unknown)=>Promise<void>}) {
  function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = String(data.get('password') ?? '');
    void save({username:data.get('username'),role:Number(data.get('role')),...(current ? {state:data.get('state')} : {}),...(!current || password ? {password} : {})});
  }
  return <form onSubmit={submit}><fieldset disabled={busy} className="fresh-fields"><div className="fresh-grid">
    <label>Usuario<input name="username" defaultValue={current?.username} pattern="[A-Za-z0-9._-]{3,50}" maxLength={50} autoComplete="off" placeholder="demo.blue" required /></label>
    <label>Rol<select name="role" defaultValue={current?.role ?? 3}><option value="3">Jugador</option><option value="2">Instructor</option><option value="4">Invitado</option></select></label>
    {current && <label>Estado<select name="state" defaultValue={current.state ?? 'activo'}><option value="activo">Activo</option><option value="inactivo">Inactivo</option><option value="bloqueado">Bloqueado</option></select></label>}
    <label>{current ? 'Nueva contraseña temporal (opcional)' : 'Contraseña inicial'}<input name="password" type="password" minLength={10} maxLength={256} autoComplete="new-password" required={!current} placeholder={current ? 'Vacío: conservar la actual' : 'Al menos 10 caracteres'} /></label>
  </div><p className="fresh-help">Al asignar una contraseña temporal, el usuario deberá cambiarla al entrar.{current && ' Al dejar de ser jugador se retiran sus grupos; si vuelve a ser jugador, deberá asignarse nuevamente.'}</p><button disabled={busy}>{busy ? 'Guardando…' : current ? 'Guardar cambios' : 'Crear usuario'}</button></fieldset></form>;
}
