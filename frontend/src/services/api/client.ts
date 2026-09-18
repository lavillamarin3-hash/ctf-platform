// ============================================================
// CLIENTE HTTP Y SESIÓN
// Responsabilidad: autenticación de peticiones y manejo uniforme de errores.
// ============================================================

const tokenKey = "ctf-access-token";

/** Guarda, recupera o elimina el token de la sesión web. */
export const session = {
  get: () => sessionStorage.getItem(tokenKey),
  save: (token: string) => sessionStorage.setItem(tokenKey, token),
  clear: () => sessionStorage.removeItem(tokenKey),
};

/** Ejecuta una petición al backend CTF y convierte errores HTTP en Error. */
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
    throw new Error(body.detail || "No se pudo completar la operación");
  }

  return body as T;
}
