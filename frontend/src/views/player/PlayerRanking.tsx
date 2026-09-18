// ============================================================
// VISTA DEL JUGADOR
// Responsabilidad: presentación de una sola pantalla.
// La lógica y efectos se mantienen en usePlayerController.
// ============================================================

import { createElement } from "react";
import { Ranking } from "../../components/common";
import type { PlayerController } from "../../controllers/usePlayerController";
import type { User } from "../../models";

export function PlayerRanking({ controller, user }: { controller: PlayerController; user: User }) {
  const { ranking } = controller;

  return (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    COMPETENCIA
                  </span>

                  <h1>
                    Ranking
                  </h1>

                  <p>
                    Clasificación actualizada
                    en tiempo real.
                  </p>
                </div>
              </div>

              <Ranking
                rows={ranking}
                user={user}
              />
            </section>
  );
}
