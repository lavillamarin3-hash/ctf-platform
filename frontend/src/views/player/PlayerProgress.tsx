// ============================================================
// VISTA DEL JUGADOR
// Responsabilidad: presentación de una sola pantalla.
// La lógica y efectos se mantienen en usePlayerController.
// ============================================================

import { createElement } from "react";
import type { PlayerController } from "../../controllers/usePlayerController";

export function PlayerProgress({ controller }: { controller: PlayerController }) {
  const { challenges, progress } = controller;

  return (
<section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    ESTADÍSTICAS
                  </span>

                  <h1>
                    Mi progreso
                  </h1>

                  <p>
                    Consulta tu avance y los retos
                    que has completado.
                  </p>
                </div>
              </div>

              <div className="progress-grid">
                <div className="progress-big glass-panel">
                  <span className="eyebrow">
                    TOTAL
                  </span>

                  <strong>
                    {progress.total_points.toLocaleString(
                      "es-ES"
                    )}{" "}
                    <small>
                      pts
                    </small>
                  </strong>

                  <p>
                    Puntaje acumulado
                  </p>
                </div>

                <div className="progress-list glass-panel">
                  <div className="panel-head">
                    <div>
                      <span className="eyebrow">
                        RETOS
                      </span>

                      <h3>
                        Historial
                      </h3>
                    </div>
                  </div>

                  {challenges.map(
                    (c) => (
                      <div
                        className="progress-row"
                        key={c.id}
                      >
                        <div
                          className="activity-dot"
                          style={{
                            opacity:
                              c.completed
                                ? 1
                                : 0.35,
                          }}
                        >
                          {c.completed
                            ? "✓"
                            : "·"}
                        </div>

                        <div>
                          <strong>
                            {c.name}
                          </strong>

                          <small>
                            {c.code} ·{" "}
                            {
                              c.difficulty
                            }
                          </small>
                        </div>

                        <b>
                          {c.completed
                            ? `+${c.points}`
                            : "Pendiente"}
                        </b>
                      </div>
                    )
                  )}
                </div>
              </div>
            </section>
  );
}
