// ============================================================
// API DEL FRONTEND
// Responsabilidad: centralizar autenticación y comunicación HTTP.
// No colocar lógica visual aquí.
//
// REGLA DE ACCESO REMOTO:
// "setStudentConnection" sustituye los permisos directos de conexión
// del estudiante y deja únicamente READ sobre la conexión seleccionada.
// ============================================================

export type User = {
  id: number;
  username: string;
  email: string | null;
  role: "admin" | "instructor" | "player" | "guest";
  is_active: boolean;
  full_name?: string | null;
  organization?: string | null;
  user_function?: string | null;
};

export type Flag = {
  id: number;
  label: string;
  flag_order: number;
  is_active: boolean;
  mode?: "static" | "dynamic";
  template?: string | null;
};

export type Challenge = {
  id: number;
  code: string;
  name: string;
  description: string;
  instructions: string;
  difficulty: "Básico" | "Medio" | "Avanzado";
  category: string;
  scenario?: string | null;
  mitre_technique: string;
  asset_references: string[];
  points: number;
  is_published: boolean;
  flag_count: number;
  completed: boolean;
  flags?: Flag[];
};

export type RankingRow = {
  position: number;
  username: string;
  total_points: number;
  challenges_completed: number;
};

export type Run = {
  id: number;
  challenge_code: string;
  status: string;
  started_at: string;
  expires_at: string;
  launch_url?: string;
  connection_state?: string;
  workspace_strategy: string;
  target_vm_name?: string | null;
  target_vm_ip?: string | null;
  target_protocol?: string | null;
  laboratory_code?: string | null;
};

export type GuacamoleUser = {
  username: string;
  attributes: Record<string, string | null>;
  last_active?: number | null;
};

export type GuacamoleStatus = {
  mode: string;
  connected: boolean;
  base_url: string;
  data_source: string;
  username: string;
  user_count?: number | null;
};

export type GuacamoleConnection = {
  identifier: string;
  name: string;
  protocol: "ssh" | "rdp" | "vnc";
  parent_identifier?: string;
  hostname?: string | null;
  port?: string | null;
  parameters: Record<string, string | null>;
  attributes: Record<string, string | null>;
  active_connections: number;
};

export type GuacamolePermissionSet = {
  system_permissions: string[];
  connection_permissions: Record<string, string[]>;
};

export type BackendVM = {
  id: number;
  laboratory_id: number;
  name: string;
  os: string;
  ip_address: string | null;
  vlan: string;
  role: string;
  network_role: string;
  subnet: string;
  profile: string;
  baseline?: string | null;
  nutanix_vm_id?: string | null;
  guacamole_connection_id?: string | null;
  guacamole_url?: string | null;
  guacamole_protocol?: string | null;
  status: string;
};

export type GroupMember = {
  user_id: number;
  username: string;
  email: string | null;
  is_active: boolean;
};

export type GroupChallenge = {
  challenge_id: number;
  code: string;
  name: string;
};

export type StudentGroup = {
  id: number;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
  guacamole_group_identifier?: string | null;
  members: GroupMember[];
  challenges: GroupChallenge[];
};

export type ProgressRow = {
  user_id: number;
  username: string;
  challenge_code: string;
  challenge_name: string;
  status: "Completado" | "No iniciado";
  points: number;
  attempts: number;
  completed_at: string | null;
};

export type BackendLaboratory = {
  id: number;
  code: string | null;
  name: string;
  description: string;
  segment: string;
  status: string;
  vms: BackendVM[];
};

// ============================================================
// SESIÓN
// ============================================================

const tokenKey = "ctf-access-token";

export const session = {
  get: () => sessionStorage.getItem(tokenKey),
  save: (token: string) => sessionStorage.setItem(tokenKey, token),
  clear: () => sessionStorage.removeItem(tokenKey),
};

// ============================================================
// CLIENTE HTTP
// ============================================================

async function request<T>(
  path: string,
  init: RequestInit = {}
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
    throw new Error(
      body.detail || "No se pudo completar la operación"
    );
  }

  return body as T;
}

