// ============================================================
// API DE USUARIOS CTF
// ============================================================
import { request } from "./client";
import type { User } from "../../models";

export const usersApi = {
  users: () => request<User[]>("/users"),

  visibleUsers: () => request<User[]>("/users/visible"),

  updateUser: (
    id: number,
    changes: Partial<
      Pick<User, "role" | "is_active"> & {
        full_name: string | null;
        organization: string | null;
        user_function: string | null;
      }
    >,
  ) =>
    request<User>(`/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),

  deleteUser: (id: number) => request<void>(`/users/${id}`, { method: "DELETE" }),

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
      body: JSON.stringify({ ...input, sync_guacamole: input.sync_guacamole ?? true }),
    }),
};
