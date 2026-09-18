// ============================================================
// VISTA: ManagementMonitoring
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { createElement } from "react";
import { api } from "../../api";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementMonitoring({ controller }: { controller: ManagementController }) {
  // Estado y datos que esta vista presenta.
  const {
    progressRows, published, draft, points,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    setMessage, setProgressRows,
  } = controller;
  return (
<section>
    <div className="page-heading">
      <div><span className="eyebrow accent">SEGUIMIENTO</span><h1>Seguimiento de estudiantes</h1><p>Consulta el avance de los estudiantes sobre los retos asignados a sus grupos.</p></div>
      <div className="page-actions"><button className="secondary-action" onClick={() => void api.progressReport().then(setProgressRows).catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar el seguimiento"))}>Actualizar</button></div>
    </div>
    <div className="table-panel glass-panel">
      <table><thead><tr><th>Estudiante</th><th>Reto</th><th>Estado</th><th>Intentos</th><th>Puntos</th><th>Completado</th></tr></thead>
        <tbody>{progressRows.map((row, i) => <tr key={`${row.user_id}-${row.challenge_code}-${i}`}><td><strong>{row.username}</strong></td><td>{row.challenge_code} · {row.challenge_name}</td><td><span className={row.status === "Completado" ? "status-published" : "status-draft"}>{row.status}</span></td><td>{row.attempts}</td><td>{row.points}</td><td>{row.completed_at ? new Date(row.completed_at).toLocaleString() : "—"}</td></tr>)}</tbody>
      </table>
      {progressRows.length === 0 && <div className="empty-card"><strong>No hay actividad registrada</strong><span>Los resultados aparecerán cuando existan estudiantes en grupos con retos asignados.</span></div>}
    </div>
  </section>
  );
}
