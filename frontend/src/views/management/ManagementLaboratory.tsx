// ============================================================
// VISTA: ManagementLaboratory
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { createElement, useEffect, useState } from "react";
import { Icon, StatCard } from "../../components/common";
import { ConnectionAssignmentPanel } from "../../components/connectionAssignments";
import { api } from "../../api";
import type { ManagementController } from "../../controllers/useManagementController";
import { operationalLaboratories } from "../../lib/operationalLabs";

const OPERATIONAL_VM_TARGETS = new Map<string, string>([
  ["LAB-KALI", "192.168.146.134"],
  ["LAB-LNXVICT", "192.168.146.137"],
]);

export function ManagementLaboratory({ controller }: { controller: ManagementController }) {
  const [showAllInventory, setShowAllInventory] = useState(false);
  const [labDiagnostic, setLabDiagnostic] = useState<Awaited<ReturnType<typeof api.verifySSHLab>> | null>(null);
  const [diagnosticError, setDiagnosticError] = useState("");
  const [diagnosing, setDiagnosing] = useState(false);
  // Estado y datos que esta vista presenta.
  const {
    user, isAdmin, laboratories, laboratoryError, selectedLabId, users,
    guacamoleConnections, guacamoleUsers, guacamoleLoading, published,
    draft,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    load, setSelectedLabId, setGuacamoleConnectionEditing, setGuacamoleConnectionFormOpen, loadGuacamole,
    deleteGuacamoleManagedConnection, setLabEditing, setLabFormOpen, setVmEditing,
    setVmFormOpen, removeLaboratory, removeVM, loadStudentConnection,
    saveStudentConnection,
  } = controller;
  const displayedLabs = showAllInventory
    ? laboratories
    : operationalLaboratories(laboratories, OPERATIONAL_VM_TARGETS);
  const displayedSelectedLab = displayedLabs.find((lab) => lab.id === selectedLabId) ?? displayedLabs[0] ?? null;
  useEffect(() => {
    if (!showAllInventory) {
      const visibleIds = operationalLaboratories(laboratories, OPERATIONAL_VM_TARGETS).map((lab) => lab.id);
      if (!visibleIds.includes(selectedLabId ?? "")) setSelectedLabId(visibleIds[0] ?? null);
    }
  }, [showAllInventory, laboratories, selectedLabId, setSelectedLabId]);
  return (
<section>
    <div className="page-heading">
      <div>
        <span className="eyebrow accent">INFRAESTRUCTURA</span>
        <h1>Laboratorios / VMs</h1>
        <p>
          Administra los entornos del cyber range, sus máquinas virtuales, redes e IPs desde la plataforma CTF.
        </p>
      </div>

      <div className="page-actions">
        {isAdmin && <button type="button" className="secondary-action" disabled={diagnosing} onClick={() => {
          setDiagnosing(true);
          setDiagnosticError("");
          void api.verifySSHLab().then(setLabDiagnostic).catch((error: unknown) => {
            setLabDiagnostic(null);
            setDiagnosticError(error instanceof Error ? error.message : "No se pudo verificar LAB-01.");
          }).finally(() => setDiagnosing(false));
        }}>{diagnosing ? "Comprobando…" : "Diagnosticar LAB-01"}</button>}
        <button type="button" className="secondary-action" onClick={() => setShowAllInventory((value) => !value)}>
          {showAllInventory ? "Solo operativos" : "Ver inventario completo"}
        </button>
        <button
          className="secondary-action"
          onClick={() => void load()}
        >
          Actualizar inventario
        </button>

        {isAdmin && showAllInventory && (
          <button
            className="primary-action"
            disabled={Boolean(laboratoryError)}
            onClick={() => {
              setLabEditing(null);
              setLabFormOpen(true);
            }}
          >
            + Nuevo laboratorio
          </button>
        )}
      </div>
    </div>

    {laboratoryError && <div className="notice notice-error" role="alert">{laboratoryError}</div>}
    {diagnosticError && <div className="notice notice-error" role="alert">{diagnosticError}</div>}
    {labDiagnostic && <section className="glass-panel admin-panel" aria-label="Diagnóstico de LAB-01" role="status">
      <div className="panel-head"><div><span className="eyebrow accent">SOLO LECTURA</span><h3>Diagnóstico de reapertura de LAB-01</h3></div><span className={labDiagnostic.ready_for_dynamic_lab ? "status-published" : "status-draft"}>{labDiagnostic.ready_for_dynamic_lab ? "Prerrequisitos OK" : "Requiere revisión"}</span></div>
      <p>VM registrada: {labDiagnostic.database_state.vm_found && labDiagnostic.database_state.vm_has_matching_ip ? "Sí" : "No"} · Destino del reto: {labDiagnostic.database_state.target_selection_matches ? "LAB-LNXVICT confirmado" : "No coincide"} · Pool libre: {labDiagnostic.database_state.pool_available ? "Sí" : "No"} · Guacamole SSH: {labDiagnostic.guacamole.reachable && labDiagnostic.guacamole.ssh_connection_found ? "Sí" : "No"}</p>
      <p>SSH desde API: {labDiagnostic.runtime.ssh_reachable_from_api === null ? "Sin comprobar" : labDiagnostic.runtime.ssh_reachable_from_api ? "Conectable" : "No conectable"} · Reserva Redis: {labDiagnostic.runtime.redis_reservation_present === null ? "Sin comprobar" : labDiagnostic.runtime.redis_reservation_present ? `Activa (${labDiagnostic.runtime.redis_reservation_ttl_seconds ?? "?"} s restantes)` : "Libre"} · Flags dinámicas: {labDiagnostic.database_state.dynamic_flag_count}</p>
      <p>Autenticación SSH del inyector: {labDiagnostic.runtime.injector_authenticated === null ? "Sin comprobar" : labDiagnostic.runtime.injector_authenticated ? "Correcta" : "Fallida"}. Si falla, revisa la cuenta/clave configurada en la API sin copiarlas aquí.</p>
      {labDiagnostic.database_state.same_ip_records > 1 && <p role="alert">Inventario: {labDiagnostic.database_state.same_ip_records} fichas usan la IP de la víctima. Revisa sus nombres, SO y rol antes de editar; LAB-01 solo seleccionará «LAB-LNXVICT».</p>}
      <small>Esta comprobación no cambia Redis, PostgreSQL ni la VM; abre una sesión SSH y ejecuta «true». No prueba el script remoto ni sus permisos sudo: el inicio y cierre reales siguen siendo la verificación final.</small>
    </section>}
    {!laboratoryError && !showAllInventory && <p className="field-help">Se muestran solo LAB-KALI (192.168.146.134) y LAB-LNXVICT (192.168.146.137) si están marcadas como listas. Los demás registros siguen guardados; consulta «Ver inventario completo» para administrarlos.</p>}

    <div className="stats-grid">
      <StatCard
        label="Laboratorios"
        value={displayedLabs.length}
        helper={showAllInventory ? "Entornos registrados" : "Entornos con VM operativa"}
        icon="lab"
        accent="blue"
      />
      <StatCard
        label="Máquinas virtuales"
        value={displayedLabs.reduce((sum, lab) => sum + lab.vms.length, 0)}
        helper={showAllInventory ? "VMs registradas" : "VMs con IP confirmada"}
        icon="settings"
        accent="purple"
      />
      <StatCard
        label="Víctimas"
        value={displayedLabs.reduce((sum, lab) => sum + lab.vms.filter((vm) => vm.networkRole === "Víctimas").length, 0)}
        helper="Red actual · 192.168.146.0/24"
        icon="target"
        accent="green"
      />
      <StatCard
        label="Atacantes"
        value={displayedLabs.reduce((sum, lab) => sum + lab.vms.filter((vm) => vm.networkRole === "Atacantes").length, 0)}
        helper="Red actual · 192.168.146.0/24"
        icon="arrow"
        accent="cyan"
      />
    </div>

    <div className="admin-grid" style={{ marginTop: "13px" }}>
      <section className="glass-panel admin-panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">INVENTARIO</span>
            <h3>Laboratorios disponibles</h3>
          </div>
          <span className="user-count">{displayedLabs.length} entorno{displayedLabs.length === 1 ? "" : "s"}</span>
        </div>

        <div className="admin-actions">
          {displayedLabs.map((lab) => (
            <button
              key={lab.id}
              type="button"
              className={`admin-action ${selectedLabId === lab.id ? "active" : ""}`}
              onClick={() => setSelectedLabId(lab.id)}
            >
              <Icon name="lab" />
              <span>
                <strong>{lab.name}</strong>
                <small>
                  {lab.code} · {lab.vms.length} VM{lab.vms.length === 1 ? "" : "s"} · {lab.environment}
                </small>
              </span>
            </button>
          ))}
        </div>

        {displayedLabs.length === 0 && (
          <div className="empty-card">
            <strong>{showAllInventory ? "No hay laboratorios registrados" : "No hay VMs operativas registradas"}</strong>
            <span>{showAllInventory ? "Crea el primer entorno para comenzar a asociar máquinas virtuales." : "Verifica el inventario real y las IP confirmadas; no se han borrado registros."}</span>
          </div>
        )}
      </section>

      {displayedSelectedLab ? (
        <section className="glass-panel admin-panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow accent">{displayedSelectedLab.code}</span>
              <h3>{displayedSelectedLab.name}</h3>
              <small>{displayedSelectedLab.description}</small>
            </div>
            <div className="row-actions">
              <span className={displayedSelectedLab.status === "Disponible" ? "status-published" : displayedSelectedLab.status === "Mantenimiento" ? "status-draft" : "category-tag"}>
                {displayedSelectedLab.status}
              </span>
              {isAdmin && (
                <button
                  className="table-action"
                  onClick={() => {
                    setLabEditing(displayedSelectedLab);
                    setLabFormOpen(true);
                  }}
                >
                  Editar
                </button>
              )}
              {isAdmin && showAllInventory && (
                <button
                  className="table-action danger"
                  onClick={() => void removeLaboratory(displayedSelectedLab)}
                >
                  Eliminar
                </button>
              )}
            </div>
          </div>

          <div className="info-panel">
            <span className="eyebrow">ENTORNO</span>
            <p><strong>{displayedSelectedLab.environment}</strong></p>
            <small>Las IPs se controlan desde el backend para evitar duplicados en el inventario.</small>
          </div>

          <div className="panel-head" style={{ marginTop: "13px" }}>
            <div>
              <span className="eyebrow">MÁQUINAS VIRTUALES</span>
              <h3>Activos del laboratorio</h3>
            </div>
            {isAdmin && showAllInventory && (
              <button
                className="secondary-action"
                onClick={() => {
                  setVmEditing(null);
                  setVmFormOpen(true);
                }}
              >
                + Agregar VM
              </button>
            )}
          </div>

          <div className="table-panel" style={{ marginTop: "10px" }}>
            <table>
              <thead>
                <tr>
                  <th>VM</th>
                  <th>Sistema operativo</th>
                  <th>Red</th>
                  <th>IP</th>
                  <th>Perfil</th>
                  <th>Guacamole</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
            {displayedSelectedLab.vms.map((vm) => (
                  <tr key={vm.id}>
                    <td><strong>{vm.name}</strong></td>
                    <td>{vm.operatingSystem}</td>
                    <td>
                      <span className="category-tag">
                        {vm.networkRole || (vm.vlan === "VLAN 20" ? "Atacantes" : "Víctimas")} · {vm.vlan}
                      </span>
                    </td>
                    <td>{vm.ip || "Sin asignar"}</td>
                    <td>{vm.profile}</td>
                    <td>
                      {vm.guacamoleConnectionId ? (
                        <span className="category-tag">
                          {guacamoleConnections.find((item) => item.identifier === vm.guacamoleConnectionId)?.name || vm.guacamoleConnectionId}
                          {vm.guacamoleProtocol ? ` · ${vm.guacamoleProtocol.toUpperCase()}` : ""}
                        </span>
                      ) : (
                        <span className="self-label">Sin asociar</span>
                      )}
                    </td>
                    <td>
                      <div className="row-actions">
                        {isAdmin ? (
                          <>
                            <button
                              className="table-action"
                              onClick={() => {
                                setVmEditing(vm);
                                setVmFormOpen(true);
                              }}
                            >
                              Editar
                            </button>
                            {showAllInventory && <button
                              className="table-action danger"
                              onClick={() => void removeVM(displayedSelectedLab.id, vm)}
                            >
                              Eliminar
                            </button>}
                          </>
                        ) : (
                          <span className="self-label">Solo lectura</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {displayedSelectedLab.vms.length === 0 && (
              <div className="empty-card">
                <strong>Este laboratorio todavía no tiene VMs</strong>
                <span>Agrega una máquina y define su sistema operativo, red e IP.</span>
              </div>
            )}
          </div>
        </section>
      ) : (
        <section className="glass-panel admin-panel">
          <div className="empty-card">
            <strong>Selecciona un laboratorio</strong>
            <span>Elige un entorno del inventario para consultar sus máquinas virtuales.</span>
          </div>
        </section>
      )}
    </div>

    {displayedSelectedLab && isAdmin && (
      <>
        {/* ==================================================
            CONEXIONES GUACAMOLE
            Se administran en el mismo módulo que las VMs.
           ================================================== */}
        <section
          className="glass-panel laboratory-access-panel"
          style={{ marginTop: "13px" }}
        >
          <div className="panel-head">
            <div>
              <span className="eyebrow accent">
                ACCESO REMOTO
              </span>
              <h3>Conexiones de Apache Guacamole</h3>
              <small>
                Crea, edita y elimina las conexiones que
                después podrán asignarse a los estudiantes.
              </small>
            </div>

            <div className="page-actions compact-actions">
              <button
                className="secondary-action"
                onClick={() =>
                  void loadGuacamole()
                }
                disabled={guacamoleLoading}
              >
                {guacamoleLoading
                  ? "Actualizando…"
                  : "Actualizar conexiones"}
              </button>

              <button
                className="primary-action"
                onClick={() => {
                  setGuacamoleConnectionEditing(null);
                  setGuacamoleConnectionFormOpen(true);
                }}
              >
                + Nueva conexión
              </button>
            </div>
          </div>

          {guacamoleConnections.length === 0 ? (
            <div className="empty-card compact">
              <strong>
                No hay conexiones registradas
              </strong>
              <span>
                Crea una conexión SSH, RDP o VNC para
                asociarla a una VM.
              </span>
            </div>
          ) : (
            <div className="table-panel">
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Protocolo</th>
                    <th>Host</th>
                    <th>Puerto</th>
                    <th>Activas</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {guacamoleConnections.map(
                    (connection) => (
                      <tr
                        key={connection.identifier}
                      >
                        <td>
                          <strong>
                            {connection.name}
                          </strong>
                        </td>

                        <td>
                          <span className="category-tag">
                            {connection.protocol.toUpperCase()}
                          </span>
                        </td>

                        <td>
                          {connection.hostname || "—"}
                        </td>

                        <td>
                          {connection.port || "—"}
                        </td>

                        <td>
                          {connection.active_connections}
                        </td>

                        <td>
                          <div className="row-actions">
                            <button
                              className="table-action"
                              onClick={() => {
                                setGuacamoleConnectionEditing(
                                  connection
                                );
                                setGuacamoleConnectionFormOpen(
                                  true
                                );
                              }}
                            >
                              Editar
                            </button>

                            <button
                              className="table-action danger"
                              disabled={
                                connection.active_connections >
                                0
                              }
                              onClick={() =>
                                void deleteGuacamoleManagedConnection(
                                  connection
                                )
                              }
                            >
                              Eliminar
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* ==================================================
            ASIGNACIÓN ESTUDIANTE -> CONEXIÓN
           ================================================== */}
        <div style={{ marginTop: "13px" }}>
          <ConnectionAssignmentPanel
            students={users}
            guacamoleUsers={guacamoleUsers}
            connections={guacamoleConnections}
            loadAssignment={loadStudentConnection}
            onAssign={saveStudentConnection}
          />
        </div>
      </>
    )}

    <div className="info-panel glass-panel" style={{ marginTop: "13px" }}>
      <span className="eyebrow">MODELO DE RED</span>
      <p>
        <strong>Atacante:</strong> 192.168.146.134. &nbsp;
        <strong>Víctima:</strong> 192.168.146.137.
      </p>
    </div>
  </section>
  );
}
