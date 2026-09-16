// ============================================================
// GUACAMOLE - FORMULARIOS
// Responsabilidad: edición de usuarios, conexiones y permisos del adaptador.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { User } from "../api";

export function GuacamoleUserForm({
  initial,
  onClose,
  onSave,
}: {
  initial: import("../api").GuacamoleUser | null;
  onClose: () => void;
  onSave: (input: { username: string; password?: string; email?: string | null; full_name?: string | null; disabled?: boolean }, initialUsername?: string) => void;
}) {
  const [username, setUsername] = useState(initial?.username ?? "");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState(initial?.attributes?.["guac-full-name"] ?? "");
  const [email, setEmail] = useState(initial?.attributes?.["guac-email-address"] ?? "");
  const [disabled, setDisabled] = useState(initial?.attributes?.disabled === "true");
  return (
    <div className="modal-backdrop">
      <form className="modal-card" onSubmit={(e) => { e.preventDefault(); if (!username.trim()) return; onSave({ username: username.trim(), password: password || undefined, full_name: fullName.trim() || null, email: email.trim() || null, disabled }, initial?.username); onClose(); }}>
        <div className="modal-head"><div><span className="eyebrow accent">GUACAMOLE</span><h2>{initial ? "Editar usuario remoto" : "Nuevo usuario remoto"}</h2><small>Administración segura desde la plataforma CTF.</small></div><button type="button" className="icon-btn" onClick={onClose}>×</button></div>
        <div className="form-grid">
          <label>Usuario<input value={username} onChange={(e) => setUsername(e.target.value)} disabled={Boolean(initial)} required /></label>
          <label>Nombre completo<input value={fullName} onChange={(e) => setFullName(e.target.value)} /></label>
          <label>Correo<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>{initial ? "Nueva contraseña (opcional)" : "Contraseña"}<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required={!initial} /></label>
        </div>
        {initial && <label className="switch-row"><input type="checkbox" checked={disabled} onChange={(e) => setDisabled(e.target.checked)} /> Cuenta remota deshabilitada</label>}
        <div className="modal-actions"><button type="button" className="secondary-action" onClick={onClose}>Cancelar</button><button className="primary-action">{initial ? "Guardar cambios" : "Crear usuario"}</button></div>
      </form>
    </div>
  );
}

export function GuacamoleConnectionForm({
  initial, onClose, onSave,
}: {
  initial: import("../api").GuacamoleConnection | null;
  onClose: () => void;
  onSave: (input: { name:string; protocol:"ssh"|"rdp"|"vnc"; hostname:string; port:number; username?:string|null; password?:string|null; domain?:string|null; parent_identifier?:string }, identifier?:string) => void;
}) {
  const [name,setName]=useState(initial?.name ?? "");
  const [protocol,setProtocol]=useState<"ssh"|"rdp"|"vnc">(initial?.protocol ?? "ssh");
  const [hostname,setHostname]=useState(initial?.hostname ?? "");
  const [port,setPort]=useState(initial?.port ?? (protocol === "rdp" ? "3389" : protocol === "vnc" ? "5900" : "22"));
  const [username,setUsername]=useState(initial?.parameters?.username ?? "");
  const [password,setPassword]=useState("");
  const [domain,setDomain]=useState(initial?.parameters?.domain ?? "");
  useEffect(()=>{ if(!initial) setPort(protocol === "rdp" ? "3389" : protocol === "vnc" ? "5900" : "22"); },[protocol,initial]);
  const submit=(e:FormEvent)=>{e.preventDefault();if(!name.trim()||!hostname.trim())return;onSave({name:name.trim(),protocol,hostname:hostname.trim(),port:Number(port),username:username.trim()||null,password:password||null,domain:domain.trim()||null,parent_identifier:initial?.parent_identifier||"ROOT"},initial?.identifier);onClose();};
  return <div className="modal-backdrop"><form className="modal-card" onSubmit={submit}><div className="modal-head"><div><span className="eyebrow accent">CONEXIÓN GUACAMOLE</span><h2>{initial?"Editar conexión":"Nueva conexión"}</h2><small>La contraseña queda únicamente en Apache Guacamole.</small></div><button type="button" className="icon-btn" onClick={onClose}>×</button></div><div className="form-grid"><label>Nombre<input value={name} onChange={e=>setName(e.target.value)} required /></label><label>Protocolo<select value={protocol} onChange={e=>setProtocol(e.target.value as "ssh"|"rdp"|"vnc")}><option value="ssh">SSH</option><option value="rdp">RDP</option><option value="vnc">VNC</option></select></label><label>Host / IP<input value={hostname} onChange={e=>setHostname(e.target.value)} placeholder="10.10.30.10" required /></label><label>Puerto<input type="number" min="1" max="65535" value={port} onChange={e=>setPort(e.target.value)} required /></label><label>Usuario remoto<input value={username} onChange={e=>setUsername(e.target.value)} /></label><label>{initial?"Contraseña (opcional)":"Contraseña"}<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required={!initial} minLength={8} /></label><label>Dominio Windows<input value={domain} onChange={e=>setDomain(e.target.value)} placeholder="Opcional para RDP" /></label></div><div className="info-panel glass-panel"><span className="eyebrow">NOTA</span><p>Editar sin contraseña conserva la contraseña actual. Nunca se muestra la contraseña almacenada.</p></div><div className="modal-actions"><button type="button" className="secondary-action" onClick={onClose}>Cancelar</button><button className="primary-action">{initial?"Guardar conexión":"Crear conexión"}</button></div></form></div>
}

