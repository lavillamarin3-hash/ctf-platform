// ============================================================
// COMPONENTES DE DATOS VISUALES
// Responsabilidad: tarjetas y resúmenes reutilizables.
// ============================================================

import { createElement } from "react";
import { categoryMeta } from "../../config";
import { Icon } from "./ui";

export function StatCard({
  label,
  value,
  helper,
  icon,
  accent,
}: {
  label: string;
  value: string | number;
  helper: string;
  icon: string;
  accent: string;
}) {
  return (
    <div
      className={`stat-card ${accent}`}
    >
      <div className="stat-icon">
        <Icon name={icon} />
      </div>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{helper}</small>
      </div>
    </div>
  );
}

export function CategoryCard({
  name,
  total,
  completed,
  onClick,
}: {
  name: string;
  total: number;
  completed: number;
  onClick: () => void;
}) {
  const meta =
    categoryMeta[name] ??
    categoryMeta.MISC;

  const progress = total
    ? Math.round(
        (completed / total) * 100
      )
    : 0;

  return (
    <button
      className={`category-card tone-${meta.tone}`}
      onClick={onClick}
    >
      <div className="category-head">
        <div className="category-icon">
          {meta.icon}
        </div>

        <span className="category-arrow">
          ↗
        </span>
      </div>

      <h3>{name}</h3>

      <p>{total} retos</p>

      <div className="category-progress">
        <div>
          <span>
            {completed}/{total}
          </span>

          <b>{progress}%</b>
        </div>

        <div className="bar">
          <span
            style={{
              width: `${progress}%`,
            }}
          />
        </div>
      </div>
    </button>
  );
}

