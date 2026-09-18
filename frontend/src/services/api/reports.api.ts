// ============================================================
// API DE REPORTES
// ============================================================
import { session } from "./client";

export const reportsApi = {
  /** Descarga el ranking en formato CSV para el administrador. */
  downloadRanking: async () => {
    const response = await fetch("/api/v1/reports/ranking.csv", {
      headers: { Authorization: `Bearer ${session.get()}` },
    });

    if (!response.ok) {
      throw new Error("No se pudo exportar el ranking");
    }

    return response.blob();
  },
};
