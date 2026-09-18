// ============================================================
// API DE RETOS, RUNS Y BANDERAS
// ============================================================
import { request } from "./client";
import type { Challenge, RankingRow, Run } from "../../models";

export const challengesApi = {
  challenges: (params: { category?: string; difficulty?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.category && params.category !== "Todas") query.set("category", params.category);
    if (params.difficulty && params.difficulty !== "Todas") query.set("difficulty", params.difficulty);
    return request<Challenge[]>(`/challenges${query.toString() ? `?${query}` : ""}`);
  },

  categories: () => request<{ name: string; challenge_count: number }[]>("/categories"),

  ranking: () => request<{ rows: RankingRow[] }>("/ranking"),

  runs: () => request<Run[]>("/runs"),

  progress: () =>
    request<{ total_points: number; challenges_completed: number }>("/progress"),

  start: (code: string) =>
    request<Run>(`/challenges/${encodeURIComponent(code)}/start`, { method: "POST" }),

  closeRun: (id: number) => request<Run>(`/runs/${id}/close`, { method: "POST" }),

  createChallenge: (
    input: Omit<Challenge, "id" | "completed" | "flag_count" | "flags">,
  ) =>
    request<Challenge>("/challenges", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateChallenge: (
    code: string,
    input: Omit<Challenge, "id" | "completed" | "flag_count" | "flags">,
  ) =>
    request<Challenge>(`/challenges/${encodeURIComponent(code)}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),

  archiveChallenge: (code: string) =>
    request<void>(`/challenges/${encodeURIComponent(code)}`, { method: "DELETE" }),

  submit: (code: string, value: string) =>
    request<{
      correct: boolean;
      challenge_completed: boolean;
      awarded_points: number;
      message: string;
    }>(`/challenges/${encodeURIComponent(code)}/submissions`, {
      method: "POST",
      body: JSON.stringify({ value }),
    }),

  createFlag: (
    code: string,
    input: {
      label: string;
      value?: string | null;
      flag_order: number;
      is_active: boolean;
      mode: "static" | "dynamic";
      template?: string | null;
    },
  ) =>
    request<Challenge>(`/challenges/${encodeURIComponent(code)}/flags`, {
      method: "POST",
      body: JSON.stringify(input),
    }),

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
    },
  ) =>
    request<Challenge>(`/challenges/${encodeURIComponent(code)}/flags/${flagId}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),

  deleteFlag: (code: string, flagId: number) =>
    request<void>(`/challenges/${encodeURIComponent(code)}/flags/${flagId}`, { method: "DELETE" }),

  configureFlag: (
    code: string,
    flagId: number,
    input: { label: string; value: string; flag_order: number; is_active: boolean },
  ) =>
    request<Challenge>(`/challenges/${encodeURIComponent(code)}/flags/${flagId}`, {
      method: "PUT",
      body: JSON.stringify({ ...input, mode: "static" }),
    }),
};
