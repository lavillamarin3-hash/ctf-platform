// ============================================================
// VISTA DEL JUGADOR - LABORATORIO
// Responsabilidad: mostrar las conexiones remotas activas.
// La lógica de datos permanece en usePlayerController.
// ============================================================

import { Icon } from "../../components/common";
import { LaboratoryRunWorkspace } from "../../components/player/LaboratoryRunWorkspace";
import type { PlayerController } from "../../controllers/usePlayerController";
import { needsLaboratoryCleanup } from "../../lib/laboratoryRunState";

/**
 * Presenta las sesiones remotas activas del jugador.
 *
 * La vista no realiza llamadas HTTP ni modifica el estado del backend.
 * Solamente consume la información preparada por el controlador.
 */
export function PlayerLaboratory({ controller }: { controller: PlayerController }) {
  const { runs, setView, closeRun, submit } = controller;
  const activeRuns = runs.filter(needsLaboratoryCleanup);

  return (
    <section className="player-laboratory">
      <div className="page-heading">
        <div>
          <span className="eyebrow accent">LABORATORIO</span>
          <h1>Mi laboratorio</h1>
          <p>
            Aquí aparecen únicamente tus instancias asignadas, activas o pendientes de limpieza.
            Inicia un reto para preparar tu sesión de acceso remoto.
          </p>
        </div>
      </div>

      {activeRuns.length === 0 ? (
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
              <h2>Mis laboratorios y limpieza</h2>
            </div>
            <span className="user-count">{activeRuns.length}</span>
          </div>

          <div className="laboratory-workspace-list">
            {activeRuns.map((run) => (
              <LaboratoryRunWorkspace
                key={run.id}
                run={run}
                onClose={closeRun}
                onSubmit={submit}
              />
            ))}
          </div>
        </section>
      )}
    </section>
  );
}
