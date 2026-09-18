// ============================================================
// API DE AUTENTICACIÓN Y PERFIL
// ============================================================
import { request } from "./client";
import type { User } from "../../models";

export const authApi = {
  login: (username: string, password: string) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<User>("/auth/me"),

  updateProfile: (input: { username: string; email?: string | null }) =>
    request<User>("/auth/profile", {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  changePassword: (input: { current_password: string; new_password: string }) =>
    request<{ ok: boolean }>("/auth/password", {
      method: "POST",
      body: JSON.stringify(input),
    }),
};
