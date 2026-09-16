// ============================================================
// PANEL DEL JUGADOR
// Responsabilidad: coordinar estado y vistas del usuario player.
// La presentación se delega a componentes reutilizables.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api, Challenge, RankingRow, Run, session, User } from "../api";
import { Theme, ThemePreference, PlayerView, categoryMeta, difficultyStyle } from "../config";
import { PlayerSidebar, Header, StatCard, CategoryCard, Ranking, RecentActivity, Icon } from "../components/common";
import { ChallengeCard, ChallengeDetail, inferCategory } from "../components/challenges";

export function PlayerApp({
  user,
  onLogout,
  theme,
  onToggleTheme,
  themePreference,
  onThemePreferenceChange,
  onUserChange,
}: {
  user: User;
  onLogout: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  themePreference: ThemePreference;
  onThemePreferenceChange: (value: ThemePreference) => void;
  onUserChange: (user: User) => void;
}) {
  const [view, setView] =
    useState<PlayerView>(
      "dashboard"
    );

  const [menuOpen, setMenuOpen] =
    useState(false);

  const [challenges, setChallenges] =
    useState<Challenge[]>([]);

  const [ranking, setRanking] =
    useState<RankingRow[]>([]);

  const [runs, setRuns] =
    useState<Run[]>([]);

  const [laboratories, setLaboratories] =
    useState<import("../api").BackendLaboratory[]>([]);

  const [selectedCode, setSelectedCode] =
    useState<string | null>(
      null
    );

  const [filter, setFilter] =
    useState("Todas");

  const [categoryFilter, setCategoryFilter] =
    useState("Todas");

  const [progress, setProgress] =
    useState({
      total_points: 0,
      challenges_completed: 0,
    });

  const [message, setMessage] =
    useState<string | null>(
      null
    );

  const load = useCallback(
    async () => {
      try {
        const [
          all,
          rank,
          activeRuns,
          currentProgress,
          playerLabs,
        ] = await Promise.all([
          api.challenges(),
          api.ranking(),
          api.runs(),
          api.progress(),
          api.playerLaboratories(),
        ]);

        setChallenges(all);
        setRanking(rank.rows);
        setRuns(activeRuns);
        setProgress(
          currentProgress
        );
        setLaboratories(
          playerLabs
        );

        if (
          !selectedCode &&
          all[0]
        ) {
          setSelectedCode(
            all[0].code
          );
        }
      } catch (err) {
        setMessage(
          err instanceof Error
            ? err.message
            : "No se pudo cargar la plataforma"
        );
      }
    },
    [selectedCode]
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const token =
      session.get();

    if (!token) return;

    const protocol =
      location.protocol ===
      "https:"
        ? "wss"
        : "ws";

    const ws =
      new WebSocket(
        `${protocol}://${location.host}/api/v1/ws/ranking?token=${encodeURIComponent(
          token
        )}`
      );

    ws.onmessage = (
      event
    ) => {
      try {
        const payload =
          JSON.parse(
            event.data
          );

        if (
          payload.type ===
          "ranking.updated"
        ) {
          setRanking(
            payload.rows
          );
        }
      } catch {
        // ignorar eventos inválidos
      }
    };

    return () =>
      ws.close();
  }, []);

  const selected =
    challenges.find(
      (item) =>
        item.code ===
        selectedCode
    ) || null;

  const visibleChallenges =
    useMemo(
      () =>
        challenges.filter(
          (item) =>
            (filter ===
              "Todas" ||
              item.difficulty ===
                filter) &&
            (categoryFilter ===
              "Todas" ||
              item.category ===
                categoryFilter)
        ),
      [
        challenges,
        filter,
        categoryFilter,
      ]
    );

  const categories =
    useMemo(() => {
      const map =
        new Map<
          string,
          {
            total: number;
            completed: number;
          }
        >();

      challenges.forEach(
        (c) => {
          const key =
            inferCategory(c);

          const cur =
            map.get(key) || {
              total: 0,
              completed: 0,
            };

          map.set(
            key,
            {
              total:
                cur.total + 1,
              completed:
                cur.completed +
                (c.completed
                  ? 1
                  : 0),
            }
          );
        }
      );

      return map;
    }, [challenges]);

  const start = async (
    code: string
  ) => {
    try {
      const run =
        await api.start(
          code
        );

      setRuns((old) => [
        run,
        ...old.filter(
          (r) =>
            r.challenge_code !==
            code
        ),
      ]);

      setMessage(
        "El entorno está listo. Guacamole se abrirá en una nueva pestaña."
      );

      if (
        run.launch_url
      ) {
        window.open(
          run.launch_url,
          "_blank",
          "noopener,noreferrer"
        );
      }
    } catch (err) {
      setMessage(
        err instanceof Error
          ? err.message
          : "No se pudo iniciar el reto"
      );
    }
  };

  const submit = async (
    code: string,
    value: string
  ) => {
    const result =
      await api.submit(
        code,
        value
      );

    await load();

    return result;
  };

  return (
    <div className="app-shell">
      <PlayerSidebar
        view={view}
        setView={setView}
        open={menuOpen}
        onClose={() =>
          setMenuOpen(false)
        }
      />

      <div className="page-shell">
        <Header
          user={user}
          roleLabel="Jugador / Estudiante"
          onLogout={onLogout}
          onOpenMenu={() =>
            setMenuOpen(true)
          }
          theme={theme}
          onToggleTheme={
            onToggleTheme
          }
          themePreference={themePreference}
          onThemePreferenceChange={onThemePreferenceChange}
          onUserChange={onUserChange}
        />

        <main className="main-content">
          {message && (
            <div className="global-message">
              <span>
                {message}
              </span>

              <button
                onClick={() =>
                  setMessage(
                    null
                  )
                }
              >
                ×
              </button>
            </div>
          )}

          {view ===
            "dashboard" && (
            <>
              <section className="hero">
                <div>
                  <span className="eyebrow accent">
                    TU ESPACIO DE ENTRENAMIENTO
                  </span>

                  <h1>
                    Bienvenido,{" "}
                    <em>
                      {
                        user.username
                      }
                    </em>
                  </h1>

                  <p>
                    Continúa tu progreso y
                    selecciona un reto para
                    practicar en el laboratorio.
                  </p>
                </div>

                <div className="level-badge">
                  <span>
                    NIVEL
                  </span>

                  <strong>
                    {Math.min(
                      7,
                      1 +
                        Math.floor(
                          progress.challenges_completed /
                            3
                        )
                    )}
                  </strong>
                </div>
              </section>

              <section className="stats-grid">
                <StatCard
                  label="Puntos acumulados"
                  value={progress.total_points.toLocaleString(
                    "es-ES"
                  )}
                  helper="Rendimiento actual"
                  icon="trophy"
                  accent="purple"
                />

                <StatCard
                  label="Retos completados"
                  value={`${progress.challenges_completed}/${challenges.length}`}
                  helper="Retos resueltos"
                  icon="flag"
                  accent="blue"
                />

                <StatCard
                  label="Progreso"
                  value={`${
                    challenges.length
                      ? Math.round(
                          (progress.challenges_completed /
                            challenges.length) *
                            100
                        )
                      : 0
                  }%`}
                  helper="Avance general"
                  icon="chart"
                  accent="green"
                />

                <StatCard
                  label="Laboratorio"
                  value="READY"
                  helper="Entorno disponible"
                  icon="lab"
                  accent="cyan"
                />
              </section>

              <section className="progress-panel glass-panel">
                <div className="progress-head">
                  <div>
                    <span className="eyebrow">
                      PROGRESO
                    </span>

                    <h3>
                      Tu avance general
                    </h3>
                  </div>

                  <strong>
                    {
                      progress.challenges_completed
                    }
                    /
                    {
                      challenges.length
                    }{" "}
                    retos
                  </strong>
                </div>

                <div className="large-progress">
                  <span
                    style={{
                      width: `${
                        challenges.length
                          ? Math.round(
                              (progress.challenges_completed /
                                challenges.length) *
                                100
                            )
                          : 0
                      }%`,
                    }}
                  />
                </div>

                <div className="progress-foot">
                  <span>
                    {Math.max(
                      challenges.length -
                        progress.challenges_completed,
                      0
                    )}{" "}
                    retos pendientes
                  </span>

                  <button
                    onClick={() =>
                      setView(
                        "progress"
                      )
                    }
                  >
                    Ver mi progreso →
                  </button>
                </div>
              </section>

              <div className="dashboard-grid">
                <div>
                  <div className="section-title">
                    <div>
                      <span className="eyebrow">
                        EXPLORA
                      </span>

                      <h2>
                        Categorías
                      </h2>
                    </div>

                    <button
                      onClick={() =>
                        setView(
                          "categories"
                        )
                      }
                    >
                      Ver todas →
                    </button>
                  </div>

                  <div className="category-grid">
                    {Array.from(
                      categories.entries()
                    )
                      .slice(
                        0,
                        6
                      )
                      .map(
                        ([
                          name,
                          data,
                        ]) => (
                          <CategoryCard
                            key={name}
                            name={name}
                            total={
                              data.total
                            }
                            completed={
                              data.completed
                            }
                            onClick={() => {
                              setView(
                                "challenges"
                              );
                              setFilter(
                                "Todas"
                              );
                              setCategoryFilter(
                                name
                              );
                            }}
                          />
                        )
                      )}
                  </div>
                </div>

                <div className="side-stack">
                  <Ranking
                    rows={ranking}
                    user={user}
                  />

                  <RecentActivity
                    challenges={
                      challenges
                    }
                  />
                </div>
              </div>
            </>
          )}

          {view ===
            "categories" && (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    CTF
                  </span>

                  <h1>
                    Categorías
                  </h1>

                  <p>
                    Explora las áreas de
                    entrenamiento disponibles.
                  </p>
                </div>
              </div>

              <div className="category-grid large">
                {Array.from(
                  categories.entries()
                ).map(
                  ([
                    name,
                    data,
                  ]) => (
                    <CategoryCard
                      key={name}
                      name={name}
                      total={
                        data.total
                      }
                      completed={
                        data.completed
                      }
                      onClick={() => {
                        setView(
                          "challenges"
                        );

                        setCategoryFilter(
                          name
                        );

                        setFilter(
                          "Todas"
                        );
                      }}
                    />
                  )
                )}
              </div>
            </section>
          )}

          {view ===
            "challenges" && (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    CATÁLOGO
                  </span>

                  <h1>
                    Retos disponibles
                  </h1>

                  <p>
                    Selecciona un reto para
                    acceder al laboratorio,
                    seguir las instrucciones y
                    enviar la flag.
                  </p>
                </div>

                <div className="filter-toolbar">
                  <label>
                    CAT.

                    <select
                      value={
                        categoryFilter
                      }
                      onChange={(
                        e
                      ) =>
                        setCategoryFilter(
                          e.target.value
                        )
                      }
                    >
                      <option>
                        Todas
                      </option>

                      {Object.keys(
                        categoryMeta
                      ).map(
                        (cat) => (
                          <option
                            key={cat}
                          >
                            {cat}
                          </option>
                        )
                      )}
                    </select>
                  </label>

                  <div className="filter-row">
                    {[
                      "Todas",
                      "Básico",
                      "Medio",
                      "Avanzado",
                    ].map(
                      (level) => (
                        <button
                          key={
                            level
                          }
                          className={
                            filter ===
                            level
                              ? "filter active"
                              : "filter"
                          }
                          onClick={() =>
                            setFilter(
                              level
                            )
                          }
                        >
                          {level}
                        </button>
                      )
                    )}
                  </div>
                </div>
              </div>

              <div className="challenge-layout">
                <div className="challenge-list">
                  {visibleChallenges.map(
                    (
                      challenge
                    ) => (
                      <ChallengeCard
                        key={
                          challenge.id
                        }
                        challenge={
                          challenge
                        }
                        selected={
                          challenge.code ===
                          selectedCode
                        }
                        onClick={() =>
                          setSelectedCode(
                            challenge.code
                          )
                        }
                      />
                    )
                  )}

                  {visibleChallenges.length ===
                    0 && (
                    <p className="empty-text">
                      No hay retos con este
                      filtro.
                    </p>
                  )}
                </div>

                <ChallengeDetail
                  challenge={
                    selected
                  }
                  runs={runs}
                  onStart={start}
                  onSubmit={
                    submit
                  }
                />
              </div>
            </section>
          )}

          {view === "progress" && (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    ESTADÍSTICAS
                  </span>

                  <h1>
                    Mi progreso
                  </h1>

                  <p>
                    Consulta tu avance y los retos
                    que has completado.
                  </p>
                </div>
              </div>

              <div className="progress-grid">
                <div className="progress-big glass-panel">
                  <span className="eyebrow">
                    TOTAL
                  </span>

                  <strong>
                    {progress.total_points.toLocaleString(
                      "es-ES"
                    )}{" "}
                    <small>
                      pts
                    </small>
                  </strong>

                  <p>
                    Puntaje acumulado
                  </p>
                </div>

                <div className="progress-list glass-panel">
                  <div className="panel-head">
                    <div>
                      <span className="eyebrow">
                        RETOS
                      </span>

                      <h3>
                        Historial
                      </h3>
                    </div>
                  </div>

                  {challenges.map(
                    (c) => (
                      <div
                        className="progress-row"
                        key={c.id}
                      >
                        <div
                          className="activity-dot"
                          style={{
                            opacity:
                              c.completed
                                ? 1
                                : 0.35,
                          }}
                        >
                          {c.completed
                            ? "✓"
                            : "·"}
                        </div>

                        <div>
                          <strong>
                            {c.name}
                          </strong>

                          <small>
                            {c.code} ·{" "}
                            {
                              c.difficulty
                            }
                          </small>
                        </div>

                        <b>
                          {c.completed
                            ? `+${c.points}`
                            : "Pendiente"}
                        </b>
                      </div>
                    )
                  )}
                </div>
              </div>
            </section>
          )}

          {view === "ranking" && (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    COMPETENCIA
                  </span>

                  <h1>
                    Ranking
                  </h1>

                  <p>
                    Clasificación actualizada
                    en tiempo real.
                  </p>
                </div>
              </div>

              <Ranking
                rows={ranking}
                user={user}
              />
            </section>
          )}

          {view === "laboratory" && (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">LABORATORIO</span>
                  <h1>Entorno de práctica</h1>
                  <p>Accede a las máquinas habilitadas para el laboratorio mediante Apache Guacamole.</p>
                </div>
              </div>

              <div className="dashboard-grid">
                {laboratories.map((lab) => (
                  <div className="glass-panel" key={lab.id}>
                    <div className="section-title">
                      <div>
                        <span className="eyebrow">{lab.code || "LABORATORIO"}</span>
                        <h2>{lab.name}</h2>
                      </div>
                      <span className="status-published">{lab.status === "ready" ? "DISPONIBLE" : lab.status.toUpperCase()}</span>
                    </div>
                    <p>{lab.description}</p>
                    <small>{lab.segment}</small>
                    <div className="connections-grid" style={{ marginTop: 16 }}>
                      {lab.vms.map((vm) => (
                        <div className="connection-card" key={vm.id}>
                          <div className="connection-state"><span className="status-dot" />{vm.status === "ready" ? "Disponible" : vm.status}</div>
                          <h3>{vm.name}</h3>
                          <p>{vm.os}</p>
                          <small>{vm.ip_address || "IP no asignada"} · {vm.network_role} · {vm.guacamole_protocol ? vm.guacamole_protocol.toUpperCase() : "Guacamole"}</small>
                          {vm.guacamole_url ? (
                            <a href={vm.guacamole_url} target="_blank" rel="noreferrer" className="primary-action full" style={{ marginTop: 12 }}>
                              <Icon name="play" /> Abrir en Guacamole
                            </a>
                          ) : (
                            <button className="secondary-action full" disabled style={{ marginTop: 12 }}>Conexión no asociada</button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {laboratories.length === 0 && (
                  <div className="empty-card">
                    <Icon name="lab" />
                    <strong>No hay laboratorios publicados</strong>
                    <span>El administrador debe asociar al menos una VM a una conexión de Guacamole.</span>
                  </div>
                )}
              </div>

              {runs.length > 0 && (
                <div className="glass-panel" style={{ marginTop: 20 }}>
                  <div className="section-title"><div><span className="eyebrow">SESIONES</span><h2>Mis ejecuciones de retos</h2></div></div>
                  <div className="connections-grid">
                    {runs.map((run) => (
                      <div className="connection-card" key={run.id}>
                        <div className="connection-state"><span className="status-dot" />{run.status}</div>
                        <h3>{run.challenge_code}</h3>
                        <small>Hasta {new Date(run.expires_at).toLocaleString("es-ES")}</small>
                        {run.launch_url && <a href={run.launch_url} target="_blank" rel="noreferrer" className="primary-action full" style={{ marginTop: 12 }}><Icon name="play" /> Abrir sesión</a>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

        </main>
      </div>
    </div>
  );
}
