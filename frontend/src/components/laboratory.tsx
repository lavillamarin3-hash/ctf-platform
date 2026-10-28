// ============================================================
// LABORATORIOS Y MÁQUINAS VIRTUALES
// Responsabilidad: formularios de infraestructura y transformación de datos.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { LabVM, Laboratory, LAB_NETWORK_METADATA, NETWORK_IPS, VM_OS_OPTIONS } from "../config";
import { api } from "../api";

export function LaboratoryForm({
  initial,
  onClose,
  onSave,
}: {
  initial: Laboratory | null;
  onClose: () => void;
  onSave: (
    laboratory: Laboratory
  ) => Promise<void>;
}) {
  const [code, setCode] =
    useState(
      initial?.code ?? ""
    );

  const [name, setName] =
    useState(
      initial?.name ?? ""
    );

  const [description, setDescription] =
    useState(
      initial?.description ?? ""
    );

  const [status, setStatus] =
    useState<
      Laboratory["status"]
    >(
      initial?.status ??
        "Planificado"
    );

  const [environment, setEnvironment] =
    useState(
      initial?.environment ??
        "Nutanix AHV · Guacamole"
    );

  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submit = async (
    event: FormEvent
  ) => {
    event.preventDefault();

    if (
      !code.trim() ||
      !name.trim()
    ) {
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      await onSave({
      id:
        initial?.id ??
        `lab-${Date.now()}`,
      code: code
        .trim()
        .toUpperCase(),
      name: name.trim(),
      description:
        description.trim() ||
        "Laboratorio del cyber range.",
      status,
      environment:
        environment.trim(),
      vms:
        initial?.vms ?? [],
      });
      onClose();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "No se pudo guardar el laboratorio");
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-backdrop">
      <form
        className="modal-card"
        onSubmit={submit}
      >
        <div className="modal-head">
          <div>
            <span className="eyebrow accent">
              LABORATORIO
            </span>

            <h2>
              {initial
                ? "Editar laboratorio"
                : "Nuevo laboratorio"}
            </h2>
          </div>

          <button
            type="button"
            className="icon-btn"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {saveError && <p role="alert" className="field-help">{saveError}</p>}
        <div className="form-grid">
          <label>
            Código

            <input
              value={code}
              onChange={(e) =>
                setCode(
                  e.target.value
                )
              }
              disabled={
                Boolean(initial)
              }
              placeholder="LAB-CTF-01"
              required
            />
          </label>

          <label>
            Nombre

            <input
              value={name}
              onChange={(e) =>
                setName(
                  e.target.value
                )
              }
              placeholder="Laboratorio Web"
              required
            />
          </label>

          <label>
            Estado

            <select
              value={status}
              onChange={(e) =>
                setStatus(
                  e.target
                    .value as Laboratory["status"]
                )
              }
            >
              <option>
                Disponible
              </option>

              <option>
                Planificado
              </option>

              <option>
                Mantenimiento
              </option>
            </select>
          </label>

          <label>
            Entorno

            <input
              value={environment}
              onChange={(e) =>
                setEnvironment(
                  e.target.value
                )
              }
              placeholder="Nutanix AHV · Guacamole"
            />
          </label>
        </div>

        <label className="form-full">
          Descripción

          <textarea
            value={description}
            onChange={(e) =>
              setDescription(
                e.target.value
              )
            }
            rows={5}
            placeholder="Descripción del laboratorio..."
          />
        </label>

        <div className="modal-actions">
          <button
            type="button"
            className="secondary-action"
            onClick={onClose}
          >
            Cancelar
          </button>

          <button className="primary-action" disabled={saving}>
            {saving ? "Guardando…" : initial
              ? "Guardar laboratorio"
              : "Crear laboratorio"}
          </button>
        </div>
      </form>
    </div>
  );
}

