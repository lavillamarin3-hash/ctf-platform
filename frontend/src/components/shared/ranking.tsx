// ============================================================
// RANKING Y ACTIVIDAD
// Responsabilidad: presentación del ranking y actividad reciente.
// ============================================================

import { createElement } from "react";
import { api, User, Challenge, RankingRow } from "../../api";
import { Icon } from "./ui";

export function buildRanking(
  rows: RankingRow[],
  user: User
): RankingRow[] {
  const byName = new Map<string, RankingRow>();

  rows.forEach((row) => {
    byName.set(row.username, row);
  });

  // Mantener al usuario autenticado visible aunque todavía no haya
  // completado un reto. No se agregan usuarios ficticios.
  if (!byName.has(user.username)) {
    byName.set(user.username, {
      position: 0,
      username: user.username,
      total_points: 0,
      challenges_completed: 0,
    });
  }

  return Array.from(byName.values())
    .sort(
      (a, b) =>
        b.total_points - a.total_points ||
        b.challenges_completed - a.challenges_completed ||
        a.username.localeCompare(b.username)
    )
    .slice(0, 10)
    .map((row, index) => ({
      ...row,
      position: index + 1,
    }));
}

export function Ranking({
  rows,
  user,
  compact = false,
}: {
  rows: RankingRow[];
  user: User;
  compact?: boolean;
}) {
  const displayRows =
    buildRanking(rows, user);

  return (
    <section
      className={`glass-panel ranking-panel ${
        compact
          ? "ranking-compact"
          : ""
      }`}
    >
      <div className="panel-head">
        <div>
          <span className="eyebrow">
            EN VIVO
          </span>

          <h3>
            {compact
              ? "Top 10"
              : "Ranking general"}
          </h3>
        </div>

        <span className="panel-link">
          10 jugadores
        </span>
      </div>

      <ol>
        {displayRows.map(
          (row) => (
            <li
              key={row.username}
              className={`${
                row.username ===
                user.username
                  ? "current"
                  : ""
              } rank-${row.position}`}
            >
              <span
                className={`rank-pos ${
                  row.position <= 3
                    ? "rank-medal"
                    : ""
                }`}
              >
                {row.position === 1
                  ? "🥇"
                  : row.position === 2
                  ? "🥈"
                  : row.position === 3
                  ? "🥉"
                  : row.position}
              </span>

              <div
                className={`rank-avatar ${
                  row.position <= 3
                    ? "rank-top-avatar"
                    : ""
                }`}
              >
                {row.username
                  .slice(0, 2)
                  .toUpperCase()}
              </div>

              <div className="rank-name">
                <strong>
                  {row.username}
                </strong>

                <small>
                  {
                    row.challenges_completed
                  }{" "}
                  retos completados
                </small>
              </div>

              <b>
                {row.total_points.toLocaleString(
                  "es-ES"
                )}{" "}
                pts
              </b>
            </li>
          )
        )}
      </ol>
    </section>
  );
}

export function RecentActivity({
  challenges,
}: {
  challenges: Challenge[];
}) {
  const items =
    challenges.slice(0, 3);

  return (
    <details className="glass-panel activity-panel activity-accordion" open>
      <summary className="panel-head activity-summary">
        <div>
          <span className="eyebrow">
            ACTIVIDAD
          </span>

          <h3>Reciente</h3>
        </div>

        <span className="activity-toggle">
          Mostrar / ocultar
        </span>
      </summary>

      <div className="activity-list">
        {items.length === 0 ? (
          <p className="empty-text">
            Todavía no hay actividad.
          </p>
        ) : (
          items.map(
            (item, idx) => (
              <div
                className="activity-item"
                key={item.code}
              >
                <div
                  className={`activity-dot ${
                    idx === 0
                      ? "success"
                      : "warn"
                  }`}
                >
                  {idx === 0
                    ? "✓"
                    : "!"}
                </div>

                <div>
                  <strong>
                    {item.completed
                      ? `Completaste ${item.code}`
                      : `Disponible: ${item.code}`}
                  </strong>

                  <small>
                    {item.name}
                  </small>
                </div>

                {item.completed && (
                  <b>
                    +{item.points} pts
                  </b>
                )}
              </div>
            )
          )
        )}
      </div>
    </details>
  );
}
