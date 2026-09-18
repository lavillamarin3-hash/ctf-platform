// ============================================================
// CONTROLADOR DEL JUGADOR
// Responsabilidad: estado, carga de datos y acciones del jugador.
// No contiene JSX. Las vistas reciben este contrato.
// ============================================================

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, BackendLaboratory, Challenge, RankingRow, Run, session } from "../api";
import { PlayerView } from "../config";
import { inferCategory } from "../components/challenges";

export function usePlayerController() {
  const [view, setView] = useState<PlayerView>("dashboard");
  const [menuOpen, setMenuOpen] = useState(false);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [ranking, setRanking] = useState<RankingRow[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [laboratories, setLaboratories] = useState<BackendLaboratory[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [filter, setFilter] = useState("Todas");
  const [categoryFilter, setCategoryFilter] = useState("Todas");
  const [progress, setProgress] = useState({ total_points: 0, challenges_completed: 0 });
  const [message, setMessage] = useState<string | null>(null);

  /** Carga el estado completo necesario para el panel del jugador. */
  const load = useCallback(async () => {
    try {
      const [all, rank, activeRuns, currentProgress, playerLabs] = await Promise.all([
        api.challenges(),
        api.ranking(),
        api.runs(),
        api.progress(),
        api.playerLaboratories(),
      ]);

      setChallenges(all);
      setRanking(rank.rows);
      setRuns(activeRuns);
      setProgress(currentProgress);
      setLaboratories(playerLabs);

      setSelectedCode((current) => current || all[0]?.code || null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar la plataforma");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  /** Suscribe el jugador a actualizaciones del ranking en tiempo real. */
  useEffect(() => {
    const token = session.get();
    if (!token) return;

    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${protocol}://${location.host}/api/v1/ws/ranking?token=${encodeURIComponent(token)}`,
    );

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "ranking.updated") {
          setRanking(payload.rows);
        }
      } catch {
        // Los eventos inválidos no deben romper la sesión del jugador.
      }
    };

    return () => ws.close();
  }, []);

  const selected = challenges.find((item) => item.code === selectedCode) || null;

  const visibleChallenges = useMemo(
    () =>
      challenges.filter(
        (item) =>
          (filter === "Todas" || item.difficulty === filter) &&
          (categoryFilter === "Todas" || item.category === categoryFilter),
      ),
    [challenges, filter, categoryFilter],
  );

  /** Agrupa los retos para la pantalla de categorías. */
  const categories = useMemo(() => {
    const map = new Map<string, { total: number; completed: number }>();

    challenges.forEach((challenge) => {
      const key = inferCategory(challenge);
      const current = map.get(key) || { total: 0, completed: 0 };
      map.set(key, {
        total: current.total + 1,
        completed: current.completed + (challenge.completed ? 1 : 0),
      });
    });

    return map;
  }, [challenges]);

  /** Inicia un reto y abre la conexión Guacamole entregada por el backend. */
  const start = async (code: string) => {
    try {
      const run = await api.start(code);
      setRuns((old) => [run, ...old.filter((item) => item.challenge_code !== code)]);
      setMessage("El entorno está listo. Guacamole se abrirá en una nueva pestaña.");

      if (run.launch_url) {
        window.open(run.launch_url, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo iniciar el reto");
    }
  };

  /** Envía una flag al backend y actualiza el progreso mostrado. */
  const submit = async (code: string, value: string) => {
    const result = await api.submit(code, value);
    await load();
    return result;
  };

  return {
    view,
    setView,
    menuOpen,
    setMenuOpen,
    challenges,
    ranking,
    runs,
    laboratories,
    selectedCode,
    setSelectedCode,
    filter,
    setFilter,
    categoryFilter,
    setCategoryFilter,
    progress,
    message,
    setMessage,
    selected,
    visibleChallenges,
    categories,
    load,
    start,
    submit,
  };
}

/** Contrato público consumido por las vistas del jugador. */
export type PlayerController = ReturnType<typeof usePlayerController>;
