// ============================================================
// CLIENTE HTTP Y SESIÓN
// Responsabilidad: autenticación de peticiones y manejo uniforme de errores.
// ============================================================

const tokenKey = "ctf-access-token";
const ownerKey = "ctf-tab-session-owner";
const instanceId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + String(Math.random());
const startedAt = Date.now();

/** Sesiones separadas por ventana; la defensa definitiva de login usa Redis. */
export const session = {
  get: () => sessionStorage.getItem(tokenKey),
  save: (token: string) => {
    sessionStorage.setItem(tokenKey, token);
    sessionStorage.setItem(ownerKey, crypto.randomUUID());
  },
  clear: () => {
    sessionStorage.removeItem(tokenKey);
    sessionStorage.removeItem(ownerKey);
  },
};

if (typeof window !== "undefined" && "BroadcastChannel" in window) {
  const channel = new BroadcastChannel("ctf-session-tabs-v1");
  channel.onmessage = (event: MessageEvent) => {
    const message = event.data;
    const owner = sessionStorage.getItem(ownerKey);
    if (!owner || !session.get() || !message || message.owner !== owner) return;
    if (message.type === "probe" && message.instance !== instanceId) {
      // La pestaña antigua conserva la sesión al detectar una copia clonada.
      if (startedAt < message.startedAt ||
          (startedAt === message.startedAt && instanceId < message.instance)) {
        channel.postMessage({ type: "occupied", owner, target: message.instance });
      }
    } else if (message.type === "occupied" && message.target === instanceId) {
      session.clear();
      window.dispatchEvent(new Event("ctf-session-expired"));
    }
  };
  window.setTimeout(() => {
    const owner = sessionStorage.getItem(ownerKey);
    if (owner && session.get()) channel.postMessage({ type: "probe", owner, instance: instanceId, startedAt });
  }, 100);
}

/** Ejecuta una petición al backend CTF y convierte errores HTTP en Error. */
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  const token = session.get();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401 && token && path !== '/terminal/auth' && session.get() === token) {
      session.clear();
      window.dispatchEvent(new Event('ctf-session-expired'));
      throw new ApiError('Tu sesión venció. Inicia sesión de nuevo para continuar.', 401);
    }
    throw new ApiError(typeof body.detail === "string" ? body.detail : "Revisa los datos e intenta nuevamente", response.status);
  }

  return body as T;
}
