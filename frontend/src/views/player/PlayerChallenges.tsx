// ============================================================
// VISTA DEL JUGADOR
// Responsabilidad: presentación de una sola pantalla.
// La lógica y efectos se mantienen en usePlayerController.
// ============================================================

import { createElement } from "react";
import { categoryMeta } from "../../config";
import { ChallengeCard, ChallengeDetail } from "../../components/challenges";
import type { PlayerController } from "../../controllers/usePlayerController";

export function PlayerChallenges({ controller }: { controller: PlayerController }) {
  const { visibleChallenges, selected, runs, filter, setFilter, categoryFilter, setCategoryFilter, selectedCode, setSelectedCode, start, submit } = controller;

  return (
<section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    CATÁLOGO
                  </span>

                  <h1>
                    Retos disponibles
                  </h1>

                  <p>
                    Selecciona un reto para
                    acceder al laboratorio,
                    seguir las instrucciones y
                    enviar la flag.
                  </p>
                </div>

                <div className="filter-toolbar">
                  <label>
                    CAT.

                    <select
                      value={
                        categoryFilter
                      }
                      onChange={(
                        e
                      ) =>
                        setCategoryFilter(
                          e.target.value
                        )
                      }
                    >
                      <option>
                        Todas
                      </option>

                      {Object.keys(
                        categoryMeta
                      ).map(
                        (cat) => (
                          <option
                            key={cat}
                          >
                            {cat}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <div className="filter-row">
                    {[
                      "Todas",
                      "Básico",
                      "Medio",
                      "Avanzado",
                    ].map(
                      (level) => (
                        <button
                          key={
                            level
                          }
                          className={
                            filter ===
                            level
                              ? "filter active"
                              : "filter"
                          }
                          onClick={() =>
                            setFilter(
                              level
                            )
                          }
                        >
                          {level}
                        </button>
                      )
                    )}
                  </div>
                </div>
              </div>

              <div className="challenge-layout">
                <div className="challenge-list">
                  {visibleChallenges.map(
                    (
                      challenge
                    ) => (
                      <ChallengeCard
                        key={
                          challenge.id
                        }
                        challenge={
                          challenge
                        }
                        selected={
                          challenge.code ===
                          selectedCode
                        }
                        onClick={() =>
                          setSelectedCode(
                            challenge.code
                          )
                        }
                      />
                    )
                  )}

                  {visibleChallenges.length ===
                    0 && (
                    <p className="empty-text">
                      No hay retos con este
                      filtro.
                    </p>
                  )}
                </div>

                <ChallengeDetail
                  challenge={
                    selected
                  }
                  runs={runs}
                  onStart={start}
                  onSubmit={
                    submit
                  }
                />
              </div>
            </section>
  );
}
