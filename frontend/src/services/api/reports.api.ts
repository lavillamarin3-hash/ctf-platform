// ============================================================
// API DE REPORTES
// ============================================================
import { request, session } from "./client";

export const reportsApi = {
  /** Abre el ranking mediante ticket HttpOnly de un uso, sin token en la URL. */
  rankingSession: () => request<{ websocket_path: string; expires_at: string }>("/ws/ranking/session", { method: "POST" }),
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
