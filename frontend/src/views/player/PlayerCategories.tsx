// ============================================================
// VISTA DEL JUGADOR
// Responsabilidad: presentación de una sola pantalla.
// La lógica y efectos se mantienen en usePlayerController.
// ============================================================

import { createElement } from "react";
import { CategoryCard } from "../../components/common";
import type { PlayerController } from "../../controllers/usePlayerController";

export function PlayerCategories({ controller }: { controller: PlayerController }) {
  const { categories, setView, setCategoryFilter, setFilter } = controller;

  return (
<section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    CTF
                  </span>

                  <h1>
                    Categorías
                  </h1>

                  <p>
                    Explora las áreas de
                    entrenamiento disponibles.
                  </p>
                </div>
              </div>

              <div className="category-grid large">
                {Array.from(
                  categories.entries()
                ).map(
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

                        setCategoryFilter(
                          name
                        );

                        setFilter(
                          "Todas"
                        );
                      }}
                    />
                  )
                )}
              </div>
            </section>
  );
}
