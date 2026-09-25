// ============================================================
// RETOS Y FLAGS
// Responsabilidad: detalle, envío de flags y formulario de administración de retos.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api, Challenge, Run } from "../api";
import { difficultyStyle, categoryMeta } from "../config";
import { Icon, ErrorMessage } from "./common";

export function challengeInternalLevel(
  difficulty: Challenge["difficulty"]
) {
  if (difficulty === "Básico") return 1;
  if (difficulty === "Medio") return 2;
  return 3;
}

export function ChallengeCard({
  challenge,
  selected,
  onClick,
}: {
  challenge: Challenge;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`challenge-card ${
        selected ? "selected" : ""
      }`}
      onClick={onClick}
    >
      <div className="challenge-top">
        <span className="challenge-code">
          {challenge.code}
        </span>

        <div className="challenge-top-right">
          <span className="challenge-level-badge">
            Nivel {challengeInternalLevel(challenge.difficulty)}
          </span>

          <span
            className={`difficulty ${
              difficultyStyle[
                challenge.difficulty
              ]
            }`}
          >
            {challenge.difficulty}
          </span>
        </div>
      </div>

      <h3>{challenge.name}</h3>

      <div className="challenge-category">
        {challenge.category}
      </div>

      <p>{challenge.description}</p>

      <div className="challenge-foot">
        <span>
          {
            challenge.mitre_technique.split(
              " — "
            )[0]
          }
        </span>

        <strong>
          {challenge.points} pts
        </strong>
      </div>

      {challenge.completed && (
        <span className="completed-badge">
          <Icon name="check" />
          Completado
        </span>
      )}
    </button>
  );
}

