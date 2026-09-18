// ============================================================
// ROUTER DE VISTAS DE GESTIÓN
// Decide qué vista presentar según el menú y el rol.
// ============================================================

import { createElement } from "react";
import type { ManagementController } from "../../controllers/useManagementController";
import { ManagementDashboard } from "./ManagementDashboard";
import { ManagementChallenges } from "./ManagementChallenges";
import { ManagementRanking } from "./ManagementRanking";
import { ManagementGroups } from "./ManagementGroups";
import { ManagementMonitoring } from "./ManagementMonitoring";
import { ManagementLaboratory } from "./ManagementLaboratory";
import { ManagementUsers } from "./ManagementUsers";
import { ManagementGuacamole } from "./ManagementGuacamole";

/** Enruta las vistas administrativas sin mezclar su JSX en ManagementApp. */
export function ManagementRouter({ controller }: { controller: ManagementController }) {
  const { view, isAdmin, panelRole } = controller;

  switch (view) {
    case "dashboard": return <ManagementDashboard controller={controller} />;
    case "challenges": return <ManagementChallenges controller={controller} />;
    case "ranking": return isAdmin || panelRole === "instructor" ? <ManagementRanking controller={controller} /> : null;
    case "groups": return isAdmin || panelRole === "instructor" ? <ManagementGroups controller={controller} /> : null;
    case "monitoring": return isAdmin || panelRole === "instructor" ? <ManagementMonitoring controller={controller} /> : null;
    case "laboratory": return <ManagementLaboratory controller={controller} />;
    case "users": return isAdmin || panelRole === "instructor" ? <ManagementUsers controller={controller} /> : null;
    case "guacamole": return isAdmin ? <ManagementGuacamole controller={controller} /> : null;
    default: return null;
  }
}
