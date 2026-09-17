// ============================================================
// GUACAMOLE — FORMULARIOS DE ADMINISTRACIÓN
// Responsabilidad: editar usuarios, conexiones y permisos de
// Apache Guacamole sin mezclar esta lógica con ManagementApp.
// ============================================================

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import type {
  GuacamoleConnection,
  GuacamolePermissionSet,
  GuacamoleUser,
} from "../api";

const SYSTEM_PERMISSIONS = [
  "READ",
  "UPDATE",
  "CREATE",
  "DELETE",
  "AUDIT",
  "ADMINISTER",
] as const;

const CONNECTION_PERMISSIONS = [
  "READ",
  "UPDATE",
  "CREATE",
  "DELETE",
  "ADMINISTER",
] as const;

// ------------------------------------------------------------
// Usuario remoto de Guacamole
// ------------------------------------------------------------
export function GuacamoleUserForm({
  initial,
  onClose,
  onSave,
}: {
  initial: GuacamoleUser | null;
  onClose: () => void;
  onSave: (input: {
    username: string;
    password?: string;
    email?: string | null;
    full_name?: string | null;
    disabled?: boolean;
  }, initialUsername?: string) => Promise<void>;
}) {
  const [username, setUsername] = useState(initial?.username ?? "");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState(
    initial?.attributes?.["guac-full-name"] ?? "",
  );
  const [email, setEmail] = useState(
    initial?.attributes?.["guac-email-address"] ?? "",
  );
  const [disabled, setDisabled] = useState(
    initial?.attributes?.disabled === "true",
  );
  const [saving, setSaving] = useState(false);

  const editing = Boolean(initial);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!username.trim() || (!editing && !password.trim())) return;

    setSaving(true);
    try {
      await onSave(
        {
          username: username.trim(),
          password: password.trim() || undefined,
          email: email.trim() || null,
          full_name: fullName.trim() || null,
          disabled,
        },
        initial?.username,
      );
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <form className="modal-card" onSubmit={submit}>
        <div className="modal-head">
          <div>
            <span className="eyebrow accent">GUACAMOLE · USUARIO</span>
            <h2>{editing ? "Editar usuario remoto" : "Crear usuario remoto"}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        <div className="form-grid">
          <label>
            Usuario
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="estudiante01"
              disabled={editing || saving}
              autoFocus
              required
            />
          </label>

          <label>
            Contraseña {editing ? "(opcional)" : ""}
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={editing ? "Dejar vacío para conservar" : "Contraseña inicial"}
              disabled={saving}
              required={!editing}
            />
          </label>

          <label>
            Nombre completo
            <input
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Estudiante de laboratorio"
              disabled={saving}
            />
          </label>

          <label>
            Correo electrónico
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="estudiante@ejemplo.edu"
              disabled={saving}
            />
          </label>
        </div>

        <label className="switch-row">
          <input
            type="checkbox"
            checked={disabled}
            onChange={(event) => setDisabled(event.target.checked)}
            disabled={saving}
          />
          Cuenta deshabilitada en Guacamole
        </label>

        <div className="modal-actions">
          <button type="button" className="secondary-action" onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button type="submit" className="primary-action" disabled={saving || !username.trim() || (!editing && !password.trim())}>
            {saving ? "Guardando…" : editing ? "Guardar cambios" : "Crear usuario"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ------------------------------------------------------------
// Conexión SSH / RDP / VNC
// ------------------------------------------------------------
export function GuacamoleConnectionForm({
  initial,
  onClose,
  onSave,
}: {
  initial: GuacamoleConnection | null;
  onClose: () => void;
  onSave: (input: {
    name: string;
    protocol: "ssh" | "rdp" | "vnc";
    hostname: string;
    port: number;
    username?: string | null;
    password?: string | null;
    domain?: string | null;
    parent_identifier?: string;
  }, identifier?: string) => Promise<void>;
}) {
  const getParameter = (key: string) => initial?.parameters?.[key] ?? "";

  const [name, setName] = useState(initial?.name ?? "");
  const [protocol, setProtocol] = useState<"ssh" | "rdp" | "vnc">(initial?.protocol ?? "ssh");
  const [hostname, setHostname] = useState(initial?.hostname ?? "192.168.146.137");
  const [port, setPort] = useState(initial?.port ? Number(initial.port) : 22);
  const [username, setUsername] = useState(getParameter("username"));
  const [password, setPassword] = useState("");
  const [domain, setDomain] = useState(getParameter("domain"));
  const [parentIdentifier, setParentIdentifier] = useState(initial?.parent_identifier ?? "ROOT");
  const [saving, setSaving] = useState(false);

  const defaultPort = useMemo(() => {
    if (protocol === "rdp") return 3389;
    if (protocol === "vnc") return 5900;
    return 22;
  }, [protocol]);

  const changeProtocol = (value: "ssh" | "rdp" | "vnc") => {
    setProtocol(value);
    if (!initial) setPort(value === "rdp" ? 3389 : value === "vnc" ? 5900 : 22);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !hostname.trim() || !port) return;

    setSaving(true);
    try {
      await onSave(
        {
          name: name.trim(),
          protocol,
          hostname: hostname.trim(),
          port: Number(port),
          username: username.trim() || null,
          password: password.trim() || null,
          domain: domain.trim() || null,
          parent_identifier: parentIdentifier.trim() || "ROOT",
        },
        initial?.identifier,
      );
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <form className="modal-card" onSubmit={submit}>
        <div className="modal-head">
          <div>
            <span className="eyebrow accent">GUACAMOLE · CONEXIÓN</span>
            <h2>{initial ? "Editar conexión" : "Nueva conexión remota"}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        <div className="form-grid">
          <label>
            Nombre de conexión
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="LAB-01-VICTIMA"
              disabled={saving}
              required
              autoFocus
            />
          </label>

          <label>
            Protocolo
            <select value={protocol} onChange={(event) => changeProtocol(event.target.value as "ssh" | "rdp" | "vnc")} disabled={saving}>
              <option value="ssh">SSH</option>
              <option value="rdp">RDP</option>
              <option value="vnc">VNC</option>
            </select>
          </label>

          <label>
            Host / IP
            <input
              value={hostname}
              onChange={(event) => setHostname(event.target.value)}
              placeholder="192.168.146.137"
              disabled={saving}
              required
            />
          </label>

          <label>
            Puerto
            <input
              type="number"
              min={1}
              max={65535}
              value={port || defaultPort}
              onChange={(event) => setPort(Number(event.target.value))}
              disabled={saving}
              required
            />
          </label>

          <label>
            Usuario remoto
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="kali / usuario"
              disabled={saving}
            />
          </label>

          <label>
            Contraseña
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={initial ? "Dejar vacío para conservar" : "Contraseña SSH/RDP"}
              disabled={saving}
            />
          </label>

          <label>
            Dominio (RDP)
            <input
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="Opcional"
              disabled={saving}
            />
          </label>

          <label>
            Grupo padre
            <input
              value={parentIdentifier}
              onChange={(event) => setParentIdentifier(event.target.value)}
              placeholder="ROOT"
              disabled={saving}
            />
          </label>
        </div>

        <div className="form-full">
          <small className="form-help">
            Para tu laboratorio actual, la víctima SSH es <strong>192.168.146.137:22</strong>.
          </small>
        </div>

        <div className="modal-actions">
          <button type="button" className="secondary-action" onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button type="submit" className="primary-action" disabled={saving || !name.trim() || !hostname.trim() || !port}>
            {saving ? "Guardando…" : initial ? "Guardar conexión" : "Crear conexión"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ------------------------------------------------------------
// Permisos de usuario
// ------------------------------------------------------------
export function GuacamolePermissionsForm({
  username,
  initial,
  connections,
  onClose,
  onSave,
}: {
  username: string;
  initial: GuacamolePermissionSet;
  connections: GuacamoleConnection[];
  onClose: () => void;
  onSave: (value: GuacamolePermissionSet) => Promise<void>;
}) {
  const [systemPermissions, setSystemPermissions] = useState<string[]>(initial.system_permissions ?? []);
  const [connectionPermissions, setConnectionPermissions] = useState<Record<string, string[]>>(
    initial.connection_permissions ?? {},
  );
  const [saving, setSaving] = useState(false);

  const toggleSystem = (permission: string) => {
    setSystemPermissions((current) =>
      current.includes(permission)
        ? current.filter((item) => item !== permission)
        : [...current, permission],
    );
  };

  const toggleConnection = (identifier: string, permission: string) => {
    setConnectionPermissions((current) => {
      const selected = current[identifier] ?? [];
      const next = selected.includes(permission)
        ? selected.filter((item) => item !== permission)
        : [...selected, permission];

      const clone = { ...current };
      if (next.length) clone[identifier] = next;
      else delete clone[identifier];
      return clone;
    });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await onSave({
        system_permissions: systemPermissions,
        connection_permissions: connectionPermissions,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <form className="modal-card" onSubmit={submit}>
        <div className="modal-head">
          <div>
            <span className="eyebrow accent">GUACAMOLE · PERMISOS</span>
            <h2>Permisos de {username}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        <div className="permission-editor">
          <div className="permission-block">
            <div className="panel-head">
              <div>
                <span className="eyebrow">SISTEMA</span>
                <h3>Permisos generales</h3>
              </div>
            </div>

            <div className="permission-checks">
              {SYSTEM_PERMISSIONS.map((permission) => (
                <label className="check-row" key={permission}>
                  <input
                    type="checkbox"
                    checked={systemPermissions.includes(permission)}
                    onChange={() => toggleSystem(permission)}
                    disabled={saving}
                  />
                  <span>
                    <strong>{permission}</strong>
                    <small>{permission === "ADMINISTER" ? "Administración de Guacamole" : "Permiso de sistema"}</small>
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="permission-block">
            <div className="panel-head">
              <div>
                <span className="eyebrow">CONEXIONES</span>
                <h3>Acceso por conexión</h3>
              </div>
            </div>

            {connections.length === 0 ? (
              <div className="empty-card compact">
                <strong>No hay conexiones remotas</strong>
                <span>Crea primero una conexión para asignar permisos.</span>
              </div>
            ) : (
              <div className="permission-table">
                {connections.map((connection) => (
                  <div className="permission-row" key={connection.identifier}>
                    <div>
                      <strong>{connection.name}</strong>
                      <small>{connection.identifier} · {connection.protocol.toUpperCase()}</small>
                    </div>
                    <div className="permission-checks">
                      {CONNECTION_PERMISSIONS.map((permission) => (
                        <label className="check-row" key={permission} title={`${permission} sobre ${connection.name}`}>
                          <input
                            type="checkbox"
                            checked={(connectionPermissions[connection.identifier] ?? []).includes(permission)}
                            onChange={() => toggleConnection(connection.identifier, permission)}
                            disabled={saving}
                          />
                          <span>{permission}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="modal-actions">
          <button type="button" className="secondary-action" onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button type="submit" className="primary-action" disabled={saving}>
            {saving ? "Guardando…" : "Guardar permisos"}
          </button>
        </div>
      </form>
    </div>
  );
}
