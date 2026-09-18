// ============================================================
// VISTA DEL JUGADOR
// Responsabilidad: presentación de una sola pantalla.
// La lógica y efectos se mantienen en usePlayerController.
// ============================================================

import { createElement } from "react";
import type { User } from "../../models";
import { CategoryCard, Ranking, RecentActivity, StatCard } from "../../components/common";
import type { PlayerController } from "../../controllers/usePlayerController";

export function PlayerDashboard({ controller, user }: { controller: PlayerController; user: User }) {
  const { challenges, categories, progress, ranking, setView, setFilter, setCategoryFilter } = controller;

  return (
<>
              <section className="hero">
                <div>
                  <span className="eyebrow accent">
                    TU ESPACIO DE ENTRENAMIENTO
                  </span>

                  <h1>
                    Bienvenido,{" "}
                    <em>
                      {
                        user.username
                      }
                    </em>
                  </h1>

                  <p>
                    Continúa tu progreso y
                    selecciona un reto para
                    practicar en el laboratorio.
                  </p>
                </div>

                <div className="level-badge">
                  <span>
                    NIVEL
                  </span>

                  <strong>
                    {Math.min(
                      7,
                      1 +
                        Math.floor(
                          progress.challenges_completed /
                            3
                        )
                    )}
                  </strong>
                </div>
              </section>

              <section className="stats-grid">
                <StatCard
                  label="Puntos acumulados"
                  value={progress.total_points.toLocaleString(
                    "es-ES"
                  )}
                  helper="Rendimiento actual"
                  icon="trophy"
                  accent="purple"
                />

                <StatCard
                  label="Retos completados"
                  value={`${progress.challenges_completed}/${challenges.length}`}
                  helper="Retos resueltos"
                  icon="flag"
                  accent="blue"
                />

                <StatCard
                  label="Progreso"
                  value={`${
                    challenges.length
                      ? Math.round(
                          (progress.challenges_completed /
                            challenges.length) *
                            100
                        )
                      : 0
                  }%`}
                  helper="Avance general"
                  icon="chart"
                  accent="green"
                />

                <StatCard
                  label="Laboratorio"
                  value="READY"
                  helper="Entorno disponible"
                  icon="lab"
                  accent="cyan"
                />
              </section>

              <section className="progress-panel glass-panel">
                <div className="progress-head">
                  <div>
                    <span className="eyebrow">
                      PROGRESO
                    </span>

                    <h3>
                      Tu avance general
                    </h3>
                  </div>

                  <strong>
                    {
                      progress.challenges_completed
                    }
                    /
                    {
                      challenges.length
                    }{" "}
                    retos
                  </strong>
                </div>

                <div className="large-progress">
                  <span
                    style={{
                      width: `${
                        challenges.length
                          ? Math.round(
                              (progress.challenges_completed /
                                challenges.length) *
                                100
                            )
                          : 0
                      }%`,
                    }}
                  />
                </div>

                <div className="progress-foot">
                  <span>
                    {Math.max(
                      challenges.length -
                        progress.challenges_completed,
                      0
                    )}{" "}
                    retos pendientes
                  </span>

                  <button
                    onClick={() =>
                      setView(
                        "progress"
                      )
                    }
                  >
                    Ver mi progreso →
                  </button>
                </div>
              </section>

              <div className="dashboard-grid">
                <div>
                  <div className="section-title">
                    <div>
                      <span className="eyebrow">
                        EXPLORA
                      </span>

                      <h2>
                        Categorías
                      </h2>
                    </div>

                    <button
                      onClick={() =>
                        setView(
                          "categories"
                        )
                      }
                    >
                      Ver todas →
                    </button>
                  </div>

                  <div className="category-grid">
                    {Array.from(
                      categories.entries()
                    )
                      .slice(
                        0,
                        6
                      )
                      .map(
                        ([
                          name,
                          data,
                        ]) => (
                          <CategoryCard
                            key={name}
                            name={name}
                            total={
                              data.total
                            }
                            completed={
                              data.completed
                            }
                            onClick={() => {
                              setView(
                                "challenges"
                              );
                              setFilter(
                                "Todas"
                              );
                              setCategoryFilter(
                                name
                              );
                            }}
                          />
                        )
                      )}
                  </div>
                </div>

                <div className="side-stack">
                  <Ranking
                    rows={ranking}
                    user={user}
                  />

                  <RecentActivity
                    challenges={
                      challenges
                    }
                  />
                </div>
              </div>
            </>
  );
}
