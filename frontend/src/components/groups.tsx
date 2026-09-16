// ============================================================
// GESTIÓN DE GRUPOS
// Responsabilidad: grupos académicos + sincronización remota indicada por backend.
// ============================================================
import { createElement, useCallback, useEffect, useMemo, useState } from "react";
import { api, Challenge, StudentGroup, User } from "../api";
import { Icon, StatCard } from "./common";

export function GroupManagement({
  isAdmin,
  onMessage,
}: { isAdmin: boolean; onMessage: (message: string) => void }) {
  const [groups, setGroups] = useState<StudentGroup[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [memberId, setMemberId] = useState("");
  const [challengeCode, setChallengeCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<import("../api").ProgressRow[]>([]);
  const [laboratories, setLaboratories] = useState<import("../api").BackendLaboratory[]>([]);
  const [guacamoleConnections, setGuacamoleConnections] = useState<import("../api").GuacamoleConnection[]>([]);
  const [remoteConnections, setRemoteConnections] = useState<import("../api").StudentRemoteConnection[]>([]);
  const [selectedVmId, setSelectedVmId] = useState("");
  const [sourceConnectionId, setSourceConnectionId] = useState("");

  const load = useCallback(async () => {
    try {
      const [g, u, c, labs, conns] = await Promise.all([
        api.groups(),
        api.visibleUsers(),
        api.challenges(),
        isAdmin ? api.laboratories() : Promise.resolve([] as import("../api").BackendLaboratory[]),
        isAdmin ? api.guacamoleConnections() : Promise.resolve([] as import("../api").GuacamoleConnection[]),
      ]);
      setGroups(g);
      setUsers(u.filter((x) => x.role === "player" && x.is_active));
      setChallenges(c);
      setLaboratories(labs);
      setGuacamoleConnections(conns);
      setSelectedId((current) => current && g.some((x) => x.id === current) ? current : (g[0]?.id ?? null));
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo cargar los grupos");
    }
  }, [onMessage]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!selectedId) { setProgress([]); setRemoteConnections([]); return; }
    void api.progressReport(selectedId)
      .then(setProgress)
      .catch((err) => onMessage(err instanceof Error ? err.message : "No se pudo cargar el seguimiento"));
    if (isAdmin) {
      void api.listGroupRemoteConnections(selectedId)
        .then(setRemoteConnections)
        .catch(() => setRemoteConnections([]));
    } else {
      setRemoteConnections([]);
    }
  }, [selectedId, isAdmin, onMessage]);

  const selected = groups.find((g) => g.id === selectedId) ?? null;
  const availableMembers = useMemo(
    () => selected ? users.filter((u) => !selected.members.some((m) => m.user_id === u.id)) : users,
    [selected, users],
  );
  const availableChallenges = useMemo(
    () => selected ? challenges.filter((c) => !selected.challenges.some((x) => x.challenge_id === c.id)) : challenges,
    [selected, challenges],
  );
  const availableVms = useMemo(
    () => laboratories.flatMap((lab) => lab.vms.map((vm) => ({ ...vm, laboratory_code: lab.code || lab.name }))),
    [laboratories],
  );
  const createRemoteConnections = async () => {
    if (!selected || !selectedVmId || !sourceConnectionId || !isAdmin) return;
    setBusy(true);
    try {
      const created = await api.createGroupRemoteConnections(selected.id, { vm_id: Number(selectedVmId), source_connection_id: sourceConnectionId });
      setRemoteConnections(created);
      onMessage(`Se crearon/verificaron ${created.length} conexiones individuales en Guacamole.`);
      await load();
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudieron crear las conexiones del grupo");
    } finally { setBusy(false); }
  };

  const resetForm = () => {
    setEditingId(null); setName(""); setCode(""); setDescription("");
  };

  const saveGroup = async () => {
    if (!name.trim() || !code.trim() || !isAdmin) return;
    setBusy(true);
    try {
      const payload = { name: name.trim(), code: code.trim().toUpperCase(), description: description.trim(), is_active: true };
      const g = editingId ? await api.updateGroup(editingId, payload) : await api.createGroup(payload);
      setGroups((current) => editingId ? current.map((item) => item.id === g.id ? g : item) : [...current, g]);
      setSelectedId(g.id);
      resetForm();
      onMessage(editingId ? "Grupo actualizado y sincronizado con Guacamole." : "Grupo creado en CTF y en Guacamole.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo guardar el grupo");
    } finally { setBusy(false); }
  };

  const editGroup = () => {
    if (!selected || !isAdmin) return;
    setEditingId(selected.id); setName(selected.name); setCode(selected.code); setDescription(selected.description);
  };

  const removeGroup = async () => {
    if (!selected || !isAdmin) return;
    if (!window.confirm(`¿Eliminar el grupo ${selected.code} de CTF y Guacamole?`)) return;
    setBusy(true);
    try {
      await api.deleteGroup(selected.id);
      const remaining = groups.filter((g) => g.id !== selected.id);
      setGroups(remaining); setSelectedId(remaining[0]?.id ?? null); resetForm();
      onMessage("Grupo eliminado de CTF y Guacamole.");
    } catch (err) { onMessage(err instanceof Error ? err.message : "No se pudo eliminar el grupo"); }
    finally { setBusy(false); }
  };

  const addMember = async () => {
    if (!selected || !memberId || !isAdmin) return;
    setBusy(true);
    try {
      const g = await api.addGroupMember(selected.id, Number(memberId));
      setGroups((current) => current.map((item) => item.id === g.id ? g : item));
      setMemberId("");
      onMessage("Estudiante agregado al grupo y sincronizado con Guacamole.");
    } catch (err) { onMessage(err instanceof Error ? err.message : "No se pudo agregar el estudiante"); }
    finally { setBusy(false); }
  };

  const removeMember = async (id: number) => {
    if (!selected || !isAdmin) return;
    setBusy(true);
    try {
      const g = await api.removeGroupMember(selected.id, id);
      setGroups((current) => current.map((item) => item.id === g.id ? g : item));
      onMessage("Estudiante retirado del grupo y de Guacamole.");
    } catch (err) { onMessage(err instanceof Error ? err.message : "No se pudo retirar el estudiante"); }
    finally { setBusy(false); }
  };

  const assign = async () => {
    if (!selected || !challengeCode) return;
    setBusy(true);
    try {
      const g = await api.assignChallengeGroup(challengeCode, selected.id);
      setGroups((current) => current.map((item) => item.id === g.id ? g : item));
      setChallengeCode("");
      onMessage("Reto asignado al grupo y permisos remotos sincronizados.");
    } catch (err) { onMessage(err instanceof Error ? err.message : "No se pudo asignar el reto"); }
    finally { setBusy(false); }
  };

  const unassign = async (challenge: string) => {
    if (!selected) return;
    setBusy(true);
    try {
      const g = await api.unassignChallengeGroup(challenge, selected.id);
      setGroups((current) => current.map((item) => item.id === g.id ? g : item));
      onMessage("Reto retirado del grupo.");
    } catch (err) { onMessage(err instanceof Error ? err.message : "No se pudo retirar el reto"); }
    finally { setBusy(false); }
  };

  return <section className="groups-page">
    <div className="page-heading groups-heading">
      <div>
        <span className="eyebrow accent">ORGANIZACIÓN ACADÉMICA</span>
        <h1>Grupos de estudiantes</h1>
        <p>Una sola estructura académica controla estudiantes, retos y acceso remoto. Cada grupo se crea y sincroniza también en Guacamole.</p>
      </div>
      <div className="page-actions"><button className="secondary-action" onClick={() => void load()} disabled={busy}>Actualizar</button></div>
    </div>

    <div className="stats-grid">
      <StatCard label="Grupos" value={groups.length} helper="CTF + Guacamole" icon="users" accent="purple" />
      <StatCard label="Estudiantes" value={users.length} helper="Cuentas activas" icon="users" accent="green" />
      <StatCard label="Retos" value={challenges.length} helper="Catálogo disponible" icon="flag" accent="cyan" />
      <StatCard label="Grupo activo" value={selected?.code ?? "—"} helper={selected ? `${selected.members.length} estudiantes · ${selected.challenges.length} retos` : "Selecciona un grupo"} icon="lab" accent="blue" />
    </div>

    <div className="groups-layout">
      <aside className="glass-panel group-list-panel">
        <div className="panel-head"><div><span className="eyebrow">GRUPOS</span><h3>Mis grupos académicos</h3></div><span className="user-count">{groups.length}</span></div>
        <div className="group-list">
          {groups.map((g) => <button key={g.id} type="button" className={`group-list-item ${selected?.id === g.id ? "active" : ""}`} onClick={() => { setSelectedId(g.id); resetForm(); }}>
            <span className="group-list-icon"><Icon name="users" /></span>
            <span><strong>{g.code}</strong><small>{g.name}</small></span>
            <span className="group-list-count">{g.members.length}</span>
          </button>)}
          {!groups.length && <div className="empty-card compact"><strong>No hay grupos</strong><span>Crea el primero desde el panel de configuración.</span></div>}
        </div>
      </aside>

      <div className="group-workspace">
        <section className="glass-panel group-overview">
          <div className="group-overview-main">
            <span className="eyebrow accent">{selected?.code ?? "SIN SELECCIÓN"}</span>
            <h2>{selected?.name ?? "Crea o selecciona un grupo"}</h2>
            <p>{selected?.description || "Los grupos conectan estudiantes y retos, y generan el grupo correspondiente en Apache Guacamole."}</p>
          </div>
          {selected && <div className="group-status-stack">
            <span className="sync-pill"><span className="status-dot" /> Guacamole sincronizado</span>
            <small>{selected.guacamole_group_identifier || selected.code}</small>
          </div>}
        </section>

        <section className="glass-panel group-form-card">
          <div className="panel-head"><div><span className="eyebrow">{editingId ? "EDITAR GRUPO" : "NUEVO GRUPO"}</span><h3>{editingId ? "Datos del grupo" : "Crear grupo académico"}</h3></div></div>
          <div className="group-form-grid">
            <label>Nombre<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Grupo Red Team 01" disabled={!isAdmin} /></label>
            <label>Código<input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="GRP-RED-01" disabled={!isAdmin || Boolean(editingId)} /></label>
            <label className="span-2">Descripción<input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Curso, paralelo o laboratorio" disabled={!isAdmin} /></label>
          </div>
          {isAdmin ? <div className="group-form-actions"><button className="primary-action" disabled={busy || !name.trim() || !code.trim()} onClick={() => void saveGroup()}><Icon name="users" /> {editingId ? "Guardar cambios" : "Crear grupo"}</button>{editingId && <button className="secondary-action" onClick={resetForm}>Cancelar</button>}{selected && !editingId && <button className="table-action" onClick={editGroup}>Editar grupo</button>}{selected && !editingId && <button className="table-action danger" onClick={() => void removeGroup()}>Eliminar</button>}</div>
            : <div className="info-panel group-readonly"><strong>Modo instructor</strong><span>Consulta, asigna retos y monitoriza. La creación y modificación del grupo corresponde al administrador.</span></div>}
        </section>

        {selected && <div className="group-detail-grid">
          <section className="glass-panel group-section-card">
            <div className="section-title"><div><span className="eyebrow">MIEMBROS</span><h3>Estudiantes del grupo</h3></div><span className="section-counter">{selected.members.length}</span></div>
            {isAdmin && <div className="inline-add-row"><select value={memberId} onChange={(e) => setMemberId(e.target.value)}><option value="">Seleccionar estudiante</option>{availableMembers.map((u) => <option key={u.id} value={u.id}>{u.username}{u.email ? ` · ${u.email}` : ""}</option>)}</select><button className="secondary-action" disabled={busy || !memberId} onClick={() => void addMember()}>Agregar</button></div>}
            <div className="entity-list">
              {selected.members.map((m) => <div className="entity-row" key={m.user_id}><span className="entity-avatar"><Icon name="users" /></span><span className="entity-main"><strong>{m.username}</strong><small>{m.email || "Sin correo"}</small></span><span className="entity-state">Activo</span>{isAdmin && <button className="icon-action danger" title="Quitar del grupo" onClick={() => void removeMember(m.user_id)}>×</button>}</div>)}
              {selected.members.length === 0 && <div className="empty-card compact"><strong>Sin estudiantes</strong><span>Agrega estudiantes creados desde Gestionar usuarios.</span></div>}
            </div>
          </section>

          <section className="glass-panel group-section-card">
            <div className="section-title"><div><span className="eyebrow">RETOS ASIGNADOS</span><h3>Retos del grupo</h3></div><span className="section-counter">{selected.challenges.length}</span></div>
            <div className="inline-add-row"><select value={challengeCode} onChange={(e) => setChallengeCode(e.target.value)}><option value="">Seleccionar reto</option>{availableChallenges.map((c) => <option key={c.id} value={c.code}>{c.code} · {c.name}</option>)}</select><button className="secondary-action" disabled={busy || !challengeCode} onClick={() => void assign()}>Asignar</button></div>
            <div className="entity-list">
              {selected.challenges.map((c) => <div className="entity-row" key={c.challenge_id}><span className="entity-avatar flag"><Icon name="flag" /></span><span className="entity-main"><strong>{c.code}</strong><small>{c.name}</small></span><span className="entity-state">Asignado</span><button className="icon-action danger" title="Quitar reto" onClick={() => void unassign(c.code)}>×</button></div>)}
              {selected.challenges.length === 0 && <div className="empty-card compact"><strong>Sin retos asignados</strong><span>Selecciona un reto para habilitarlo al grupo.</span></div>}
            </div>
          </section>
        </div>}

        {selected && isAdmin && <section className="glass-panel group-section-card group-remote-card">
          <div className="section-title">
            <div><span className="eyebrow">ACCESO REMOTO</span><h3>Conexiones individuales por estudiante</h3><small>Clona una conexión base de Guacamole y asigna acceso READ únicamente al estudiante. La máquina puede reutilizarse mientras se mantenga el mismo entorno.</small></div>
          </div>
          <div className="remote-connection-form">
            <label>Máquina / VM<select value={selectedVmId} onChange={(e)=>setSelectedVmId(e.target.value)}><option value="">Seleccionar VM...</option>{availableVms.map((vm)=><option key={vm.id} value={vm.id}>{vm.name} · {vm.ip_address || "sin IP"} · {vm.laboratory_code}</option>)}</select></label>
            <label>Conexión base<select value={sourceConnectionId} onChange={(e)=>setSourceConnectionId(e.target.value)}><option value="">Seleccionar conexión...</option>{guacamoleConnections.map((c)=><option key={c.identifier} value={c.identifier}>{c.name} · {c.protocol.toUpperCase()} · {c.hostname || "—"}</option>)}</select></label>
            <button className="primary-action" disabled={busy || !selectedVmId || !sourceConnectionId || selected.members.length === 0} onClick={()=>void createRemoteConnections()}><Icon name="play" /> Crear conexiones del grupo</button>
          </div>
          <div className="remote-connection-list">
            {remoteConnections.map((rc)=><div className="entity-row" key={rc.id}><span className="entity-avatar"><Icon name="users" /></span><span className="entity-main"><strong>{rc.username}</strong><small>{rc.connection_name} · {rc.protocol.toUpperCase()} · {rc.hostname || "—"}</small></span><span className="entity-state">READ</span></div>)}
            {!remoteConnections.length && <div className="empty-card compact"><strong>No hay conexiones individuales creadas en esta vista</strong><span>Selecciona una VM y una conexión base para generar una por cada estudiante del grupo.</span></div>}
          </div>
        </section>}

        {selected && <section className="glass-panel group-section-card monitoring-card">
          <div className="section-title"><div><span className="eyebrow">SEGUIMIENTO</span><h3>Progreso del grupo</h3><small>Estado, intentos y puntos de los estudiantes en los retos asignados.</small></div></div>
          <div className="progress-list-table">
            {progress.map((row, i) => <div className="progress-list-row" key={`${row.user_id}-${row.challenge_code}-${i}`}><span><strong>{row.username}</strong><small>{row.challenge_code} · {row.challenge_name}</small></span><span className={row.status === "Completado" ? "status-published" : "status-draft"}>{row.status}</span><span>{row.attempts} intentos</span><strong>{row.points} pts</strong></div>)}
            {progress.length === 0 && <div className="empty-card compact"><strong>No hay actividad todavía</strong><span>El progreso aparecerá cuando los estudiantes comiencen sus retos.</span></div>}
          </div>
        </section>}
      </div>
    </div>
  </section>;
}
