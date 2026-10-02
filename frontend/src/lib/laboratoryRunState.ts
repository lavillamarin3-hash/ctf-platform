import type { Run } from "../models";

/** Una expiración pendiente de cleanup debe conservar su acción de reintento. */
export function needsLaboratoryCleanup(run: Run): boolean {
  return run.status === "active" || (run.status === "expired" &&
    (run.connection_state === "active" || run.connection_state === "ready"));
}
