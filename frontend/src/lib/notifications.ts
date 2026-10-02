/** Avisos operativos locales: se guardan solo tipos predefinidos, nunca flags ni secretos. */

export const notificationCopy = {
  "lab.ready": { title: "Laboratorio listo", message: "Tu instancia está asignada. Abre la terminal integrada para comenzar.", tone: "success" },
  "lab.error": { title: "Laboratorio no disponible", message: "No se pudo iniciar el laboratorio. Revisa el aviso del reto e inténtalo de nuevo.", tone: "error" },
  "lab.closed": { title: "Laboratorio cerrado", message: "La sesión terminó y la limpieza fue confirmada.", tone: "success" },
  "lab.close_error": { title: "Cierre pendiente", message: "No se confirmó la limpieza del laboratorio. La ejecución sigue disponible para reintentar el cierre.", tone: "warning" },
  "flag.correct": { title: "Flag correcta", message: "El backend validó tu respuesta. Consulta el progreso del reto.", tone: "success" },
  "flag.incorrect": { title: "Flag incorrecta", message: "La respuesta no coincide. Sigue investigando el escenario.", tone: "warning" },
  "flag.error": { title: "Validación no disponible", message: "No se pudo comprobar la respuesta. Puedes volver a enviarla.", tone: "error" },
  "assignment.new": { title: "Nuevo reto asignado", message: "Hay un reto nuevo disponible en tu catálogo.", tone: "info" },
} as const;

export type NotificationKind = keyof typeof notificationCopy;
export type NotificationRecord = { id: string; kind: NotificationKind; createdAt: string; read: boolean };
const eventName = "ctf:notifications:changed";
const maximum = 20;
const keyFor = (userId: number) => `ctf:notifications:${userId}`;
const assignmentKeyFor = (userId: number) => `ctf:notification-assignments:${userId}`;

function storage(): Storage | null {
  try { return window.sessionStorage; } catch { return null; }
}

function changed(userId: number, kind?: NotificationKind) {
  window.dispatchEvent(new CustomEvent(eventName, { detail: { userId, kind } }));
}

export function readNotifications(userId: number): NotificationRecord[] {
  try {
    const value = JSON.parse(storage()?.getItem(keyFor(userId)) || "[]");
    if (!Array.isArray(value)) return [];
    return value.filter((item): item is NotificationRecord =>
      item && typeof item.id === "string" && typeof item.createdAt === "string" &&
      typeof item.read === "boolean" && typeof item.kind === "string" &&
      Object.prototype.hasOwnProperty.call(notificationCopy, item.kind),
    ).slice(0, maximum);
  } catch { return []; }
}

function save(userId: number, records: NotificationRecord[], kind?: NotificationKind) {
  try { storage()?.setItem(keyFor(userId), JSON.stringify(records.slice(0, maximum))); } catch { /* Memoria de la pestaña opcional. */ }
  changed(userId, kind);
}

export function publishNotification(userId: number, kind: NotificationKind) {
  if (!Object.prototype.hasOwnProperty.call(notificationCopy, kind)) return;
  const id = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  save(userId, [{ id, kind, createdAt: new Date().toISOString(), read: false }, ...readNotifications(userId)], kind);
}

export function markNotificationRead(userId: number, id: string) {
  save(userId, readNotifications(userId).map((record) => record.id === id ? { ...record, read: true } : record));
}

export function markAllNotificationsRead(userId: number) {
  save(userId, readNotifications(userId).map((record) => ({ ...record, read: true })));
}

export function subscribeNotifications(userId: number, listener: (kind?: NotificationKind) => void) {
  const onChanged = (event: Event) => {
    const detail = (event as CustomEvent<{ userId: number; kind?: NotificationKind }>).detail;
    if (detail?.userId === userId) listener(detail.kind);
  };
  window.addEventListener(eventName, onChanged);
  return () => window.removeEventListener(eventName, onChanged);
}

/** Detecta una nueva asignación solo cuando el catálogo vuelve a cargarse. */
export function observeAssignedChallenges(userId: number, challengeIds: number[]) {
  const current = [...new Set(challengeIds.filter((id) => Number.isSafeInteger(id) && id > 0))].sort((a, b) => a - b);
  const store = storage();
  if (!store) return;
  try {
    const previousRaw = store.getItem(assignmentKeyFor(userId));
    if (previousRaw !== null) {
      const previous = JSON.parse(previousRaw);
      if (Array.isArray(previous) && current.some((id) => !previous.includes(id))) {
        publishNotification(userId, "assignment.new");
      }
    }
    store.setItem(assignmentKeyFor(userId), JSON.stringify(current));
  } catch {
    try { store.setItem(assignmentKeyFor(userId), JSON.stringify(current)); } catch { /* Almacenamiento opcional. */ }
  }
}
