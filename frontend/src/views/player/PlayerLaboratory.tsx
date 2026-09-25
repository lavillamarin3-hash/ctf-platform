// ============================================================
// VISTA DEL JUGADOR - LABORATORIO
// Responsabilidad: mostrar las conexiones remotas activas.
// La lógica de datos permanece en usePlayerController.
// ============================================================

import { Icon } from "../../components/common";
import type { PlayerController } from "../../controllers/usePlayerController";

/**
 * Presenta las sesiones remotas activas del jugador.
 *
 * La vista no realiza llamadas HTTP ni modifica el estado del backend.
 * Solamente consume la información preparada por el controlador.
 */
export function PlayerLaboratory({ controller }: { controller: PlayerController }) {
  const { runs, setView, closeRun } = controller;

  return (
    <section className="player-laboratory">
      <div className="page-heading">
        <div>
          <span className="eyebrow accent">LABORATORIO</span>
          <h1>Mis conexiones</h1>
          <p>
            Aquí aparecen únicamente tus sesiones activas. Para acceder a un
            entorno inicia primero el reto correspondiente.
          </p>
        </div>
      </div>

      {runs.length === 0 ? (
        <div className="empty-card student-no-connections">
          <Icon name="lab" />
          <strong>No tienes conexiones activas</strong>
          <span>
            Inicia un reto asignado para preparar tu sesión de acceso remoto.
          </span>
          <button
            type="button"
            className="primary-action"
            onClick={() => setView("challenges")}
          >
            Explorar retos
          </button>
        </div>
      ) : (
        <section className="glass-panel student-connections-panel">
          <div className="section-title">
            <div>
              <span className="eyebrow">ACCESO REMOTO</span>
              <h2>Mis conexiones activas</h2>
            </div>
            <span className="user-count">{runs.length}</span>
          </div>

          <div className="connections-grid">
            {runs.map((run) => {
              const vmName = run.target_vm_name || run.challenge_code;
              const protocol = run.target_protocol
                ? ` · ${run.target_protocol.toUpperCase()}`
                : "";
              const targetIp =
                run.target_vm_ip || "IP administrada por el laboratorio";
              const expiration = new Date(run.expires_at).toLocaleString("es-ES");

              return (
                <article className="connection-card" key={run.id}>
                  <div className="connection-state">
                    <span className="status-dot" />
                    {run.status === "active" ? "ACTIVA" : run.status.toUpperCase()}
                  </div>

                  <h3>{vmName}</h3>
                  <p>
                    {run.challenge_code}
                    {protocol}
                  </p>
                  <small>
                    {targetIp} · Hasta {expiration}
                  </small>

                  <div className="connection-card-actions">
                    {run.launch_url ? (
                      <a
                        href={run.launch_url}
                        target="_blank"
                        rel="noreferrer"
                        className="primary-action full"
                      >
                        <Icon name="play" />
                        Abrir conexión
                      </a>
                    ) : (
                      <button type="button" className="secondary-action full" disabled>
                        Conexión no disponible
                      </button>
                    )}
                    {run.status === "active" && (
                      <button type="button" className="table-action danger full" onClick={() => void closeRun(run.id)}>
                        Cerrar sesión y limpiar VM
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </section>
  );
}
