// ============================================================
// ASIGNACIÓN DE CONEXIONES POR ESTUDIANTE
// Responsabilidad: interfaz para asegurar que cada estudiante tenga
// una sola conexión Guacamole directa.
// No administra infraestructura; solo presenta y actualiza la
// asignación mediante callbacks del panel de administración.
// ============================================================

import { useEffect, useMemo, useState } from "react";
import {
  GuacamoleConnection,
  GuacamoleUser,
  User,
} from "../api";
import { Icon } from "./common";

export type ConnectionAssignmentPanelProps = {
  students: User[];
  guacamoleUsers: GuacamoleUser[];
  connections: GuacamoleConnection[];
  loadAssignment: (
    username: string
  ) => Promise<string | null>;
  onAssign: (
    username: string,
    connectionId: string | null
  ) => Promise<void>;
};

/**
 * Panel administrativo de asignación.
 *
 * Regla del módulo:
 *   1 estudiante -> 1 conexión directa -> READ
 *
 * Una conexión puede ser usada por varios estudiantes; la restricción
 * es que cada estudiante tenga como máximo una conexión asignada.
 */
export function ConnectionAssignmentPanel({
  students,
  guacamoleUsers,
  connections,
  loadAssignment,
  onAssign,
}: ConnectionAssignmentPanelProps) {
  const [assignments, setAssignments] = useState<
    Record<string, string>
  >({});
  const [loading, setLoading] = useState(false);
  const [busyUser, setBusyUser] = useState<string | null>(
    null
  );

  const activeStudents = useMemo(
    () =>
      students
        .filter(
          (item) =>
            item.role === "player" && item.is_active
        )
        .sort((a, b) =>
          a.username.localeCompare(b.username)
        ),
    [students]
  );

  const remoteUsernames = useMemo(
    () =>
      new Set(
        guacamoleUsers.map((item) =>
          item.username.toLowerCase()
        )
      ),
    [guacamoleUsers]
  );

  useEffect(() => {
    let cancelled = false;

    /**
     * Carga la asignación individual desde los permisos reales
     * de Guacamole, sin depender de datos ficticios del frontend.
     */
    const loadAssignments = async () => {
      setLoading(true);

      const entries = await Promise.all(
        activeStudents.map(async (student) => {
          if (
            !remoteUsernames.has(
              student.username.toLowerCase()
            )
          ) {
            return [student.username, ""] as const;
          }

          try {
            const identifier =
              await loadAssignment(student.username);
            return [
              student.username,
              identifier ?? "",
            ] as const;
          } catch {
            return [student.username, ""] as const;
          }
        })
      );

      if (!cancelled) {
        setAssignments(
          Object.fromEntries(entries)
        );
        setLoading(false);
      }
    };

    void loadAssignments();

    return () => {
      cancelled = true;
    };
  }, [
    activeStudents,
    loadAssignment,
    remoteUsernames,
    connections.length,
  ]);

  /**
   * Guarda una nueva asignación y actualiza el estado local.
   */
  const handleChange = async (
    username: string,
    connectionId: string
  ) => {
    setBusyUser(username);

    try {
      await onAssign(
        username,
        connectionId || null
      );

      setAssignments((current) => ({
        ...current,
        [username]: connectionId,
      }));
    } finally {
      setBusyUser(null);
    }
  };

  return (
    <section className="glass-panel connection-assignment-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow accent">
            CONTROL DE ACCESO
          </span>
          <h3>Conexión Guacamole por estudiante</h3>
          <small>
            Cada estudiante puede tener como máximo una
            conexión directa. El acceso se concede con
            permiso READ.
          </small>
        </div>

        <div className="assignment-rule-badge">
          <Icon name="lock" />
          <span>1 estudiante · 1 conexión</span>
        </div>
      </div>

      <div className="assignment-note">
        <Icon name="settings" />
        <span>
          Al guardar una conexión se sustituyen los demás
          permisos directos de conexión de ese estudiante.
        </span>
      </div>

      <div className="assignment-table">
        <div className="assignment-table-head">
          <span>Estudiante</span>
          <span>Grupo / estado</span>
          <span>Conexión asignada</span>
          <span>Permiso</span>
          <span>Estado</span>
        </div>

        {loading ? (
          <div className="assignment-empty">
            Cargando asignaciones…
          </div>
        ) : activeStudents.length === 0 ? (
          <div className="assignment-empty">
            <strong>No hay estudiantes activos</strong>
            <span>
              Crea un usuario con rol Jugador para
              asignarle una conexión.
            </span>
          </div>
        ) : (
          activeStudents.map((student) => {
            const hasRemote =
              remoteUsernames.has(
                student.username.toLowerCase()
              );

            const selected =
              assignments[student.username] ?? "";

            const selectedConnection =
              connections.find(
                (item) =>
                  item.identifier === selected
              );

            return (
              <div
                className="assignment-row"
                key={student.id}
              >
                <div className="assignment-student">
                  <div className="assignment-avatar">
                    {student.username
                      .slice(0, 2)
                      .toUpperCase()}
                  </div>
                  <div>
                    <strong>{student.username}</strong>
                    <small>
                      {student.full_name ||
                        student.email ||
                        "Cuenta de estudiante"}
                    </small>
                  </div>
                </div>

                <div>
                  <span className="category-tag">
                    Jugador
                  </span>
                </div>

                <div className="assignment-select-wrap">
                  <select
                    value={selected}
                    disabled={
                      !hasRemote ||
                      busyUser === student.username
                    }
                    onChange={(event) => {
                      void handleChange(
                        student.username,
                        event.target.value
                      );
                    }}
                  >
                    <option value="">
                      Sin conexión
                    </option>

                    {connections.map((connection) => (
                      <option
                        key={connection.identifier}
                        value={connection.identifier}
                      >
                        {connection.name} ·{" "}
                        {connection.protocol.toUpperCase()}
                        {connection.hostname
                          ? ` · ${connection.hostname}`
                          : ""}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  {selectedConnection ? (
                    <span className="permission-read-badge">
                      READ
                    </span>
                  ) : (
                    <span className="self-label">
                      —
                    </span>
                  )}
                </div>

                <div>
                  {!hasRemote ? (
                    <span className="status-draft">
                      Sin cuenta Guacamole
                    </span>
                  ) : busyUser === student.username ? (
                    <span className="status-draft">
                      Guardando…
                    </span>
                  ) : selectedConnection ? (
                    <span className="status-published">
                      Asignada
                    </span>
                  ) : (
                    <span className="status-draft">
                      Sin asignar
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
