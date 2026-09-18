// ============================================================
// VISTA: ManagementGuacamole
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { createElement } from "react";
import { Icon, StatCard } from "../../components/common";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementGuacamole({ controller }: { controller: ManagementController }) {
  // Estado y datos que esta vista presenta.
  const {
    groups, guacamoleConnections, guacamoleMode, guacamoleTested,
    guacamoleUsers, guacamoleStatus, published, draft,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    setGuacamoleUserEditing, setGuacamoleFormOpen, setGuacamoleConnectionEditing, setGuacamoleConnectionFormOpen,
    loadGuacamole, deleteGuacamoleManagedConnection, openGuacamolePermissions, deleteGuacamoleManagedUser,
  } = controller;
  return (
<section>
    <div className="page-heading"><div><span className="eyebrow accent">INTEGRACIÓN</span><h1>Apache Guacamole</h1><p>Administra usuarios, conexiones y permisos directamente desde la plataforma CTF.</p></div><div className="page-actions"><button className="secondary-action" onClick={()=>void loadGuacamole()}>Actualizar</button><button className="primary-action" onClick={()=>{setGuacamoleConnectionEditing(null);setGuacamoleConnectionFormOpen(true)}}>+ Nueva conexión</button></div></div>
    <div className="stats-grid"><StatCard label="Estado" value={guacamoleMode === "stub" ? "STUB" : "REAL"} helper={guacamoleTested?"Conexión verificada":"Pendiente"} icon="settings" accent="purple"/><StatCard label="Servidor" value="192.168.146.132" helper="Puerto 8080 · Guacamole" icon="lab" accent="blue"/><StatCard label="Conexiones" value={guacamoleConnections.length} helper="Administradas desde CTF" icon="arrow" accent="green"/><StatCard label="Usuarios" value={guacamoleUsers.length} helper="Cuentas remotas" icon="users" accent="cyan"/></div>
    <section className="table-panel glass-panel" style={{marginTop:"13px"}}><div className="panel-head"><div><span className="eyebrow">CONEXIONES</span><h3>Conexiones remotas</h3><small>El backend administra la API de Guacamole; el navegador nunca recibe el token de servicio.</small></div></div><table><thead><tr><th>Nombre</th><th>Protocolo</th><th>Host</th><th>Puerto</th><th>Activas</th><th>Acciones</th></tr></thead><tbody>{guacamoleConnections.map(c=><tr key={c.identifier}><td><strong>{c.name}</strong></td><td>{c.protocol.toUpperCase()}</td><td>{c.hostname||"—"}</td><td>{c.port||"—"}</td><td>{c.active_connections}</td><td><div className="row-actions"><button className="table-action" onClick={()=>{setGuacamoleConnectionEditing(c);setGuacamoleConnectionFormOpen(true)}}>Editar</button><button className="table-action danger" onClick={()=>void deleteGuacamoleManagedConnection(c)} disabled={c.active_connections>0}>Eliminar</button></div></td></tr>)}</tbody></table>{guacamoleConnections.length===0&&<div className="empty-card"><strong>No hay conexiones administradas</strong><span>Crea la primera conexión para una VM del cyber range.</span></div>}</section>
    <section className="table-panel glass-panel guac-groups-panel" style={{marginTop:"13px"}}><div className="panel-head"><div><span className="eyebrow">GRUPOS SINCRONIZADOS</span><h3>Grupos académicos en Guacamole</h3><small>Cada grupo CTF se refleja como User Group de Guacamole para heredar permisos de acceso remoto.</small></div></div><div className="guac-group-grid">{groups.map(g=><div className="guac-group-card" key={g.id}><span className="group-list-icon"><Icon name="users" /></span><div><strong>{g.code}</strong><small>{g.name}</small></div><span className="sync-pill"><span className="status-dot" /> Sincronizado</span></div>)}{groups.length===0&&<div className="empty-card compact"><strong>Aún no hay grupos académicos</strong><span>Al crear un grupo desde CTF se creará su User Group en Guacamole.</span></div>}</div></section>
    <section className="table-panel glass-panel" style={{marginTop:"13px"}}><div className="panel-head"><div><span className="eyebrow">USUARIOS</span><h3>Administración de cuentas remotas</h3></div><button className="secondary-action" onClick={()=>{setGuacamoleUserEditing(null);setGuacamoleFormOpen(true)}}>+ Nuevo usuario</button></div><table><thead><tr><th>Usuario</th><th>Nombre</th><th>Correo</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{guacamoleUsers.map(remote=><tr key={remote.username}><td><strong>{remote.username}</strong></td><td>{remote.attributes?.["guac-full-name"]||"—"}</td><td>{remote.attributes?.["guac-email-address"]||"—"}</td><td><span className={remote.attributes?.disabled === "true" ? "status-draft":"status-published"}>{remote.attributes?.disabled === "true"?"Deshabilitado":"Activo"}</span></td><td><div className="row-actions"><button className="table-action" onClick={()=>{setGuacamoleUserEditing(remote);setGuacamoleFormOpen(true)}}>Editar</button><button className="table-action" onClick={()=>void openGuacamolePermissions(remote.username)}>Permisos</button><button className="table-action danger" disabled={remote.username===guacamoleStatus?.username} onClick={()=>void deleteGuacamoleManagedUser(remote)}>Eliminar</button></div></td></tr>)}</tbody></table></section>
    <div className="info-panel glass-panel" style={{marginTop:"13px"}}><span className="eyebrow">MODELO DE PERMISOS</span><p>Los permisos de sistema de Guacamole y los permisos por conexión se administran independientemente del rol CTF. <strong>ADMINISTER</strong> es el permiso de superusuario de Guacamole.</p></div>
  </section>
  );
}