export function ChallengeDetail({
  challenge,
  runs,
  onStart,
  onSubmit,
  username,
}: {
  challenge: Challenge | null;
  runs: Run[];
  onStart: (
    code: string
  ) => Promise<void>;
  onSubmit: (
    code: string,
    flag: string
  ) => Promise<{
    correct: boolean;
    challenge_completed: boolean;
    awarded_points: number;
    message: string;
  }>;
  username?: string;
}) {
  const [flag, setFlag] =
    useState("");

  const [busy, setBusy] =
    useState(false);

  const [notice, setNotice] =
    useState<{
      message: string;
      kind: "error" | "success";
    } | null>(null);

  const [submissionResult, setSubmissionResult] = useState<{
    correct: boolean;
    completed: boolean;
    awarded: number;
  } | null>(null);

  if (!challenge) {
    return (
      <div className="detail-empty">
        Selecciona un reto para acceder al
        laboratorio, seguir las instrucciones
        y enviar la flag.
      </div>
    );
  }

  const activeRun =
    runs.find(
      (run) =>
        run.challenge_code ===
          challenge.code &&
        run.status === "active"
    );

  const submit = async (
    event: FormEvent
  ) => {
    event.preventDefault();

    if (!flag.trim()) return;

    setBusy(true);
    setNotice(null);

    try {
      const result =
        await onSubmit(
          challenge.code,
          flag
        );

      setFlag("");
      setSubmissionResult({ correct: result.correct, completed: result.challenge_completed, awarded: result.awarded_points });

      setNotice({
        message: result.message,
        kind: result.correct
          ? "success"
          : "error",
      });
    } catch (err) {
      setNotice({
        message:
          err instanceof Error
            ? err.message
            : "No se pudo enviar la flag",
        kind: "error",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div>
          <span className="challenge-code">
            {challenge.code}
          </span>

          <h2>
            {challenge.name}
          </h2>
        </div>

        <span
          className={`difficulty ${
            difficultyStyle[
              challenge.difficulty
            ]
          }`}
        >
          {challenge.difficulty}
        </span>
      </div>

      <p className="detail-description">
        {challenge.description}
      </p>

      <div className="workspace-card challenge-run-card">
        <div>
          <span className="eyebrow accent">LABORATORIO ASIGNADO</span>
          <h3>{activeRun?.target_vm_name || "Entorno de práctica"}</h3>
          <p>
            {activeRun?.laboratory_code || "Laboratorio CTF"}
            {activeRun?.target_vm_ip ? ` · ${activeRun.target_vm_ip}` : ""}
            {activeRun?.target_protocol
              ? ` · ${activeRun.target_protocol.toUpperCase()}`
              : " · SSH"}
          </p>
          <small>
            Cuenta CTF / Guacamole: <strong>{username || "usuario actual"}</strong>
          </small>
        </div>

        {activeRun?.launch_url ? (
          <a
            href={activeRun.launch_url}
            target="_blank"
            rel="noreferrer"
            className="primary-action"
          >
            <Icon name="play" /> Abrir máquina asignada
          </a>
        ) : (
          <button
            type="button"
            className="primary-action"
            onClick={() => onStart(challenge.code)}
            disabled={busy}
          >
            <Icon name="play" />
            {challenge.completed
              ? "Reabrir entorno de práctica"
              : "Abrir máquina asignada"}
          </button>
        )}
      </div>

      <details className="challenge-accordion">
        <summary>
          <span>
            Información y configuración del reto
          </span>

          <small>
            Mostrar detalles
          </small>
        </summary>

        <div className="detail-meta">
          <div>
            <span>
              CATEGORÍA
            </span>

            <strong>
              {challenge.category}
            </strong>
          </div>

          <div>
            <span>
              DIFICULTAD
            </span>

            <strong>
              {challenge.difficulty}
            </strong>
          </div>

          <div>
            <span>
              PUNTAJE
            </span>

            <strong className="accent-text">
              {challenge.points} pts
            </strong>
          </div>

          <div>
            <span>
              ESCENARIO
            </span>

            <strong>
              {challenge.scenario ||
                "CTF general"}
            </strong>
          </div>

          <div>
            <span>MITRE</span>

            <strong>
              {challenge.mitre_technique}
            </strong>
          </div>

          <div>
            <span>
              ACTIVOS
            </span>

            <strong>
              {challenge.asset_references.join(
                " · "
              ) ||
                "Por definir"}
            </strong>
          </div>
        </div>
      </details>

      <details className="challenge-accordion">
        <summary>
          <span>
            Objetivo e instrucciones
          </span>

          <small>
            Mostrar detalles
          </small>
        </summary>

        <div className="instruction-box">
          <span>
            OBJETIVO DEL RETO
          </span>

          <p>
            {challenge.instructions}
          </p>
        </div>
      </details>

      <div className="hint-panel challenge-hints">
        <div className="hint-panel-head">
          <div><span className="eyebrow accent">AYUDAS DEL INSTRUCTOR</span><h3>Pistas y sugerencias</h3></div>
          <span className="hint-badge">sin revelar la flag</span>
        </div>
        {challenge.code === "LAB-01" ? (
          <div className="hint-list">
            <details><summary>Pista 1 · reconocimiento</summary><p>Comienza identificando qué servicios escucha la víctima <strong>192.168.146.137</strong>. Desde la Kali atacante puedes usar <code>nmap -sV 192.168.146.137</code>.</p></details>
            <details><summary>Pista 2 · acceso</summary><p>Cuando confirmes SSH, utiliza las credenciales entregadas por el instructor y entra por el puerto identificado. No necesitas cambiar la configuración del servidor.</p></details>
            <details><summary>Pista 3 · localización</summary><p>Una vez dentro, piensa en archivos destinados a ejercicios CTF. La ruta preparada para este laboratorio es <code>/opt/ctf/flag.txt</code>.</p></details>
          </div>
        ) : (
          <div className="hint-list"><details><summary>Sugerencia</summary><p>Lee el objetivo y divide el reto en pequeñas comprobaciones antes de intentar una respuesta final.</p></details></div>
        )}
      </div>

      {submissionResult && (
        <div className={`result-card ${submissionResult.correct ? "success" : "error"}`}>
          <div className="result-icon">{submissionResult.correct ? "✓" : "!"}</div>
          <div><span className="eyebrow">RESULTADO DE LA RESPUESTA</span><h3>{submissionResult.correct ? (submissionResult.completed ? "Reto completado" : "Flag correcta") : "Respuesta incorrecta"}</h3><p>{submissionResult.correct ? (submissionResult.completed ? `Has obtenido +${submissionResult.awarded} puntos.` : "Continúa con los objetivos restantes del ejercicio.") : "La respuesta no coincide con la flag esperada. Revisa las pistas y vuelve a intentarlo."}</p></div>
          {submissionResult.completed && <strong className="result-score">+{submissionResult.awarded} pts</strong>}
        </div>
      )}

      <ErrorMessage
        message={
          notice?.message ?? null
        }
        kind={
          notice?.kind ??
          "error"
        }
      />

      <div className="workspace-grid">
        <div className="workspace-card">
          <div className="workspace-top">
            <div>
              <span className="eyebrow">
                LABORATORIO
              </span>

              <h3>
                Entorno del reto
              </h3>
            </div>

            <span
              className={
                activeRun
                  ? "ready-chip"
                  : "muted-chip"
              }
            >
              {activeRun
                ? "Entorno listo"
                : "Sin sesión"}
            </span>
          </div>

          <div className="terminal-preview terminal-large">
            <div className="terminal-bar">
              <span>●</span>
              <span>●</span>
              <span>●</span>

              <b>
                guacamole /{" "}
                {challenge.code.toLowerCase()}
              </b>
            </div>

            <div className="terminal-body">
              <div>
                <span className="prompt">
                  kali@redteam:~$
                </span>{" "}
                sudo nmap -sV objetivo
              </div>

              <div className="terminal-dim">
                [+] Escenario autorizado:{" "}
                {challenge.code}
              </div>

              <div className="terminal-dim">
                [+] Activos:{" "}
                {challenge.asset_references.join(
                  ", "
                )}
              </div>

              <div className="terminal-cursor">
                █
              </div>
            </div>
          </div>

          <div className="workspace-actions">
            {activeRun ? (
              <a
                className="primary-action"
                href={
                  activeRun.launch_url
                }
                target="_blank"
                rel="noreferrer"
              >
                <Icon name="play" />
                Abrir Guacamole
              </a>
            ) : (
              <button
                className="primary-action"
                onClick={() =>
                  onStart(
                    challenge.code
                  )
                }
                disabled={busy}
              >
                <Icon name="play" />

                {challenge.completed
                  ? "Reabrir entorno de práctica"
                  : "Iniciar laboratorio"}
              </button>
            )}

            <span>
              <Icon name="clock" />

              {activeRun
                ? `Activo hasta ${new Date(
                    activeRun.expires_at
                  ).toLocaleTimeString(
                    [],
                    {
                      hour: "2-digit",
                      minute: "2-digit",
                    }
                  )}`
                : "El entorno se prepara al iniciar"}
            </span>
          </div>
        </div>

        <form
          className="flag-panel flag-panel-large"
          onSubmit={submit}
        >
          <div>
            <span className="eyebrow">
              ENVÍO DE FLAG
            </span>

            <h3>
              ¿Encontraste la flag?
            </h3>

            <p>
              Introduce la bandera obtenida
              durante la resolución del reto.
              La validación se realiza de forma
              segura en el backend.
            </p>
          </div>

          <div className="flag-submit-row">
            <input
              placeholder="FLAG{...}"
              value={flag}
              onChange={(e) =>
                setFlag(
                  e.target.value
                )
              }
              disabled={
                busy ||
                !activeRun
              }
            />

            <button
              className="primary-action"
              disabled={
                busy ||
                !activeRun
              }
            >
              <Icon name="flag" />

              {challenge.completed && !activeRun
                ? "Reto completado"
                : "Enviar flag"}
            </button>
          </div>

          {challenge.completed && !activeRun ? (
            <div className="flag-success">
              <Icon name="check" />

              Reto completado · {challenge.points} puntos obtenidos.
              Puedes reabrir el entorno para prácticas adicionales; no se
              otorgarán puntos nuevamente.
            </div>
          ) : (
            <div className="flag-helper">
              {challenge.completed
                ? "Entorno de práctica activo. Las respuestas correctas posteriores no generan puntos adicionales."
                : "Los intentos se registran para mantener la trazabilidad del CTF."}
            </div>
          )}

          <div className="attempt-panel">
            <div>
              <span>ESTADO</span>

              <strong>
                {activeRun ? "Sesión activa" : challenge.completed ? "Completado" : "Pendiente"}
              </strong>
            </div>

            <div>
              <span>VALOR</span>

              <strong>
                {challenge.points} pts
              </strong>
            </div>
          </div>
        </form>
      </div>
    </section>
  );
}

export function inferCategory(
  challenge: Challenge
): string {
  return (
    challenge.category ||
    "MISC"
  );
}

export function ChallengeForm({
  initial,
  onClose,
  onSave,
  laboratories = [],
  groups = [],
}: {
  initial: Challenge | null;
  onClose: () => void;
  onSave: (
    challenge: Omit<Challenge, "id" | "completed" | "flag_count" | "flags">,
    flags: Array<{
      id?: number;
      label: string;
      mode: "static" | "dynamic";
      value: string;
      template: string;
      flag_order: number;
      is_active: boolean;
    }>,
    groupIds: number[]
  ) => Promise<void>;
  laboratories?: Array<{
    id: number | string;
    code?: string | null;
    name: string;
    vms?: Array<{
      id: number | string;
      name: string;
      os?: string;
      operatingSystem?: string;
    }>;
  }>;
  groups?: Array<{
    id: number;
    name: string;
    code: string;
    challenges: Array<{ challenge_id: number; code: string; name: string }>;
  }>;
}) {
  const firstAsset = initial?.asset_references?.[0] ?? "";
  const [code, setCode] = useState(initial?.code ?? "");
  const [name, setName] = useState(initial?.name ?? "");
  const [category, setCategory] = useState(initial?.category ?? "MISC");
  const [difficulty, setDifficulty] = useState<Challenge["difficulty"]>(initial?.difficulty ?? "Básico");
  const [scenario, setScenario] = useState(initial?.scenario ?? "");
  const [mitre, setMitre] = useState(initial?.mitre_technique ?? "—");
  const [assets, setAssets] = useState(initial?.asset_references?.join(", ") ?? firstAsset);
  const [primaryAsset, setPrimaryAsset] = useState(firstAsset);
  const [points, setPoints] = useState(String(initial?.points ?? 100));
  const [description, setDescription] = useState(initial?.description ?? "");
  const [instructions, setInstructions] = useState(initial?.instructions ?? "");
  const [published, setPublished] = useState(initial?.is_published ?? true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  type Draft = {
    id?: number;
    label: string;
    mode: "static" | "dynamic";
    value: string;
    template: string;
    flag_order: number;
    is_active: boolean;
  };

  const [flags, setFlags] = useState<Draft[]>(() =>
    initial?.flags?.map((flag) => ({
      id: flag.id,
      label: flag.label,
      mode: flag.mode ?? "static",
      value: "",
      template: flag.template ?? `FLAG{${initial?.code ?? "CODE"}}-{{RUN_ID}}-{{RAND}}`,
      flag_order: flag.flag_order,
      is_active: flag.is_active,
    })) ?? []
  );

  const existingGroupIds = useMemo(
    () =>
      initial
        ? groups.filter((group) => group.challenges.some((item) => item.challenge_id === initial.id)).map((group) => group.id)
        : [],
    [groups, initial]
  );
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>(existingGroupIds);

  useEffect(() => {
    setSelectedGroupIds(existingGroupIds);
  }, [existingGroupIds]);

  useEffect(() => {
    if (!primaryAsset && laboratories[0]) {
      const fallback = laboratories[0].vms?.[0]?.name ?? laboratories[0].code ?? laboratories[0].name;
      setPrimaryAsset(fallback);
    }
  }, [laboratories, primaryAsset]);

  const assetOptions = useMemo(() => {
    const options: Array<{ value: string; label: string }> = [];
    laboratories.forEach((lab) => {
      const labValue = lab.code || lab.name;
      options.push({ value: labValue, label: `${labValue} · ${lab.name}` });
      (lab.vms ?? []).forEach((vm) => {
        options.push({ value: vm.name, label: `${vm.name} · ${vm.os || vm.operatingSystem || "VM"}` });
      });
    });
    return options;
  }, [laboratories]);

  const addFlag = () =>
    setFlags((current) => [
      ...current,
      {
        label: `Flag ${current.length + 1}`,
        mode: "static",
        value: "",
        template: "FLAG{ssh_{{USER}}_{{RUN_ID}}_{{RAND}}}",
        flag_order: current.length + 1,
        is_active: true,
      },
    ]);

  const updateFlag = (index: number, patch: Partial<Draft>) =>
    setFlags((current) => current.map((flag, i) => (i === index ? { ...flag, ...patch } : flag)));

  const toggleGroup = (groupId: number) =>
    setSelectedGroupIds((current) =>
      current.includes(groupId) ? current.filter((id) => id !== groupId) : [...current, groupId]
    );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const references = [primaryAsset, ...assets.split(",").map((value) => value.trim()).filter(Boolean)];
      const uniqueReferences = [...new Set(references.filter(Boolean))];
      if (!uniqueReferences.length) throw new Error("Selecciona al menos un laboratorio o una VM.");
      await onSave(
        {
          code: code.trim().toUpperCase(),
          name: name.trim(),
          category,
          difficulty,
          scenario: scenario || null,
          mitre_technique: mitre || "—",
          asset_references: uniqueReferences,
          points: Number(points),
          description: description.trim(),
          instructions: instructions.trim(),
          is_published: published,
        },
        flags,
        selectedGroupIds
      );
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar el reto");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <form className="modal-card challenge-modal" onSubmit={submit}>
        <div className="modal-head">
          <div>
            <span className="eyebrow accent">GESTIÓN DE RETO</span>
            <h2>{initial ? `Editar ${initial.code}` : "Nuevo reto"}</h2>
            <small>Relaciona el reto con un laboratorio real, grupos de estudiantes y sus flags.</small>
          </div>
          <button type="button" className="icon-btn" onClick={onClose}>×</button>
        </div>

        {error && <ErrorMessage message={error} />}

        <div className="form-grid">
          <label>Código<input value={code} onChange={(event) => setCode(event.target.value)} disabled={Boolean(initial)} required /></label>
          <label>Nombre<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
          <label>Categoría<select value={category} onChange={(event) => setCategory(event.target.value)}>{Object.keys(categoryMeta).map((value) => <option key={value}>{value}</option>)}</select></label>
          <label>Dificultad<select value={difficulty} onChange={(event) => setDifficulty(event.target.value as Challenge["difficulty"])}><option>Básico</option><option>Medio</option><option>Avanzado</option></select></label>
          <label>Escenario<input value={scenario} onChange={(event) => setScenario(event.target.value)} /></label>
          <label>MITRE<input value={mitre} onChange={(event) => setMitre(event.target.value)} /></label>
          <label>Laboratorio / VM
            <select value={primaryAsset} onChange={(event) => setPrimaryAsset(event.target.value)} required>
              <option value="">Selecciona un activo…</option>
              {assetOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
            <small className="field-help">La VM seleccionada determina IP, protocolo y conexión Guacamole cuando el jugador inicia el reto.</small>
          </label>
          <label>Puntos<input type="number" min="1" max="10000" value={points} onChange={(event) => setPoints(event.target.value)} required /></label>
        </div>

        <label className="form-full">Activos adicionales
          <input value={assets} onChange={(event) => setAssets(event.target.value)} placeholder="LAB-LNXVICT, otra-vm" />
          <small className="field-help">Opcional. Usa nombres exactos separados por comas.</small>
        </label>
        <label className="form-full">Descripción<textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} required /></label>
        <label className="form-full">Instrucciones del reto<textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={4} /></label>

        <section className="glass-panel flag-builder">
          <div className="panel-head">
            <div><span className="eyebrow accent">FLAGS</span><h3>Validación del reto</h3><small>Las flags dinámicas se generan por ejecución, se inyectan en la VM víctima y solo se valida su hash asociado a esa ejecución.</small></div>
            <button type="button" className="secondary-action" onClick={addFlag}>+ Añadir flag</button>
          </div>
          {flags.map((flag, index) => (
            <div className="flag-builder-row" key={flag.id ?? `new-${index}`}>
              <div className="flag-builder-head"><strong>Flag {flag.flag_order}</strong><button type="button" className="table-action danger" onClick={() => setFlags((current) => current.filter((_, i) => i !== index))}>Eliminar</button></div>
              <div className="form-grid">
                <label>Etiqueta<input value={flag.label} onChange={(event) => updateFlag(index, { label: event.target.value })} /></label>
                <label>Tipo<select value={flag.mode} onChange={(event) => updateFlag(index, { mode: event.target.value as Draft["mode"] })}><option value="static">Estática</option><option value="dynamic">Dinámica por ejecución</option></select></label>
                {flag.mode === "static" ? (
                  <label className="form-span-2">Valor<input value={flag.value} onChange={(event) => updateFlag(index, { value: event.target.value })} placeholder="FLAG{valor_estatico}" /></label>
                ) : (
                  <label className="form-span-2">Plantilla<input value={flag.template} onChange={(event) => updateFlag(index, { template: event.target.value })} /><small className="field-help">Variables: {'{{CODE}}'}, {'{{USER}}'}, {'{{RUN_ID}}'}, {'{{RAND}}'}</small></label>
                )}
                <label>Orden<input type="number" min="1" max="10" value={flag.flag_order} onChange={(event) => updateFlag(index, { flag_order: Number(event.target.value) })} /></label>
              </div>
              <label className="switch-row"><input type="checkbox" checked={flag.is_active} onChange={(event) => updateFlag(index, { is_active: event.target.checked })} /><span>Flag activa</span></label>
            </div>
          ))}
          {!flags.length && <div className="empty-card"><strong>No hay flags configuradas</strong><span>Añade una flag para poder iniciar el reto.</span></div>}
        </section>

        <section className="glass-panel assignment-panel">
          <div className="panel-head"><div><span className="eyebrow accent">GRUPOS</span><h3>Publicación por grupo</h3><small>Solo los estudiantes de los grupos seleccionados verán este reto.</small></div></div>
          <div className="selection-list">
            {groups.map((group) => (
              <label className="selection-row" key={group.id}>
                <input type="checkbox" checked={selectedGroupIds.includes(group.id)} onChange={() => toggleGroup(group.id)} />
                <span><strong>{group.code}</strong><small className="table-subline">{group.name} · {group.challenges.length} retos asignados</small></span>
              </label>
            ))}
          </div>
          {!groups.length && <div className="empty-card"><strong>No hay grupos</strong><span>Crea primero un grupo de estudiantes.</span></div>}
        </section>

        <label className="switch-row"><input type="checkbox" checked={published} onChange={(event) => setPublished(event.target.checked)} /><span>Publicar reto inmediatamente</span></label>
        <div className="modal-actions"><button type="button" className="secondary-action" onClick={onClose}>Cancelar</button><button className="primary-action" disabled={busy}>{busy ? "Guardando…" : initial ? "Guardar cambios" : "Crear reto"}</button></div>
      </form>
    </div>
  );
}
