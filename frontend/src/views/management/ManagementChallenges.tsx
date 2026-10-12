// ============================================================
// VISTA: ManagementChallenges
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { request } from "../../services/api/client";
import { createElement, useState } from "react";
import { difficultyStyle } from "../../config";
import { inferCategory } from "../../components/challenges";
import { legacyPublishedCodes } from "../../lib/pilotChallenges";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementChallenges({ controller }: { controller: ManagementController }) {
  const [dfirBusy, setDfirBusy] = useState(false);
  const [dfirMessage, setDfirMessage] = useState("");
  async function createDfir() {
    setDfirBusy(true);
    try {
      await request("/challenges/dfir-draft", { method: "POST" });
      await controller.load();
      setDfirMessage("DFIR-01 está en el catálogo. Revisa el borrador, publícalo y asígnalo a un grupo para probarlo como estudiante.");
    } catch (error) { setDfirMessage(error instanceof Error ? error.message : "No se pudo crear el borrador."); }
    finally { setDfirBusy(false); }
  }
  // Estado y datos que esta vista presenta.
  const {
    challenges, published, draft, points, isAdmin, catalogActionBusy,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    load, setEditing, setCreating, archive, archiveLegacyChallenges, createBeginnerChallengeDrafts,
  } = controller;
  const legacyCount = legacyPublishedCodes(challenges).length;
  return (
<section>
    <div className="page-heading">
      <div>
        <span className="eyebrow accent">
          GESTIÓN DE CONTENIDO
        </span>

        <h1>
          Retos
        </h1>

        <p>
          Administra el catálogo
          directamente desde la plataforma.
        </p>
      </div>

      <div className="page-actions">
        <button
          className="secondary-action"
          onClick={() =>
            void load()
          }
        >
          Actualizar
        </button>

        <button
          className="primary-action"
          onClick={() => {
            setEditing(
              null
            );

            setCreating(
              true
            );
          }}
        >
          + Nuevo reto
        </button>
      </div>
    </div>

    {isAdmin && <div className="glass-panel" style={{ marginBottom: "1rem", padding: "1rem" }}>
      <span className="eyebrow accent">CATÁLOGO OPERATIVO</span>
      <p>Conserva LAB-01 y el historial. Los otros retos publicados se pueden desactivar sin borrar resultados. Los ejercicios Linux y Kali → Linux se crean como borradores con flag dinámica; se publican solo después de probarlos en las VM reales.</p>
      <div className="row-actions">
        <button type="button" className="secondary-action" disabled={catalogActionBusy || legacyCount === 0} onClick={() => void archiveLegacyChallenges()}>Desactivar {legacyCount} retos anteriores</button>
        <button type="button" className="secondary-action" disabled={catalogActionBusy} onClick={() => void createBeginnerChallengeDrafts()}>Crear 3 borradores de práctica</button>
      </div>
    </div>}

    <div className="glass-panel" style={{ padding: "1rem", marginBottom: "1rem" }}>
      <h2>DFIR-01 · Correlación forense avanzada</h2>
      <p>500 puntos · Tres fuentes de registros · Relojes desfasados · Caso diferente por corrida</p>
      <button className="primary-action" disabled={dfirBusy} onClick={() => void createDfir()}>{dfirBusy ? "Preparando…" : "Crear o localizar borrador DFIR-01"}</button>
      {dfirMessage && <p role="status">{dfirMessage}</p>}
    </div>
    <div className="table-panel glass-panel">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Categoría</th>
            <th>Dificultad</th>
            <th>MITRE</th>
            <th>
              VM / Activo
            </th>
            <th>Puntos</th>
            <th>Estado</th>
            <th>
              Acciones
            </th>
          </tr>
        </thead>

        <tbody>
          {challenges.map(
            (c) => (
              <tr
                key={
                  c.id
                }
              >
                <td>
                  {c.code}
                </td>

                <td>
                  <strong>
                    {c.name}
                  </strong>
                </td>

                <td>
                  <span className="category-tag">
                    {inferCategory(
                      c
                    )}
                  </span>
                </td>

                <td>
                  <span
                    className={`difficulty ${
                      difficultyStyle[
                        c.difficulty
                      ]
                    }`}
                  >
                    {
                      c.difficulty
                    }
                  </span>
                </td>

                <td>
                  {
                    c.mitre_technique.split(
                      " — "
                    )[0]
                  }
                </td>

                <td>
                  {c.asset_references.join(
                    ", "
                  ) ||
                    "—"}
                </td>

                <td>
                  {c.points}
                </td>

                <td>
                  <span
                    className={
                      c.is_published
                        ? "status-published"
                        : "status-draft"
                    }
                  >
                    {c.is_published
                      ? "Publicado"
                      : "Inactivo"}
                  </span>
                </td>

                <td>
                  <div className="row-actions">
                    <button
                      className="table-action"
                      onClick={() => {
                        setEditing(
                          c
                        );

                        setCreating(
                          true
                        );
                      }}
                    >
                      Editar
                    </button>

                    <button
                      className="table-action danger"
                      onClick={() =>
                        void archive(
                          c.code
                        )
                      }
                      disabled={
                        !c.is_published
                      }
                    >
                      Desactivar
                    </button>
                  </div>
                </td>
              </tr>
            )
          )}
        </tbody>
      </table>

      {challenges.length ===
        0 && (
        <div className="empty-card">
          <strong>
            No hay retos cargados
          </strong>
        </div>
      )}
    </div>
  </section>
  );
}
