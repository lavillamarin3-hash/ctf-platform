// ============================================================
// ROUTER DE VISTAS DEL JUGADOR
// ============================================================

import { createElement } from "react";
import type { User } from "../../models";
import type { PlayerController } from "../../controllers/usePlayerController";
import { PlayerDashboard } from "./PlayerDashboard";
import { PlayerCategories } from "./PlayerCategories";
import { PlayerChallenges } from "./PlayerChallenges";
import { PlayerProgress } from "./PlayerProgress";
import { PlayerRanking } from "./PlayerRanking";
import { PlayerLaboratory } from "./PlayerLaboratory";

/** Decide qué vista mostrar sin mezclar la navegación con el contenido. */
export function PlayerRouter({ controller, user }: { controller: PlayerController; user: User }) {
  switch (controller.view) {
    case "dashboard":
      return <PlayerDashboard controller={controller} user={user} />;
    case "categories":
      return <PlayerCategories controller={controller} />;
    case "challenges":
      return <PlayerChallenges controller={controller} />;
    case "progress":
      return <PlayerProgress controller={controller} />;
    case "ranking":
      return <PlayerRanking controller={controller} user={user} />;
    case "laboratory":
      return <PlayerLaboratory controller={controller} />;
    default:
      return null;
  }
}
