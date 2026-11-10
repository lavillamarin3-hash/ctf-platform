export type User = { id: string; username: string; role: number; must_change_password: boolean };
export type Machine = { id: string; name: string; ip: string; kind: string; vlan: number; state: string; busy: boolean };
export type Scenario = { code: string; strategy: string; difficulty: string; points: number; victims: string[]; enabled: boolean };
export type Challenge = { id: string; code: string; name: string; difficulty: string; points: number; description: string; instructions: string; strategy: string; state: string; pilot_passed: boolean; availability: string; hints: {order:number;penalty:number}[]; resources: {title:string;url:string}[] };
export type Run = { id: string; challenge_id: string; state: string; outcome?: string; expires: string; pilot: boolean };
export type Group = { id: string; code: string; name: string; state?: string };
export type Maintenance = { id: string; machine_id: string; reason: string; state: string; tested: boolean };
export const token = { get: () => sessionStorage.getItem('ctf-fresh-token'), set: (value: string) => sessionStorage.setItem('ctf-fresh-token', value), clear: () => sessionStorage.removeItem('ctf-fresh-token') };

export async function api<T>(path: string, body?: unknown, method?: string): Promise<T> {
  let response: Response;
  const accessToken = token.get();
  try {
    response = await fetch(`/api/v1${path}`, { method: method ?? (body === undefined ? 'GET' : 'POST'), headers: { 'Content-Type': 'application/json', ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}) }, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
  } catch { throw new Error('No se pudo conectar. Comprueba tu conexión y pulsa Reintentar.'); }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login' && token.get() === accessToken) { token.clear(); window.dispatchEvent(new Event('fresh-logout')); }
    throw new Error(result.message || 'No se pudo completar la operación.');
  }
  return result as T;
}
