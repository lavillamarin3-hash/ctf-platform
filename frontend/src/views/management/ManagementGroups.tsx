// ============================================================
// VISTA: ManagementGroups
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { GroupManagement } from "../../components/groups";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementGroups({ controller }: { controller: ManagementController }) {
  // Estado y datos que esta vista presenta.
  const {
    isAdmin,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    setMessage,
  } = controller;
  return (
<GroupManagement isAdmin={isAdmin} onMessage={setMessage} />
  );
}
