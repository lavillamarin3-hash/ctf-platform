// ============================================================
// VISTA: ManagementLaboratory
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { createElement } from "react";
import { Icon, StatCard } from "../../components/common";
import { ConnectionAssignmentPanel } from "../../components/connectionAssignments";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementLaboratory({ controller }: { controller: ManagementController }) {
  // Estado y datos que esta vista presenta.
  const {
    user, isAdmin, laboratories, selectedLab, selectedLabId, users,
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
        <button
          className="secondary-action"
          onClick={() => void load()}
        >
          Actualizar inventario
        </button>

        {isAdmin && (
          <button
            className="primary-action"
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

    <div className="stats-grid">
      <StatCard
        label="Laboratorios"
        value={laboratories.length}
        helper="Entornos registrados"
        icon="lab"
        accent="blue"
      />
      <StatCard
        label="Máquinas virtuales"
        value={laboratories.reduce((sum, lab) => sum + lab.vms.length, 0)}
        helper="VMs registradas"
        icon="settings"
        accent="purple"
      />
      <StatCard
        label="Víctimas"
        value={laboratories.reduce((sum, lab) => sum + lab.vms.filter((vm) => vm.networkRole === "Víctimas").length, 0)}
        helper="Red actual · 192.168.146.0/24"
        icon="target"
        accent="green"
      />
      <StatCard
        label="Atacantes"
        value={laboratories.reduce((sum, lab) => sum + lab.vms.filter((vm) => vm.networkRole === "Atacantes").length, 0)}
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
          <span className="user-count">{laboratories.length} entorno{laboratories.length === 1 ? "" : "s"}</span>
        </div>

        <div className="admin-actions">
          {laboratories.map((lab) => (
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

        {laboratories.length === 0 && (
          <div className="empty-card">
            <strong>No hay laboratorios registrados</strong>
            <span>Crea el primer entorno para comenzar a asociar máquinas virtuales.</span>
          </div>
        )}
      </section>

      {selectedLab ? (
        <section className="glass-panel admin-panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow accent">{selectedLab.code}</span>
              <h3>{selectedLab.name}</h3>
              <small>{selectedLab.description}</small>
            </div>
            <div className="row-actions">
              <span className={selectedLab.status === "Disponible" ? "status-published" : selectedLab.status === "Mantenimiento" ? "status-draft" : "category-tag"}>
                {selectedLab.status}
              </span>
              {isAdmin && (
                <button
                  className="table-action"
                  onClick={() => {
                    setLabEditing(selectedLab);
                    setLabFormOpen(true);
                  }}
                >
                  Editar
                </button>
              )}
              {isAdmin && (
                <button
                  className="table-action danger"
                  onClick={() => void removeLaboratory(selectedLab)}
                >
                  Eliminar
                </button>
              )}
            </div>
          </div>

          <div className="info-panel">
            <span className="eyebrow">ENTORNO</span>
            <p><strong>{selectedLab.environment}</strong></p>
            <small>Las IPs se controlan desde el backend para evitar duplicados en el inventario.</small>
          </div>

          <div className="panel-head" style={{ marginTop: "13px" }}>
            <div>
              <span className="eyebrow">MÁQUINAS VIRTUALES</span>
              <h3>Activos del laboratorio</h3>
            </div>
            {isAdmin && (
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
                {selectedLab.vms.map((vm) => (
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
                            <button
                              className="table-action danger"
                              onClick={() => void removeVM(selectedLab.id, vm)}
                            >
                              Eliminar
                            </button>
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

            {selectedLab.vms.length === 0 && (
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

    {selectedLab && isAdmin && (
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
