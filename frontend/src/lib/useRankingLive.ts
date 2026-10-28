import { useEffect, useRef } from "react";
import { api, type RankingRow } from "../api";

/** Observer del ranking para estudiantes y administración. */
export function useRankingLive(updateRows: (rows: RankingRow[]) => void): void {
  const updateRef = useRef(updateRows);
  updateRef.current = updateRows;

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let delay = 2000;
    let pageSuspended = false;
    let connecting = false;

    const refresh = async () => {
      try {
        const response = await api.ranking();
        if (!stopped) updateRef.current(response.rows);
      } catch { /* Se conserva el último ranking visible durante una caída. */ }
    };

    const scheduleRetry = () => {
      if (stopped || pageSuspended || retry !== null || !navigator.onLine || document.visibilityState !== "visible") return;
      retry = setTimeout(() => {
        retry = null;
        void connect();
      }, delay);
      delay = Math.min(delay * 2, 120000);
    };

    async function connect() {
      if (stopped || pageSuspended || connecting || !navigator.onLine || document.visibilityState !== "visible" || (socket && socket.readyState < WebSocket.CLOSING)) return;
      connecting = true;
      try {
        // El ticket viaja en cookie HttpOnly; nunca se agrega un JWT a la URL.
        const ticket = await api.rankingSession();
        if (stopped || pageSuspended) return;
        if (ticket.websocket_path !== "/api/v1/ws/ranking") {
          scheduleRetry();
          return;
        }
        const protocol = location.protocol === "https:" ? "wss" : "ws";
        const current = new WebSocket(`${protocol}://${location.host}${ticket.websocket_path}`);
        socket = current;
        current.onopen = () => { delay = 2000; };
        current.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === "ranking.updated" && Array.isArray(payload.rows)) {
              updateRef.current(payload.rows);
            }
          } catch { /* Un evento inválido no interrumpe la sesión. */ }
        };
        current.onerror = () => current.close();
        current.onclose = () => {
          if (socket === current) socket = null;
          if (!stopped) {
            void refresh();
            scheduleRetry();
          }
        };
      } catch {
        if (!stopped && !pageSuspended) {
          void refresh();
          scheduleRetry();
        }
      } finally {
        connecting = false;
      }
    }

    const clearRetry = () => { if (retry !== null) clearTimeout(retry); retry = null; };
    const pause = () => { clearRetry(); socket?.close(); socket = null; };
    const onPageHide = () => { pageSuspended = true; pause(); };
    const onPageShow = () => { if (pageSuspended) { pageSuspended = false; void refresh(); void connect(); } };
    const onOnline = () => { if (!pageSuspended) { void refresh(); void connect(); } };
    const onOffline = () => pause();
    const onVisibility = () => {
      if (document.visibilityState === "visible" && !pageSuspended) { void refresh(); void connect(); }
      else pause();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", onPageHide);
    window.addEventListener("pageshow", onPageShow);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    void connect();

    return () => {
      stopped = true;
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", onPageHide);
      window.removeEventListener("pageshow", onPageShow);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      pause();
    };
  }, []);
}