export function VMForm({
  laboratory,
  initial,
  onClose,
  onSave,
  guacamoleConnections = [],
}: {
  laboratory: Laboratory;
  initial: LabVM | null;
  onClose: () => void;
  onSave: (laboratoryId: string, vm: LabVM) => Promise<void>;
  guacamoleConnections?: import("../api").GuacamoleConnection[];
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [networkRole, setNetworkRole] = useState<"Atacantes" | "Víctimas">(initial?.networkRole ?? (initial?.vlan === "VLAN 20" ? "Atacantes" : "Víctimas"));
  const [ip, setIp] = useState(initial?.ip ?? "");
  const [operatingSystem, setOperatingSystem] = useState(initial?.operatingSystem ?? "Windows 10 (ES)");
  const [profile, setProfile] = useState<LabVM["profile"]>(initial?.profile ?? "Vulnerable");
  const [status, setStatus] = useState<NonNullable<LabVM["status"]>>(initial?.status ?? "planned");
  const [guacamoleConnectionId, setGuacamoleConnectionId] = useState(initial?.guacamoleConnectionId ?? "");
  const [saveErrorVm, setSaveErrorVm] = useState<string | null>(null);
  const [savingVm, setSavingVm] = useState(false);

  const usedIps = laboratory.vms.map((item) => item.ip).filter(Boolean);
  const availableIps = NETWORK_IPS[networkRole].filter((candidate) => !usedIps.includes(candidate) || candidate === initial?.ip);
  // "Sin asignar" es una elección explícita: no tomar otra IP al guardar.
  const selectedIp = ip;
  // Las VLAN de atacantes y víctimas se mantienen separadas.
  const subnet = networkRole === "Atacantes" ? "10.10.20.0/24" : "10.10.30.0/24";
  const segmentLabel = LAB_NETWORK_METADATA[networkRole].segment;

  const connectionForIp = (candidateIp: string) =>
    guacamoleConnections.find((item) => (item.hostname || "").trim() === candidateIp) ||
    guacamoleConnections.find((item) => (item.parameters?.hostname || "").trim() === candidateIp);

  useEffect(() => {
    if (!guacamoleConnectionId && ip) {
      const match = connectionForIp(ip);
      if (match) setGuacamoleConnectionId(match.identifier);
    }
  }, [guacamoleConnectionId, ip, guacamoleConnections]);

  /** Guarda la VM y conserva la conexión de Guacamole seleccionada. */
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !operatingSystem) return;
    setSavingVm(true);
    setSaveErrorVm(null);
    try {
      await onSave(laboratory.id, {
      id: initial?.id ?? `vm-${Date.now()}`,
      name: name.trim(),
      ip: selectedIp,
      operatingSystem,
      profile,
      status,
      networkRole,
      vlan: networkRole === "Atacantes" ? "VLAN 20" : "VLAN 30",
      subnet,
      guacamoleConnectionId: guacamoleConnectionId || undefined,
      guacamoleProtocol: guacamoleConnections.find((item) => item.identifier === guacamoleConnectionId)?.protocol,
      });
      onClose();
    } catch (err) {
      setSaveErrorVm(err instanceof Error ? err.message : "No se pudo guardar la MV");
    } finally { setSavingVm(false); }
  };

  return (
    <div className="modal-backdrop">
      <form className="modal-card" onSubmit={submit}>
        <div className="modal-head">
          <div><span className="eyebrow accent">MÁQUINA VIRTUAL</span><h2>{initial ? "Editar VM" : "Agregar VM"}</h2><small>{laboratory.code} · inventario del cyber range</small></div>
          <button type="button" className="icon-btn" onClick={onClose}>×</button>
        </div>
        {saveErrorVm && <p role="alert" className="field-help">{saveErrorVm}</p>}
        <div className="form-grid">
          <label>Nombre de VM<input value={name} onChange={(e) => setName(e.target.value)} placeholder="LAB-WINVICT-A" required /></label>
          <label>Rol de red<select value={networkRole} onChange={(e) => { const next = e.target.value as "Atacantes" | "Víctimas"; setNetworkRole(next); const first = NETWORK_IPS[next].find((item) => !usedIps.includes(item) || item === initial?.ip); setIp(first || ""); }}><option value="Atacantes">Atacante</option><option value="Víctimas">Víctima</option></select></label>
          <label>Dirección IP disponible<select value={ip} onChange={(e) => { const nextIp = e.target.value; setIp(nextIp); const match = connectionForIp(nextIp); setGuacamoleConnectionId(match?.identifier || ""); }}><option value="">Sin asignar</option>{availableIps.map((candidate) => <option key={candidate} value={candidate}>{candidate}</option>)}</select></label>
          <label>Sistema operativo<select value={operatingSystem} onChange={(e) => setOperatingSystem(e.target.value)}>{VM_OS_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label>Segmento de red<input value={`${segmentLabel} · ${subnet}`} readOnly /></label>
          <label>Perfil de seguridad<select value={profile} onChange={(e) => setProfile(e.target.value as LabVM["profile"])}><option>Vulnerable</option><option>Standard</option><option>Hardened</option></select></label>
          <label>Estado de la VM<select value={status} onChange={(e) => setStatus(e.target.value as NonNullable<LabVM["status"]>)}><option value="planned">Planificada</option><option value="ready">Lista (comprobada)</option><option value="maintenance">Mantenimiento</option><option value="offline">Apagada</option></select></label>
          <label>Conexión de Guacamole<select value={guacamoleConnectionId} onChange={(e) => setGuacamoleConnectionId(e.target.value)}><option value="">Sin asociar</option>{guacamoleConnections.map((item) => <option key={item.identifier} value={item.identifier}>{item.name} · {item.protocol.toUpperCase()}{item.hostname ? ` · ${item.hostname}` : ""}</option>)}</select></label>
        </div>
        <div className="network-preview"><span>{LAB_NETWORK_METADATA[networkRole].label}</span><strong>{selectedIp || "Sin IP"}</strong><small>{subnet}</small></div>
        <div className="modal-actions"><button type="button" className="secondary-action" onClick={onClose}>Cancelar</button><button className="primary-action" disabled={savingVm}>{savingVm ? "Guardando…" : initial ? "Guardar VM" : "Agregar VM"}</button></div>
      </form>
    </div>
  );
}

// ============================================================
/* TRANSFORMACIÓN DE RESPUESTAS DEL BACKEND */
// ============================================================

export function mapBackendVM(item: import("../api").BackendVM): LabVM {
  return {
    id: String(item.id),
    name: item.name,
    ip: item.ip_address || "",
    operatingSystem: item.os,
    profile: item.profile === "vulnerable" ? "Vulnerable" : item.profile === "hardened" ? "Hardened" : "Standard",
    networkRole: item.network_role === "Atacantes" ? "Atacantes" : item.network_role === "Víctimas" ? "Víctimas" : (item.vlan === "VLAN 20" ? "Atacantes" : "Víctimas"),
    vlan: item.vlan,
    subnet: item.subnet,
    status: item.status as LabVM["status"],
    guacamoleConnectionId: item.guacamole_connection_id || undefined,
    guacamoleProtocol: item.guacamole_protocol || undefined,
    guacamoleUrl: item.guacamole_url || undefined,
  };
}

export function mapBackendLaboratory(item: import("../api").BackendLaboratory): Laboratory {
  return {
    id: String(item.id),
    code: item.code || `LAB-${item.id}`,
    name: item.name,
    description: item.description,
    status: item.status === "ready" ? "Disponible" : item.status === "maintenance" ? "Mantenimiento" : "Planificado",
    environment: item.segment,
    vms: item.vms.map(mapBackendVM),
  };
}
