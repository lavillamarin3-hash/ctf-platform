// ============================================================
// FACHADA DE API DEL FRONTEND
// Responsabilidad: mantener una interfaz única mientras los endpoints
// están organizados internamente por dominio en services/api/.
// Las vistas y controladores no necesitan conocer los archivos físicos.
// ============================================================

export * from "./models";
export { session } from "./services/api/client";

import { authApi } from "./services/api/auth.api";
import { usersApi } from "./services/api/users.api";
import { guacamoleApi } from "./services/api/guacamole.api";
import { challengesApi } from "./services/api/challenges.api";
import { groupsApi } from "./services/api/groups.api";
import { laboratoriesApi } from "./services/api/laboratories.api";
import { reportsApi } from "./services/api/reports.api";

/**
 * Fachada compatible con el código existente.
 * Los módulos nuevos se dividen por dominio, pero los consumidores
 * pueden seguir usando `api.algo()` durante la migración gradual.
 */
export const api = {
  ...authApi,
  ...usersApi,
  ...guacamoleApi,
  ...challengesApi,
  ...groupsApi,
  ...laboratoriesApi,
  ...reportsApi,
};