export function GuacamolePermissionsForm({ username, initial, connections, onClose, onSave }: { username:string; initial:import("../api").GuacamolePermissionSet; connections:import("../api").GuacamoleConnection[]; onClose:()=>void; onSave:(value:import("../api").GuacamolePermissionSet)=>void; }) {
  const [system,setSystem]=useState<string[]>(initial.system_permissions || []);
  const [byConnection,setByConnection]=useState<Record<string,string[]>>(initial.connection_permissions || {});
  const toggleSystem=(perm:string)=>setSystem(v=>v.includes(perm)?v.filter(x=>x!==perm):[...v,perm]);
  const toggleConn=(id:string,perm:string)=>setByConnection(v=>{const cur=v[id]||[];const next=cur.includes(perm)?cur.filter(x=>x!==perm):[...cur,perm];return {...v,[id]:next};});
  return <div className="modal-backdrop"><div className="modal-card permission-modal"><div className="modal-head"><div><span className="eyebrow accent">PERMISOS GUACAMOLE</span><h2>{username}</h2><small>Permisos del sistema y acceso por conexión.</small></div><button type="button" className="icon-btn" onClick={onClose}>×</button></div><div className="preference-section"><span className="preference-label">Permisos de sistema</span>{["ADMINISTER","CREATE_USER","CREATE_CONNECTION","CREATE_CONNECTION_GROUP"].map(p=><label className="check-row" key={p}><input type="checkbox" checked={system.includes(p)} onChange={()=>toggleSystem(p)} /><span>{p}</span></label>)}<small className="form-help">ADMINISTER convierte la cuenta en superusuario de Guacamole y debe concederse únicamente cuando sea necesario.</small></div><div className="preference-section"><span className="preference-label">Acceso a conexiones</span><div className="permission-table">{connections.length===0?<div className="empty-card"><span>No hay conexiones administradas.</span></div>:connections.map(c=><div className="permission-row" key={c.identifier}><div><strong>{c.name}</strong><small>{c.protocol.toUpperCase()} · {c.hostname}:{c.port}</small></div><div className="permission-checks">{["READ","UPDATE","DELETE","ADMINISTER"].map(p=><label key={p}><input type="checkbox" checked={(byConnection[c.identifier]||[]).includes(p)} onChange={()=>toggleConn(c.identifier,p)} /><span>{p}</span></label>)}</div></div>)}</div></div><div className="modal-actions"><button type="button" className="secondary-action" onClick={onClose}>Cancelar</button><button type="button" className="primary-action" onClick={()=>onSave({system_permissions:system,connection_permissions:byConnection})}>Guardar permisos</button></div></div></div>
}
