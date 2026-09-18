// ============================================================
// API DE GRUPOS
// ============================================================
import { request } from "./client";
import type { ProgressRow, StudentGroup } from "../../models";

export const groupsApi = {
  progressReport: (groupId?: number) =>
    request<ProgressRow[]>(`/reports/progress${groupId ? `?group_id=${groupId}` : ""}`),

  groups: () => request<StudentGroup[]>("/groups"),

  createGroup: (input: { name: string; code: string; description?: string; is_active?: boolean }) =>
    request<StudentGroup>("/groups", {
      method: "POST",
      body: JSON.stringify({ ...input, is_active: input.is_active ?? true }),
    }),

  updateGroup: (
    id: number,
    input: { name: string; code: string; description?: string; is_active?: boolean },
  ) =>
    request<StudentGroup>(`/groups/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteGroup: (id: number) => request<void>(`/groups/${id}`, { method: "DELETE" }),

  addGroupMember: (groupId: number, userId: number) =>
    request<StudentGroup>(`/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),

  removeGroupMember: (groupId: number, userId: number) =>
    request<void>(`/groups/${groupId}/members/${userId}`, { method: "DELETE" }),

  assignChallengeGroup: (code: string, groupId: number) =>
    request<StudentGroup>(`/challenges/${encodeURIComponent(code)}/groups/${groupId}`, { method: "PUT" }),

  unassignChallengeGroup: (code: string, groupId: number) =>
    request<StudentGroup>(`/challenges/${encodeURIComponent(code)}/groups/${groupId}`, { method: "DELETE" }),
};
