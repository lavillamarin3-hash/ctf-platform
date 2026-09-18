// ============================================================
// VISTA: ManagementDashboard
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { createElement } from "react";
import { Icon, Ranking, StatCard } from "../../components/common";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementDashboard({ controller }: { controller: ManagementController }) {
  // Estado y datos que esta vista presenta.
  const {
    user, isAdmin, challenges, ranking,
    laboratories, published, points, activeUsers,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    setView,
  } = controller;
  return (
<>
    <section className="hero">
      <div>
        <span className="eyebrow accent">
          {isAdmin
            ? "ADMINISTRACIÓN"
            : "DISEÑO DE RETOS"}
        </span>

        <h1>
          Panel de{" "}
          <em>
            {isAdmin
              ? "administración"
              : "instructor"}
          </em>
        </h1>

        <p>
          {isAdmin
            ? "Gestiona usuarios, retos, ranking y el estado general de la plataforma."
            : "Diseña retos, revisa el progreso y supervisa los entornos del laboratorio."}
        </p>
      </div>

      <div className="level-badge">
        <span>
          LABS
        </span>

        <strong>
          {
            laboratories.length
          }
        </strong>
      </div>
    </section>

    <section className="stats-grid">
      <StatCard
        label="Retos"
        value={
          challenges.length
        }
        helper={`${published} publicados`}
        icon="flag"
        accent="purple"
      />

      <StatCard
        label="Usuarios activos"
        value={
          activeUsers ||
          ranking.length
        }
        helper={`${ranking.length} jugadores en ranking`}
        icon="users"
        accent="green"
      />

      <StatCard
        label="Puntos disponibles"
        value={points.toLocaleString(
          "es-ES"
        )}
        helper="Catálogo actual"
        icon="trophy"
        accent="cyan"
      />

      <StatCard
        label="Laboratorios"
        value={
          laboratories.length
        }
        helper="Entornos configurados"
        icon="lab"
        accent="blue"
      />
    </section>

    <div className="admin-grid">
      <section className="glass-panel admin-panel">
        <div className="panel-head">
          <div>
            <span className="eyebrow">
              ACCESOS
            </span>

            <h3>
              Gestión rápida
            </h3>
          </div>
        </div>

        <div className="admin-actions">
          <button
            className="admin-action"
            onClick={() =>
              setView(
                "challenges"
              )
            }
          >
            <Icon name="flag" />

            <span>
              <strong>
                Gestionar retos
              </strong>

              <small>
                Crear, editar, publicar y
                desactivar
              </small>
            </span>
          </button>

          {isAdmin && (
            <button
              className="admin-action"
              onClick={() =>
                setView(
                  "users"
                )
              }
            >
              <Icon name="users" />

              <span>
                <strong>
                  Gestionar usuarios
                </strong>

                <small>
                  Modificar rol y habilitación
                  de cuentas
                </small>
              </span>
            </button>
          )}

          <button
            className="admin-action"
            onClick={() =>
              setView(
                "laboratory"
              )
            }
          >
            <Icon name="lab" />

            <span>
              <strong>
                Laboratorios / VMs
              </strong>

              <small>
                {
                  laboratories.length
                }{" "}
                laboratorios ·{" "}
                {laboratories.reduce(
                  (
                    sum,
                    lab
                  ) =>
                    sum +
                    lab.vms
                      .length,
                  0
                )}{" "}
                VMs
              </small>
            </span>
          </button>

          <button
            className="admin-action"
            onClick={() =>
              setView(
                "ranking"
              )
            }
          >
            <Icon name="trophy" />

            <span>
              <strong>
                Ranking real
              </strong>

              <small>
                Resultados calculados desde
                los completados
              </small>
            </span>
          </button>
        </div>
      </section>

      <Ranking
        rows={ranking}
        user={user}
      />
    </div>
  </>
  );
}
