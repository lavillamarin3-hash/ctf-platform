// ============================================================
// API DE LABORATORIOS Y VMs
// ============================================================
import { request } from "./client";
import type { BackendLaboratory, BackendVM } from "../../models";

export const laboratoriesApi = {
  prepareDemoLab: () =>
    request<{
      laboratory: { id: number; code: string; name: string };
      vm: {
        id: number;
        name: string;
        ip: string;
        protocol: string;
        guacamole_connection_id: string;
        guacamole_connection_name: string;
      };
      challenge: { code: string; name: string; points: number; flag_mode: string };
      attacker_ip: string;
      victim_ip: string;
      flag: string;
      note: string;
    }>("/admin/lab-ssh/prepare", { method: "POST" }),

  laboratories: () => request<BackendLaboratory[]>("/laboratories"),

  playerLaboratories: () => request<BackendLaboratory[]>("/player/laboratories"),

  createLaboratory: (input: Omit<BackendLaboratory, "id" | "vms">) =>
    request<BackendLaboratory>("/laboratories", {
      method: "POST",
      body: JSON.stringify({ ...input, status: input.status || "planned" }),
    }),

  updateLaboratory: (id: number, input: Omit<BackendLaboratory, "id" | "vms">) =>
    request<BackendLaboratory>(`/laboratories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteLaboratory: (id: number) => request<void>(`/laboratories/${id}`, { method: "DELETE" }),

  createVM: (input: Omit<BackendVM, "id">) =>
    request<BackendVM>("/vms", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  updateVM: (id: number, input: Omit<BackendVM, "id">) =>
    request<BackendVM>(`/vms/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteVM: (id: number) => request<void>(`/vms/${id}`, { method: "DELETE" }),
};
