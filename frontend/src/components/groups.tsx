// ============================================================
// GESTIÓN DE GRUPOS
// Responsabilidad: grupos académicos + sincronización real con Guacamole.
// ============================================================
import { createElement, useCallback, useEffect, useMemo, useState } from "react";
import { api, Challenge, StudentGroup, User } from "../api";
import { Icon, StatCard } from "./common";

export function GroupManagement({
  isAdmin,
  onMessage,
}: {
  isAdmin: boolean;
  onMessage: (message: string) => void;
}) {
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
  const [groupError, setGroupError] = useState("");
  const [progress, setProgress] = useState<import("../api").ProgressRow[]>([]);

  /**
   * Carga grupos, estudiantes y retos desde el backend.
   * La pantalla se mantiene sincronizada con el estado real.
   */
  const load = useCallback(async () => {
    try {
      const [groupData, userData, challengeData] = await Promise.all([
        api.groups(),
        api.visibleUsers(),
        api.challenges(),
      ]);
      setGroups(groupData);
      setUsers(userData.filter((item) => item.role === "player" && item.is_active));
      setChallenges(challengeData);
      setSelectedId((current) => current && groupData.some((item) => item.id === current) ? current : (groupData[0]?.id ?? null));
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo cargar la gestión de grupos.");
    }
  }, [onMessage]);

  useEffect(() => { void load(); }, [load]);

  const selected = groups.find((item) => item.id === selectedId) ?? null;
  useEffect(() => {
    if (!selectedId) {
      setProgress([]);
      return;
    }
    void api.progressReport(selectedId).then(setProgress).catch((err) => onMessage(err instanceof Error ? err.message : "No se pudo cargar el seguimiento."));
  }, [selectedId, onMessage]);

  const availableMembers = useMemo(() => selected ? users.filter((item) => !selected.members.some((member) => member.user_id === item.id)) : users, [selected, users]);
  const availableChallenges = useMemo(() => selected ? challenges.filter((item) => !selected.challenges.some((challenge) => challenge.challenge_id === item.id)) : challenges, [selected, challenges]);

  const resetForm = () => {
    setEditingId(null);
    setName("");
    setCode("");
    setDescription("");
  };

  const startEdit = () => {
    if (!selected || !isAdmin) return;
    setEditingId(selected.id);
    setName(selected.name);
    setCode(selected.code);
    setDescription(selected.description);
  };

  /** Crea o actualiza el grupo seleccionado. */
  const saveGroup = async () => {
    if (!isAdmin) return;
    const cleanCode = code.trim().toUpperCase();
    const cleanName = name.trim();
    setGroupError("");
    if (!/^[A-Z0-9_-]{2,64}$/.test(cleanCode)) {
      setGroupError("Código: utiliza de 2 a 64 caracteres, solo letras mayúsculas, números, guiones y _."); return;
    }
    if (cleanName.length < 2 || cleanName.length > 120) {
      setGroupError("Nombre: utiliza entre 2 y 120 caracteres."); return;
    }
    setBusy(true);
    try {
      const payload = { name: cleanName, code: cleanCode, description: description.trim(), is_active: true };
      const saved = editingId ? await api.updateGroup(editingId, payload) : await api.createGroup(payload);
      setGroups((current) => editingId ? current.map((item) => item.id === saved.id ? saved : item) : [saved, ...current]);
      setSelectedId(saved.id);
      resetForm();
      onMessage(editingId ? "Grupo actualizado en Cociber CTF y sincronizado con Guacamole." : "Grupo creado en Cociber CTF y en Guacamole.");
    } catch (err) {
      const status = (err as { status?: number } | null)?.status;
      const message = status === 405
        ? "La API no permite crear grupos (HTTP 405). Actualiza el backend de CoCiber CTF en el servidor y confirma POST /api/v1/groups."
        : status === 502
          ? "No se pudo sincronizar el grupo con Guacamole. Comprueba su API y la cuenta de servicio."
          : err instanceof Error ? err.message : "No se pudo guardar el grupo.";
      setGroupError(message);
      onMessage(message);
    } finally {
      setBusy(false);
    }
  };

  /** Elimina el grupo seleccionado después de confirmación. */
  const removeGroup = async () => {
    if (!selected || !isAdmin) return;
    if (!window.confirm(`¿Eliminar ${selected.code} de Cociber CTF y Guacamole?`)) return;
    setBusy(true);
    try {
      await api.deleteGroup(selected.id);
      const next = groups.filter((item) => item.id !== selected.id);
      setGroups(next);
      setSelectedId(next[0]?.id ?? null);
      resetForm();
      onMessage("Grupo eliminado de Cociber CTF y Guacamole.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo eliminar el grupo.");
    } finally {
      setBusy(false);
    }
  };

  /** Agrega un estudiante al grupo y dispara la sincronización remota. */
  const addMember = async () => {
    if (!selected || !memberId || !isAdmin) return;
    setBusy(true);
    try {
      const saved = await api.addGroupMember(selected.id, Number(memberId));
      setGroups((current) => current.map((item) => item.id === saved.id ? saved : item));
      setMemberId("");
      onMessage("Estudiante agregado al grupo de Cociber CTF y al User Group de Guacamole.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo agregar el estudiante.");
    } finally {
      setBusy(false);
    }
  };

  /** Retira un estudiante del grupo. */
  const removeMember = async (userId: number) => {
    if (!selected || !isAdmin) return;
    setBusy(true);
    try {
      await api.removeGroupMember(selected.id, userId);
      // El endpoint DELETE confirma con 204; recargamos para conservar
      // la respuesta completa del grupo y sus miembros.
      const updatedGroups = await api.groups();
      setGroups(updatedGroups);
      onMessage("Estudiante retirado del grupo y de Guacamole.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo retirar el estudiante.");
    } finally {
      setBusy(false);
    }
  };

  /** Asigna un reto al grupo. */
  const assignChallenge = async () => {
    if (!selected || !challengeCode || !isAdmin) return;
    setBusy(true);
    try {
      const saved = await api.assignChallengeGroup(challengeCode, selected.id);
      setGroups((current) => current.map((item) => item.id === saved.id ? saved : item));
      setChallengeCode("");
      onMessage("Reto asignado al grupo y permisos de acceso remoto sincronizados.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo asignar el reto.");
    } finally {
      setBusy(false);
    }
  };

  /** Retira un reto del grupo. */
  const unassignChallenge = async (challenge: string) => {
    if (!selected || !isAdmin) return;
    setBusy(true);
    try {
      const saved = await api.unassignChallengeGroup(challenge, selected.id);
      setGroups((current) => current.map((item) => item.id === saved.id ? saved : item));
      onMessage("Reto retirado del grupo.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo retirar el reto.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="groups-page">
      <div className="page-heading groups-heading">
        <div>
          <span className="eyebrow accent">ORGANIZACIÓN ACADÉMICA</span>
          <h1>Grupos de estudiantes</h1>
          <p>Un grupo controla miembros, retos y acceso remoto. Cada grupo académico se refleja como un User Group real en Apache Guacamole.</p>
        </div>
        <div className="page-actions">
          <button className="secondary-action" onClick={() => void load()} disabled={busy}>Actualizar</button>
          {selected && isAdmin && <button className="secondary-action" onClick={startEdit} disabled={busy}>Editar grupo</button>}
          {selected && isAdmin && <button className="danger-action" onClick={() => void removeGroup()} disabled={busy}>Eliminar</button>}
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Grupos" value={groups.length} helper="Cociber CTF + Guacamole" icon="users" accent="purple" />
        <StatCard label="Estudiantes" value={users.length} helper="Cuentas activas" icon="users" accent="green" />
        <StatCard label="Retos" value={challenges.length} helper="Catálogo disponible" icon="flag" accent="cyan" />
        <StatCard label="Grupo seleccionado" value={selected?.code ?? "—"} helper={selected ? `${selected.members.length} miembros · ${selected.challenges.length} retos` : "Selecciona un grupo"} icon="lab" accent="blue" />
      </div>

      <div className="groups-shell">
        <aside className="glass-panel groups-index">
          <div className="panel-head">
            <div><span className="eyebrow">GRUPOS</span><h3>Mis grupos</h3></div>
            <span className="user-count">{groups.length}</span>
          </div>
          <div className="group-list">
            {groups.map((group) => (
              <button key={group.id} type="button" className={`group-list-item ${selected?.id === group.id ? "active" : ""}`} onClick={() => { setSelectedId(group.id); resetForm(); }}>
                <span className="group-list-icon"><Icon name="users" /></span>
                <span className="group-list-copy"><strong>{group.code}</strong><small>{group.name}</small></span>
                <span className="group-list-count">{group.members.length}</span>
              </button>
            ))}
          </div>
          {isAdmin && (
            <div className="group-create-box">
              <span className="eyebrow">NUEVO GRUPO</span>
              <input value={editingId ? name : name} onChange={(e) => setName(e.target.value)} placeholder="Grupo Red Team 01" />
              <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="GRP-RED-01" disabled={Boolean(editingId)} />
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Curso, paralelo o laboratorio" rows={3} />
              {groupError && <p role="alert" className="ctf-inline-error">{groupError}</p>}
              <button className="primary-action full" onClick={() => void saveGroup()} disabled={busy || !name.trim() || !code.trim()}>{editingId ? "Guardar cambios" : "Crear grupo"}</button>
              {editingId && <button className="secondary-action full" onClick={resetForm} disabled={busy}>Cancelar edición</button>}
            </div>
          )}
        </aside>

        {selected ? (
          <div className="group-workspace">
            <section className="glass-panel group-hero-card">
              <div className="group-hero-content">
                <span className="eyebrow accent">{selected.code}</span>
                <h2>{selected.name}</h2>
                <p>{selected.description || "Grupo académico para organizar estudiantes y retos del laboratorio."}</p>
              </div>
              <div className="group-sync-card">
                <span className="sync-pill"><span className="status-dot" /> Sincronizado</span>
                <strong>Apache Guacamole</strong>
                <small>{selected.guacamole_group_identifier || selected.code}</small>
              </div>
            </section>

            <div className="group-panels-grid">
              <section className="glass-panel group-panel-card">
                <div className="panel-head"><div><span className="eyebrow">MIEMBROS</span><h3>Estudiantes del grupo</h3></div><span className="user-count">{selected.members.length}</span></div>
                {isAdmin && <div className="inline-add-row"><select value={memberId} onChange={(e) => setMemberId(e.target.value)}><option value="">Seleccionar estudiante...</option>{availableMembers.map((item) => <option key={item.id} value={item.id}>{item.username}{item.full_name ? ` · ${item.full_name}` : ""}</option>)}</select><button className="secondary-action" onClick={() => void addMember()} disabled={busy || !memberId}>Agregar</button></div>}
                <div className="member-list">
                  {selected.members.map((member) => (
                    <div className="member-card" key={member.user_id}>
                      <div className="member-avatar"><Icon name="users" /></div>
                      <div className="member-copy"><strong>{member.username}</strong><small>{member.email || "Sin correo"}</small></div>
                      <span className="status-published">Activo</span>
                      {isAdmin && <button className="icon-danger" title="Retirar del grupo" onClick={() => void removeMember(member.user_id)} disabled={busy}>×</button>}
                    </div>
                  ))}
                  {selected.members.length === 0 && <div className="empty-card compact"><strong>Sin estudiantes</strong><span>Agrega un estudiante para habilitar el acceso del grupo.</span></div>}
                </div>
              </section>

              <section className="glass-panel group-panel-card">
                <div className="panel-head"><div><span className="eyebrow">RETOS ASIGNADOS</span><h3>Acceso por grupo</h3></div><span className="user-count">{selected.challenges.length}</span></div>
                {isAdmin && <div className="inline-add-row"><select value={challengeCode} onChange={(e) => setChallengeCode(e.target.value)}><option value="">Seleccionar reto...</option>{availableChallenges.map((item) => <option key={item.id} value={item.code}>{item.code} · {item.name}</option>)}</select><button className="secondary-action" onClick={() => void assignChallenge()} disabled={busy || !challengeCode}>Asignar</button></div>}
                <div className="challenge-assigned-list">
                  {selected.challenges.map((challenge) => (
                    <div className="assigned-challenge-card" key={challenge.challenge_id}>
                      <div className="assigned-challenge-code">{challenge.code}</div>
                      <div className="assigned-challenge-copy"><strong>{challenge.name}</strong><small>Disponible para los miembros del grupo</small></div>
                      {isAdmin && <button className="icon-danger" title="Retirar reto" onClick={() => void unassignChallenge(challenge.code)} disabled={busy}>×</button>}
                    </div>
                  ))}
                  {selected.challenges.length === 0 && <div className="empty-card compact"><strong>Sin retos asignados</strong><span>Asigna LAB-01 para comenzar el ejercicio.</span></div>}
                </div>
              </section>
            </div>

            <section className="glass-panel group-panel-card group-progress-card">
              <div className="panel-head"><div><span className="eyebrow">SEGUIMIENTO</span><h3>Progreso de este grupo</h3></div><span className="eyebrow">RETOS + PUNTAJE</span></div>
              <div className="group-progress-grid">
                {progress.map((row) => (
                  <div className="group-progress-row" key={`${row.user_id}-${row.challenge_code}`}>
                    <div><strong>{row.username}</strong><small>{row.challenge_code} · {row.challenge_name}</small></div>
                    <span className={row.status === "Completado" ? "status-published" : "status-draft"}>{row.status}</span>
                    <b>{row.points} pts</b>
                    <small>{row.attempts} intento{row.attempts === 1 ? "" : "s"}</small>
                  </div>
                ))}
              </div>
              {progress.length === 0 && <div className="empty-card compact"><strong>Aún no hay actividad</strong><span>Cuando un estudiante inicie y resuelva LAB-01, el resultado aparecerá aquí.</span></div>}
            </section>
          </div>
        ) : (
          <section className="glass-panel group-empty-workspace"><Icon name="users" /><h2>Crea el primer grupo</h2><p>Los grupos son la unión entre estudiantes, retos y permisos de acceso remoto.</p></section>
        )}
      </div>
    </section>
  );
}
