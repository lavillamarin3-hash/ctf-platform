// ============================================================
// API DE ADMINISTRACIÓN DE GUACAMOLE
// ============================================================
import { request } from "./client";
import type {
  GuacamoleConnection,
  GuacamolePermissionSet,
  GuacamoleStatus,
  GuacamoleUser,
} from "../../models";

export const guacamoleApi = {
  guacamoleStatus: () => request<GuacamoleStatus>("/admin/guacamole/status"),

  guacamoleUsers: () => request<GuacamoleUser[]>("/admin/guacamole/users"),

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
    input: { password?: string; email?: string | null; full_name?: string | null; disabled?: boolean },
  ) =>
    request<GuacamoleUser>(`/admin/guacamole/users/${encodeURIComponent(username)}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteGuacamoleUser: (username: string) =>
    request<void>(`/admin/guacamole/users/${encodeURIComponent(username)}`, { method: "DELETE" }),

  guacamoleConnections: () => request<GuacamoleConnection[]>("/admin/guacamole/connections"),

  createGuacamoleConnection: (input: {
    name: string;
    protocol: GuacamoleConnection["protocol"];
    hostname: string;
    port: number;
    username?: string | null;
    password?: string | null;
    domain?: string | null;
    parent_identifier?: string;
  }) =>
    request<GuacamoleConnection>("/admin/guacamole/connections", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateGuacamoleConnection: (
    identifier: string,
    input: {
      name: string;
      protocol: GuacamoleConnection["protocol"];
      hostname: string;
      port: number;
      username?: string | null;
      password?: string | null;
      domain?: string | null;
      parent_identifier?: string;
    },
  ) =>
    request<GuacamoleConnection>(`/admin/guacamole/connections/${encodeURIComponent(identifier)}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),

  deleteGuacamoleConnection: (identifier: string) =>
    request<void>(`/admin/guacamole/connections/${encodeURIComponent(identifier)}`, { method: "DELETE" }),

  guacamolePermissions: (username: string) =>
    request<GuacamolePermissionSet>(
      `/admin/guacamole/users/${encodeURIComponent(username)}/permissions`,
    ),

  updateGuacamolePermissions: (
    username: string,
    input: GuacamolePermissionSet,
  ) =>
    request<GuacamolePermissionSet>(
      `/admin/guacamole/users/${encodeURIComponent(username)}/permissions`,
      {
        method: "PATCH",
        body: JSON.stringify(input),
      },
    ),

  /** Asigna exactamente una conexión con permiso READ a un estudiante. */
  setStudentConnection: (
    username: string,
    connectionId: string | null,
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
      },
    ),
};
