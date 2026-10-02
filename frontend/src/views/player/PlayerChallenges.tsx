// Catálogo del estudiante. La autorización de asignaciones pertenece al backend.
import { useRef } from "react";
import { ChallengeDetail, challengeInternalLevel } from "../../components/challenges";
import { difficultyStyle } from "../../config";
import type { PlayerController } from "../../controllers/usePlayerController";

export function PlayerChallenges({ controller }: { controller: PlayerController }) {
  const {
    challenges, visibleChallenges, selected, runs, filter, setFilter,
    categoryFilter, setCategoryFilter, search, setSearch, setSelectedCode,
    start, submit, closeRun,
  } = controller;
  const assignedCategories = [...new Set(challenges.map((challenge) => challenge.category || "MISC"))].sort();
  const hasFilters = Boolean(search || filter !== "Todas" || categoryFilter !== "Todas");
  const clearFilters = () => { setSearch(""); setFilter("Todas"); setCategoryFilter("Todas"); };
  const detailRef = useRef<HTMLDivElement>(null);
  const selectChallenge = (code: string) => {
    setSelectedCode(code);
    detailRef.current?.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  };

  return (
    <section className="player-challenges">
      <div className="page-heading">
        <div>
          <span className="eyebrow accent">TU ESPACIO CTF</span>
          <h1>Retos asignados</h1>
          <p>Selecciona un reto, investiga en su laboratorio y valida la flag en este mismo espacio.</p>
        </div>
      </div>

      <div className="challenge-catalog-toolbar" role="search" aria-label="Buscar retos asignados">
        <label className="challenge-search-label" htmlFor="challenge-search">
          Buscar reto
          <input id="challenge-search" type="search" className="challenge-search-input" value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Nombre, código, categoría o técnica MITRE" autoComplete="off" />
        </label>
        <label className="challenge-category-label" htmlFor="challenge-category">
          Categoría
          <select id="challenge-category" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
            <option value="Todas">Todas las categorías</option>
            {assignedCategories.map((category) => <option key={category}>{category}</option>)}
          </select>
        </label>
        <fieldset className="challenge-difficulty-filter">
          <legend>Dificultad</legend>
          <div className="filter-row">
            {["Todas", "Básico", "Medio", "Avanzado"].map((level) => (
              <button type="button" key={level} className={filter === level ? "filter active" : "filter"}
                aria-pressed={filter === level} onClick={() => setFilter(level)}>{level}</button>
            ))}
          </div>
        </fieldset>
      </div>
      <div className="challenge-catalog-status">
        <p role="status" aria-live="polite">{visibleChallenges.length} de {challenges.length} retos asignados</p>
        {hasFilters && <button type="button" className="resource-link" onClick={clearFilters}>Limpiar filtros</button>}
      </div>

      <div className="challenge-layout">
        <div className="challenge-list" aria-label="Lista de retos asignados">
          {visibleChallenges.length > 0 ? (
            <div className="challenge-table-scroll" role="region" aria-label="Tabla de retos asignados" tabIndex={0}>
              <table className="player-challenge-table">
                <caption className="sr-only">Retos asignados al estudiante</caption>
                <thead><tr><th scope="col">Código</th><th scope="col">Reto</th><th scope="col">Categoría</th><th scope="col">Nivel</th><th scope="col">MITRE</th><th scope="col">Puntos</th><th scope="col">Estado</th><th scope="col">Acción</th></tr></thead>
                <tbody>{visibleChallenges.map((challenge) => (
                  <tr key={challenge.id} className={challenge.code === selected?.code ? "selected" : ""}>
                    <th scope="row" className="challenge-table-code">{challenge.code}</th>
                    <td className="challenge-table-name"><button type="button" className="challenge-table-title" aria-current={challenge.code === selected?.code ? "true" : undefined} aria-controls="challenge-selected-detail" onClick={() => selectChallenge(challenge.code)}>{challenge.name}</button><small>{challenge.description}</small></td>
                    <td data-label="Categoría"><span className="challenge-category">{challenge.category || "MISC"}</span></td>
                    <td data-label="Nivel"><span className="challenge-table-level">Nivel {challengeInternalLevel(challenge.difficulty)}</span><span className={`difficulty ${difficultyStyle[challenge.difficulty]}`}>{challenge.difficulty}</span></td>
                    <td data-label="MITRE">{challenge.mitre_technique.split(" — ")[0] || "—"}</td>
                    <td data-label="Puntos"><strong className="accent-text">{challenge.points} pts</strong></td>
                    <td data-label="Estado"><span className={challenge.completed ? "challenge-table-complete" : "challenge-table-pending"}>{challenge.completed ? "Completado" : "Pendiente"}</span></td>
                    <td className="challenge-table-action"><button type="button" className="secondary-action" aria-label={`Ver reto ${challenge.name}`} aria-controls="challenge-selected-detail" onClick={() => selectChallenge(challenge.code)}>Ver reto</button></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : (
            <div className="challenge-catalog-empty">
              <strong>{hasFilters ? "No hay coincidencias" : "Aún no tienes retos asignados"}</strong>
              <p>{hasFilters ? "Prueba otro término o cambia los filtros." : "Tu instructor publicará los retos para tu grupo."}</p>
              {hasFilters && <button type="button" className="secondary-action" onClick={clearFilters}>Ver todos mis retos</button>}
            </div>
          )}
        </div>
        <div className="challenge-detail-container" id="challenge-selected-detail" ref={detailRef}>
          <ChallengeDetail key={selected?.code ?? "empty"} challenge={selected} runs={runs}
            onStart={start} onSubmit={submit} onClose={closeRun} />
        </div>
      </div>
    </section>
  );
}
