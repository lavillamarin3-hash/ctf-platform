/** Ejecución activa o histórica de un reto. */
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
