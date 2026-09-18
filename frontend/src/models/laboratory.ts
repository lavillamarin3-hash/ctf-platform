/** VM registrada dentro de un laboratorio. */
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

/** Laboratorio y su inventario de máquinas virtuales. */
export type BackendLaboratory = {
  id: number;
  code: string | null;
  name: string;
  description: string;
  segment: string;
  status: string;
  vms: BackendVM[];
};
