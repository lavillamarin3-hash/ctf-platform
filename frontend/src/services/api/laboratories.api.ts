// ============================================================
// API DE LABORATORIOS Y VMs
// ============================================================
import { request } from "./client";
import type { BackendLaboratory, BackendVM } from "../../models";

export const laboratoriesApi = {
  verifySSHLab: () => request<{
    read_only: boolean;
    ready_for_dynamic_lab: boolean;
    guacamole: { reachable: boolean; ssh_connection_found: boolean };
    database_state: { vm_found: boolean; vm_has_matching_ip: boolean; target_selection_matches: boolean; same_ip_records: number; challenge_found: boolean; dynamic_flag_count: number; pool_available: boolean };
    runtime: { ssh_reachable_from_api: boolean | null; injector_authenticated: boolean | null; redis_reservation_present: boolean | null; redis_reservation_ttl_seconds: number | null };
  }>("/admin/lab-ssh/verify"),

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
