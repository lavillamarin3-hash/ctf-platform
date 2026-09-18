/** Usuario administrable dentro de Apache Guacamole. */
export type GuacamoleUser = {
  username: string;
  attributes: Record<string, string | null>;
  last_active?: number | null;
};

/** Estado de la integración con Guacamole. */
export type GuacamoleStatus = {
  mode: string;
  connected: boolean;
  base_url: string;
  data_source: string;
  username: string;
  user_count?: number | null;
};

/** Conexión remota administrada por Guacamole. */
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

/** Permisos de un usuario sobre Guacamole. */
export type GuacamolePermissionSet = {
  system_permissions: string[];
  connection_permissions: Record<string, string[]>;
};