// ============================================================
// ENDPOINTS
// ============================================================

export const api = {
  // ---------------- AUTENTICACIÓN ----------------

  login: (username: string, password: string) =>
    request<{ access_token: string; user: User }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }
    ),

  me: () => request<User>("/auth/me"),

  updateProfile: (input: {
    username: string;
    email?: string | null;
  }) =>
    request<User>("/auth/profile", {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  changePassword: (input: {
    current_password: string;
    new_password: string;
  }) =>
    request<{ ok: boolean }>("/auth/password", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  // ---------------- USUARIOS CTF ----------------

  users: () => request<User[]>("/users"),

  visibleUsers: () =>
    request<User[]>("/users/visible"),

  updateUser: (
    id: number,
    changes: Partial<
      Pick<User, "role" | "is_active"> & {
        full_name: string | null;
        organization: string | null;
        user_function: string | null;
      }
    >
  ) =>
    request<User>(`/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),

  deleteUser: (id: number) =>
    request<void>(`/users/${id}`, {
      method: "DELETE",
    }),

  createUser: (input: {
    username: string;
    email?: string | null;
    password: string;
    role: User["role"];
    full_name?: string | null;
    organization?: string | null;
    user_function?: string | null;
    sync_guacamole?: boolean;
  }) =>
    request<User>("/users", {
      method: "POST",
      body: JSON.stringify({
        ...input,
        sync_guacamole: input.sync_guacamole ?? true,
      }),
    }),

  // ---------------- GUACAMOLE ----------------

  guacamoleStatus: () =>
    request<GuacamoleStatus>("/admin/guacamole/status"),

  guacamoleUsers: () =>
    request<GuacamoleUser[]>("/admin/guacamole/users"),

  createGuacamoleUser: (input: {
    username: string;
    password: string;
    email?: string | null;
    full_name?: string | null;
  }) =>
    request<GuacamoleUser>("/admin/guacamole/users", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateGuacamoleUser: (
    username: string,
    input: {
      password?: string;
      email?: string | null;
      full_name?: string | null;
      disabled?: boolean;
    }
  ) =>
    request<GuacamoleUser>(
      `/admin/guacamole/users/${encodeURIComponent(username)}`,
      {
        method: "PATCH",
        body: JSON.stringify(input),
      }
    ),

  deleteGuacamoleUser: (username: string) =>
    request<void>(
      `/admin/guacamole/users/${encodeURIComponent(username)}`,
      {
        method: "DELETE",
      }
    ),

  guacamoleConnections: () =>
    request<GuacamoleConnection[]>(
      "/admin/guacamole/connections"
    ),

  createGuacamoleConnection: (input: {
    name: string;
    protocol: "ssh" | "rdp" | "vnc";
    hostname: string;
    port: number;
    username?: string | null;
    password?: string | null;
    domain?: string | null;
    parent_identifier?: string;
  }) =>
    request<GuacamoleConnection>(
      "/admin/guacamole/connections",
      {
        method: "POST",
        body: JSON.stringify(input),
      }
    ),

  updateGuacamoleConnection: (
    identifier: string,
    input: {
      name: string;
      protocol: "ssh" | "rdp" | "vnc";
      hostname: string;
      port: number;
      username?: string | null;
      password?: string | null;
      domain?: string | null;
      parent_identifier?: string;
    }
  ) =>
    request<GuacamoleConnection>(
      `/admin/guacamole/connections/${encodeURIComponent(identifier)}`,
      {
        method: "PUT",
        body: JSON.stringify(input),
      }
    ),

  deleteGuacamoleConnection: (identifier: string) =>
    request<void>(
      `/admin/guacamole/connections/${encodeURIComponent(identifier)}`,
      {
        method: "DELETE",
      }
    ),

  guacamolePermissions: (username: string) =>
    request<GuacamolePermissionSet>(
      `/admin/guacamole/users/${encodeURIComponent(username)}/permissions`
    ),

  updateGuacamolePermissions: (
    username: string,
    input: GuacamolePermissionSet
  ) =>
    request<GuacamolePermissionSet>(
      `/admin/guacamole/users/${encodeURIComponent(username)}/permissions`,
      {
        method: "PATCH",
        body: JSON.stringify(input),
      }
    ),

  /**
   * Asigna exactamente una conexión a un estudiante.
   * La petición reemplaza el conjunto de permisos directos de conexión:
   * - system_permissions = []
   * - la conexión seleccionada recibe únicamente READ
   * - si connectionId es null, el estudiante queda sin conexión directa.
   */
  setStudentConnection: (
    username: string,
    connectionId: string | null
  ) =>
    request<GuacamolePermissionSet>(
      `/admin/guacamole/users/${encodeURIComponent(username)}/permissions`,
      {
        method: "PATCH",
        body: JSON.stringify({
          system_permissions: [],
          connection_permissions: connectionId
            ? { [connectionId]: ["READ"] }
            : {},
        }),
      }
    ),

  // ---------------- RETOS ----------------

  challenges: (
    params: { category?: string; difficulty?: string } = {}
  ) => {
    const q = new URLSearchParams();

    if (params.category && params.category !== "Todas") {
      q.set("category", params.category);
    }

    if (params.difficulty && params.difficulty !== "Todas") {
      q.set("difficulty", params.difficulty);
    }

    return request<Challenge[]>(
      `/challenges${q.toString() ? `?${q}` : ""}`
    );
  },

  categories: () =>
    request<{ name: string; challenge_count: number }[]>(
      "/categories"
    ),

  ranking: () =>
    request<{ rows: RankingRow[] }>("/ranking"),

  runs: () => request<Run[]>("/runs"),

  progress: () =>
    request<{
      total_points: number;
      challenges_completed: number;
    }>("/progress"),

  start: (code: string) =>
    request<Run>(
      `/challenges/${encodeURIComponent(code)}/start`,
      { method: "POST" }
    ),

  closeRun: (id: number) =>
    request<Run>(`/runs/${id}/close`, {
      method: "POST",
    }),

  createChallenge: (
    input: Omit<
      Challenge,
      "id" | "completed" | "flag_count" | "flags"
    >
  ) =>
    request<Challenge>("/challenges", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateChallenge: (
    code: string,
    input: Omit<
      Challenge,
      "id" | "completed" | "flag_count" | "flags"
    >
  ) =>
    request<Challenge>(
      `/challenges/${encodeURIComponent(code)}`,
      {
        method: "PUT",
        body: JSON.stringify(input),
      }
    ),

  archiveChallenge: (code: string) =>
    request<void>(
      `/challenges/${encodeURIComponent(code)}`,
      { method: "DELETE" }
    ),

  submit: (code: string, value: string) =>
    request<{
      correct: boolean;
      challenge_completed: boolean;
      awarded_points: number;
      message: string;
    }>(
      `/challenges/${encodeURIComponent(code)}/submissions`,
      {
        method: "POST",
        body: JSON.stringify({ value }),
      }
    ),

  createFlag: (
    code: string,
    input: {
      label: string;
      value?: string | null;
      flag_order: number;
      is_active: boolean;
      mode: "static" | "dynamic";
      template?: string | null;
    }
  ) =>
    request<Challenge>(
      `/challenges/${encodeURIComponent(code)}/flags`,
      {
        method: "POST",
        body: JSON.stringify(input),
      }
    ),

  updateFlag: (
    code: string,
    flagId: number,
    input: {
      label: string;
      value?: string | null;
      flag_order: number;
      is_active: boolean;
      mode: "static" | "dynamic";
      template?: string | null;
    }
  ) =>
    request<Challenge>(
      `/challenges/${encodeURIComponent(code)}/flags/${flagId}`,
      {
        method: "PUT",
        body: JSON.stringify(input),
      }
    ),

  deleteFlag: (code: string, flagId: number) =>
    request<void>(
      `/challenges/${encodeURIComponent(code)}/flags/${flagId}`,
      { method: "DELETE" }
    ),

  configureFlag: (
    code: string,
    flagId: number,
    input: {
      label: string;
      value: string;
      flag_order: number;
      is_active: boolean;
    }
  ) =>
    request<Challenge>(
      `/challenges/${encodeURIComponent(code)}/flags/${flagId}`,
      {
        method: "PUT",
        body: JSON.stringify({
          ...input,
          mode: "static",
        }),
      }
    ),

  // ---------------- GRUPOS ----------------

  progressReport: (groupId?: number) =>
    request<ProgressRow[]>(
      `/reports/progress${groupId ? `?group_id=${groupId}` : ""}`
    ),

  groups: () =>
    request<StudentGroup[]>("/groups"),

  createGroup: (input: {
    name: string;
    code: string;
    description?: string;
    is_active?: boolean;
  }) =>
    request<StudentGroup>("/groups", {
      method: "POST",
      body: JSON.stringify({
        ...input,
        is_active: input.is_active ?? true,
      }),
    }),

  updateGroup: (
    id: number,
    input: {
      name: string;
      code: string;
      description?: string;
      is_active?: boolean;
    }
  ) =>
    request<StudentGroup>(`/groups/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteGroup: (id: number) =>
    request<void>(`/groups/${id}`, {
      method: "DELETE",
    }),

  addGroupMember: (groupId: number, userId: number) =>
    request<StudentGroup>(`/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),

  removeGroupMember: (groupId: number, userId: number) =>
    request<void>(
      `/groups/${groupId}/members/${userId}`,
      { method: "DELETE" }
    ),

  assignChallengeGroup: (code: string, groupId: number) =>
    request<StudentGroup>(
      `/challenges/${encodeURIComponent(code)}/groups/${groupId}`,
      { method: "PUT" }
    ),

  unassignChallengeGroup: (code: string, groupId: number) =>
    request<StudentGroup>(
      `/challenges/${encodeURIComponent(code)}/groups/${groupId}`,
      { method: "DELETE" }
    ),

  // ---------------- LABORATORIOS / VMs ----------------

  prepareDemoLab: () =>
    request<{
      laboratory: {
        id: number;
        code: string;
        name: string;
      };
      vm: {
        id: number;
        name: string;
        ip: string;
        protocol: string;
        guacamole_connection_id: string;
        guacamole_connection_name: string;
      };
      challenge: {
        code: string;
        name: string;
        points: number;
        flag_mode: string;
      };
      attacker_ip: string;
      victim_ip: string;
      flag: string;
      note: string;
    }>("/admin/lab-ssh/prepare", {
      method: "POST",
    }),

  laboratories: () =>
    request<BackendLaboratory[]>("/laboratories"),

  playerLaboratories: () =>
    request<BackendLaboratory[]>("/player/laboratories"),

  createLaboratory: (
    input: Omit<BackendLaboratory, "id" | "vms">
  ) =>
    request<BackendLaboratory>("/laboratories", {
      method: "POST",
      body: JSON.stringify({
        ...input,
        status: input.status || "planned",
      }),
    }),

  updateLaboratory: (
    id: number,
    input: Omit<BackendLaboratory, "id" | "vms">
  ) =>
    request<BackendLaboratory>(`/laboratories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteLaboratory: (id: number) =>
    request<void>(`/laboratories/${id}`, {
      method: "DELETE",
    }),

  createVM: (input: Omit<BackendVM, "id">) =>
    request<BackendVM>("/vms", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateVM: (
    id: number,
    input: Omit<BackendVM, "id">
  ) =>
    request<BackendVM>(`/vms/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteVM: (id: number) =>
    request<void>(`/vms/${id}`, {
      method: "DELETE",
    }),

  // ---------------- REPORTES ----------------

  downloadRanking: async () => {
    const response = await fetch("/api/v1/reports/ranking.csv", {
      headers: {
        Authorization: `Bearer ${session.get()}`,
      },
    });

    if (!response.ok) {
      throw new Error("No se pudo exportar el ranking");
    }

    return response.blob();
  },
};
