// ============================================================
// VISTA: ManagementChallenges
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { createElement } from "react";
import { difficultyStyle } from "../../config";
import { inferCategory } from "../../components/challenges";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementChallenges({ controller }: { controller: ManagementController }) {
  // Estado y datos que esta vista presenta.
  const {
    challenges, published, draft, points,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    load, setEditing, setCreating, archive,
  } = controller;
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
