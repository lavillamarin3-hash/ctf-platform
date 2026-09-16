// ============================================================
// PANEL DE ADMINISTRACIÓN / INSTRUCTOR
// Responsabilidad: orquestar estado de gestión y coordinar servicios.
// Las piezas visuales y formularios se mantienen en módulos especializados.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api, Challenge, RankingRow, User } from "../api";
import { Theme, ThemePreference, ManagementView, ManagedUser, UserFunction, Laboratory, LabVM, DEMO_USERS, DEFAULT_LABORATORIES, difficultyStyle } from "../config";
import { ManagementSidebar, Header, StatCard, Ranking, Icon } from "../components/common";
import { UserForm } from "../components/users";
import { GuacamoleUserForm, GuacamoleConnectionForm, GuacamolePermissionsForm } from "../components/guacamole";
import { LaboratoryForm, VMForm, mapBackendLaboratory, mapBackendVM } from "../components/laboratory";
import { ChallengeForm, inferCategory } from "../components/challenges";
import { GroupManagement } from "../components/groups";
import { GuestApp } from "./GuestApp";

const defaultUserFunction = (role: User["role"]): UserFunction =>
  role === "admin"
    ? "Administrador de laboratorio"
    : role === "instructor"
      ? "Instructor"
      : role === "player"
        ? "Estudiante"
        : "Otro";

const normalizeManagedUser = (
  item: User,
  fallback: Partial<Pick<ManagedUser, "full_name" | "user_function" | "organization">> = {},
): ManagedUser => ({
  ...item,
  full_name: item.full_name?.trim() || fallback.full_name?.trim() || item.username,
  user_function:
    (item.user_function as UserFunction) ||
    fallback.user_function ||
    defaultUserFunction(item.role),
  organization:
    item.organization?.trim() ||
    fallback.organization?.trim() ||
    "Sin organización",
  demo: (item as ManagedUser).demo,
});


export function ManagementApp({
  user,
  onLogout,
  theme,
  onToggleTheme,
  themePreference,
  onThemePreferenceChange,
  onUserChange,
  panelRole,
}: {
  user: User;
  onLogout: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  themePreference: ThemePreference;
  onThemePreferenceChange: (value: ThemePreference) => void;
  onUserChange: (user: User) => void;
  panelRole: "admin" | "instructor";
}) {
  const [view, setView] =
    useState<ManagementView>(
      "dashboard"
    );

  const [menuOpen, setMenuOpen] =
    useState(false);

  const [challenges, setChallenges] =
    useState<Challenge[]>([]);

  const [users, setUsers] =
    useState<ManagedUser[]>([]);

  const [userSearch, setUserSearch] =
    useState("");

  const [userRoleFilter, setUserRoleFilter] =
    useState<"Todas" | User["role"]>("Todas");

  const [userFormOpen, setUserFormOpen] =
    useState(false);

  const [userEditing, setUserEditing] =
    useState<ManagedUser | null>(null);

  const [ranking, setRanking] =
    useState<RankingRow[]>([]);

  const [groups, setGroups] =
    useState<import("../api").StudentGroup[]>([]);

  const [progressRows, setProgressRows] =
    useState<import("../api").ProgressRow[]>([]);

  const [message, setMessage] =
    useState<string | null>(
      null
    );

  const [editing, setEditing] =
    useState<Challenge | null>(
      null
    );

  const [creating, setCreating] =
    useState(false);

  /* ---------------- LABORATORIOS ---------------- */

  const [laboratories, setLaboratories] =
    useState<Laboratory[]>(() => {
      const saved =
        localStorage.getItem(
          "ctf-laboratories"
        );

      if (!saved) {
        return DEFAULT_LABORATORIES;
      }

      try {
        return JSON.parse(
          saved
        ) as Laboratory[];
      } catch {
        return DEFAULT_LABORATORIES;
      }
    });

  const [selectedLabId, setSelectedLabId] =
    useState<string | null>(
      DEFAULT_LABORATORIES[0]?.id ??
        null
    );

  const [labFormOpen, setLabFormOpen] =
    useState(false);

  const [labEditing, setLabEditing] =
    useState<Laboratory | null>(
      null
    );

  const [vmFormOpen, setVmFormOpen] =
    useState(false);

  const [vmEditing, setVmEditing] =
    useState<LabVM | null>(
      null
    );

  /* ---------------- GUACAMOLE ---------------- */

  const [guacamoleConnections, setGuacamoleConnections] =
    useState<import("../api").GuacamoleConnection[]>([]);

  const [guacamoleMode, setGuacamoleMode] =
    useState<"stub" | "real">("stub");

  const [guacamoleServiceAccount, setGuacamoleServiceAccount] =
    useState("");

  const [guacamoleServicePassword, setGuacamoleServicePassword] =
    useState("");

  const [guacamoleTested, setGuacamoleTested] =
    useState(false);

  const [guacamoleStatus, setGuacamoleStatus] =
    useState<import("../api").GuacamoleStatus | null>(null);

  const [guacamoleUsers, setGuacamoleUsers] =
    useState<import("../api").GuacamoleUser[]>([]);

  const [guacamoleLoading, setGuacamoleLoading] =
    useState(false);

  const [guacamoleFormOpen, setGuacamoleFormOpen] = useState(false);
  const [guacamoleUserEditing, setGuacamoleUserEditing] = useState<import("../api").GuacamoleUser | null>(null);
  const [guacamoleConnectionEditing, setGuacamoleConnectionEditing] = useState<import("../api").GuacamoleConnection | null>(null);
  const [guacamoleConnectionFormOpen, setGuacamoleConnectionFormOpen] = useState(false);
  const [guacamolePermissionsUser, setGuacamolePermissionsUser] = useState<string | null>(null);
  const [guacamolePermissions, setGuacamolePermissions] = useState<import("../api").GuacamolePermissionSet>({ system_permissions: [], connection_permissions: {} });
  const [guacamolePermissionsOpen, setGuacamolePermissionsOpen] = useState(false);



  useEffect(() => {
    localStorage.setItem(
      "ctf-laboratories",
      JSON.stringify(
        laboratories
      )
    );
  }, [laboratories]);

  const selectedLab =
    laboratories.find(
      (lab) =>
        lab.id ===
        selectedLabId
    ) ?? null;

  const isAdmin = panelRole === "admin";

  const loadGuacamole = useCallback(async () => {
    if (!isAdmin) return;
    setGuacamoleLoading(true);
    try {
      const [statusData, usersData, connectionData] = await Promise.all([
        api.guacamoleStatus(),
        api.guacamoleUsers(),
        api.guacamoleConnections(),
      ]);
      setGuacamoleStatus(statusData);
      setGuacamoleUsers(usersData);
      setGuacamoleConnections(connectionData);
      setGuacamoleMode(statusData.mode === "real" ? "real" : "stub");
      setGuacamoleTested(true);
      setMessage("Conexión con Guacamole verificada correctamente.");
    } catch (err) {
      setGuacamoleTested(false);
      setMessage(err instanceof Error ? err.message : "No se pudo consultar Guacamole");
    } finally {
      setGuacamoleLoading(false);
    }
  }, [isAdmin]);

  const testGuacamoleConnection = () => {
    void loadGuacamole();
  };

  const saveGuacamoleUser = async (input: { username: string; password?: string; email?: string | null; full_name?: string | null; disabled?: boolean }, initialUsername?: string) => {
    if (!isAdmin) return;
    try {
      if (initialUsername) {
        await api.updateGuacamoleUser(initialUsername, { password: input.password, email: input.email, full_name: input.full_name, disabled: input.disabled });
        setMessage("Usuario de Guacamole actualizado correctamente.");
      } else {
        await api.createGuacamoleUser({ username: input.username, password: input.password || "", email: input.email, full_name: input.full_name });
        setMessage("Usuario creado directamente en Guacamole.");
      }
      await loadGuacamole();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo actualizar Guacamole.");
    }
  };

  const deleteGuacamoleManagedUser = async (target: import("../api").GuacamoleUser) => {
    if (!isAdmin) return;
    if (!window.confirm(`¿Eliminar ${target.username} de Guacamole?`)) return;
    try { await api.deleteGuacamoleUser(target.username); await loadGuacamole(); setMessage("Usuario eliminado de Guacamole."); } catch (err) { setMessage(err instanceof Error ? err.message : "No se pudo eliminar el usuario remoto."); }
  };

  const saveGuacamoleConnection = async (input: { name:string; protocol:"ssh"|"rdp"|"vnc"; hostname:string; port:number; username?:string|null; password?:string|null; domain?:string|null; parent_identifier?:string }, identifier?:string) => {
    if (!isAdmin) return;
    try {
      if (identifier) await api.updateGuacamoleConnection(identifier, input);
      else await api.createGuacamoleConnection(input);
      await loadGuacamole();
      setMessage(identifier ? "Conexión de Guacamole actualizada correctamente." : "Conexión de Guacamole creada correctamente.");
    } catch (err) { setMessage(err instanceof Error ? err.message : "No se pudo guardar la conexión."); }
  };
  const deleteGuacamoleManagedConnection = async (connection: import("../api").GuacamoleConnection) => {
    if (!isAdmin) return;
    if (!window.confirm(`¿Eliminar la conexión ${connection.name}?`)) return;
    try { await api.deleteGuacamoleConnection(connection.identifier); await loadGuacamole(); setMessage("Conexión eliminada correctamente."); } catch (err) { setMessage(err instanceof Error ? err.message : "No se pudo eliminar la conexión."); }
  };
  const openGuacamolePermissions = async (username:string) => {
    try { const data = await api.guacamolePermissions(username); setGuacamolePermissions(data); setGuacamolePermissionsUser(username); setGuacamolePermissionsOpen(true); } catch (err) { setMessage(err instanceof Error ? err.message : "No se pudieron consultar los permisos."); }
  };
  const saveGuacamolePermissions = async (value: import("../api").GuacamolePermissionSet) => {
    if (!guacamolePermissionsUser) return;
    try { await api.updateGuacamolePermissions(guacamolePermissionsUser, value); setGuacamolePermissions(value); setGuacamolePermissionsOpen(false); setMessage("Permisos de Guacamole actualizados correctamente."); } catch (err) { setMessage(err instanceof Error ? err.message : "No se pudieron guardar los permisos."); }
  };


  const load = useCallback(
    async () => {
      try {
        const [
          challengeData,
          rank,
        ] = await Promise.all([
          api.challenges(),
          api.ranking(),
        ]);

        setChallenges(
          challengeData
        );

        setRanking(
          rank.rows
        );

        try {
          setGroups(await api.groups());
        } catch {
          setGroups([]);
        }

        if (isAdmin || panelRole === "instructor") {
          try {
            setProgressRows(await api.progressReport());
          } catch {
            setProgressRows([]);
          }
        }

        try {
          const backendLabs = await api.laboratories();
          if (backendLabs.length) {
            const mappedLabs = backendLabs.map(mapBackendLaboratory);
            setLaboratories(mappedLabs);
            setSelectedLabId((current) =>
              mappedLabs.some((item) => item.id === current)
                ? current
                : mappedLabs[0]?.id ?? null
            );
          }
        } catch {
          // Mantener inventario local de respaldo.
        }
      } catch (err) {
        setMessage(
          err instanceof Error
            ? err.message
            : "No se pudo cargar el panel"
        );
      }

      try {
        const backendUsers =
          await api.visibleUsers();

        const normalized: ManagedUser[] = backendUsers.map((item) =>
          normalizeManagedUser(item, {
            full_name: item.username,
            organization: "Cyber Lab",
          })
        );

        setUsers(normalized);
      } catch {
        setUsers(DEMO_USERS);
      }
    },
    [isAdmin, panelRole]
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (view === "groups") {
      void api.groups().then(setGroups).catch(() => setGroups([]));
    }
    if (view === "monitoring") {
      void api.progressReport().then(setProgressRows).catch(() => setProgressRows([]));
    }
  }, [view]);


  useEffect(() => {
    if ((view === "guacamole" || view === "laboratory") && isAdmin) {
      void loadGuacamole();
    }
  }, [view, isAdmin, loadGuacamole]);

  const published =
    challenges.filter(
      (c) =>
        c.is_published
    ).length;

  const draft =
    challenges.length -
    published;

  const points =
    challenges.reduce(
      (sum, c) =>
        sum + c.points,
      0
    );

  const activeUsers =
    users.filter(
      (u) =>
        u.is_active
    ).length;

  const roleLabel = isAdmin
    ? "Administrador"
    : "Instructor / Diseñador";

  const saveChallenge = async (input: Omit<Challenge,"id"|"completed"|"flag_count"|"flags">, draftFlags: Array<{id?:number;label:string;mode:"static"|"dynamic";value:string;template:string;flag_order:number;is_active:boolean}>, groupIds: number[] = []) => {
    let saved: Challenge;
    if (editing) saved = await api.updateChallenge(editing.code, input);
    else saved = await api.createChallenge(input);
    const existing = editing?.flags ?? [];
    for (const flag of existing) {
      if (!draftFlags.some(f => f.id === flag.id)) await api.deleteFlag(saved.code, flag.id);
    }
    for (const flag of draftFlags) {
      const payload = { label: flag.label.trim(), value: flag.mode === "static" ? (flag.value.trim() || undefined) : undefined, flag_order: flag.flag_order, is_active: flag.is_active, mode: flag.mode, template: flag.mode === "dynamic" ? flag.template.trim() : undefined };
      if (flag.id) await api.updateFlag(saved.code, flag.id, payload);
      else await api.createFlag(saved.code, payload);
    }
    const desired = new Set(groupIds);
    const assigned = groups.filter((g) => g.challenges.some((c) => c.challenge_id === saved.id)).map((g) => g.id);
    for (const groupId of desired) {
      if (!assigned.includes(groupId)) await api.assignChallengeGroup(saved.code, groupId);
    }
    for (const groupId of assigned) {
      if (!desired.has(groupId)) await api.unassignChallengeGroup(saved.code, groupId);
    }
    await load();
    setMessage(editing ? "Reto actualizado correctamente" : "Reto creado correctamente");
  };

  const archive = async (
    code: string
  ) => {
    if (
      !window.confirm(
        `¿Desactivar el reto ${code}? Se conservarán sus registros.`
      )
    ) {
      return;
    }

    try {
      await api.archiveChallenge(
        code
      );

      await load();

      setMessage(
        "Reto desactivado y conservado en el historial."
      );
    } catch (err) {
      setMessage(
        err instanceof Error
          ? err.message
          : "No se pudo desactivar el reto"
      );
    }
  };

  const changeUser = async (
    id: number,
    changes: Partial<
      Pick<
        User,
        "role" | "is_active"
      >
    >
  ) => {
    if (!isAdmin) {
      return;
    }

    const target = users.find(
      (item) => item.id === id
    );

    if (!target) return;

    if (target.demo) {
      setUsers((current) =>
        current.map((item) =>
          item.id === id
            ? { ...item, ...changes }
            : item
        )
      );

      setMessage(
        "Usuario de demostración actualizado localmente."
      );
      return;
    }

    try {
      const updated =
        await api.updateUser(
          id,
          changes
        );

      setUsers((current) =>
        current.map((item) =>
          item.id === id
            ? normalizeManagedUser({ ...item, ...updated })
            : item
        )
      );

      setMessage(
        "Usuario actualizado correctamente"
      );
    } catch (err) {
      setMessage(
        err instanceof Error
          ? err.message
          : "No se pudo actualizar el usuario"
      );
    }
  };

  const saveManagedUser = async (
    input: ManagedUser,
    password: string
  ) => {
    if (!isAdmin) return;

    if (userEditing) {
      await changeUser(
        userEditing.id,
        {
          role: input.role,
          is_active: input.is_active,
        }
      );

      setUsers((current) =>
        current.map((item) =>
          item.id === userEditing.id
            ? normalizeManagedUser(input)
            : item
        )
      );

      setMessage(
        input.demo
          ? "Usuario de demostración editado localmente."
          : "Usuario actualizado correctamente."
      );
    } else {
      try {
        const created = await api.createUser({
          username: input.username,
          email: input.email,
          password,
          role: input.role,
          full_name: input.full_name,
          sync_guacamole: true,
        });

        setUsers((current) => [
          normalizeManagedUser(created, {
            full_name: input.full_name,
            user_function: input.user_function,
            organization: input.organization,
          }),
          ...current.filter(
            (item) =>
              item.username.toLowerCase() !== created.username.toLowerCase()
          ),
        ]);

        setMessage("Usuario creado correctamente en CTF y sincronizado con Guacamole.");
        void loadGuacamole();
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "No se pudo crear el usuario");
      }
    }
  };

  const deleteManagedUser = (
    target: ManagedUser
  ) => {
    if (
      !isAdmin ||
      target.id === user.id
    ) {
      return;
    }

    if (
      !window.confirm(
        `¿Eliminar el usuario ${target.username}?`
      )
    ) {
      return;
    }

    setUsers((current) =>
      current.filter(
        (item) =>
          item.id !== target.id
      )
    );

    setMessage(
      target.demo
        ? "Usuario de demostración eliminado."
        : "Usuario retirado de la vista. La eliminación persistente requiere el endpoint backend."
    );
  };

  const visibleUsers = useMemo(() => {
    const query =
      userSearch.trim().toLowerCase();

    return users.filter(
      (item) => {
        if (!isAdmin && item.role === "admin") return false;
        const matchesRole =
          userRoleFilter === "Todas" ||
          item.role ===
            userRoleFilter;

        const matchesSearch =
          !query ||
          item.username
            .toLowerCase()
            .includes(query) ||
          item.full_name
            .toLowerCase()
            .includes(query) ||
          item.user_function
            .toLowerCase()
            .includes(query) ||
          item.organization
            .toLowerCase()
            .includes(query);

        return (
          matchesRole &&
          matchesSearch
        );
      }
    );
  }, [
    userRoleFilter,
    userSearch,
    users,
    isAdmin,
  ]);

  /* ---------------- PERSISTENCIA DE LABORATORIOS ---------------- */

  const saveLaboratory = async (laboratory: Laboratory) => {
    if (!isAdmin) return;
    const payload = {
      code: laboratory.code,
      name: laboratory.name,
      description: laboratory.description,
      segment: laboratory.environment,
      status: laboratory.status === "Disponible" ? "ready" : laboratory.status === "Mantenimiento" ? "maintenance" : "planned",
    } as const;
    try {
      const isPersisted = /^\d+$/.test(laboratory.id);
      const saved = isPersisted
        ? await api.updateLaboratory(Number(laboratory.id), payload)
        : await api.createLaboratory(payload);
      const mapped = mapBackendLaboratory(saved);
      setLaboratories((current) => isPersisted ? current.map((lab) => lab.id === laboratory.id ? mapped : lab) : [...current, mapped]);
      setSelectedLabId(mapped.id);
      setLabFormOpen(false);
      setMessage(isPersisted ? "Laboratorio actualizado correctamente." : "Laboratorio creado y guardado en la base de datos.");
    } catch (err) {
      // El fallback local permite continuar con una instalación anterior sin los endpoints nuevos.
      setLaboratories((current) => current.some((lab) => lab.id === laboratory.id) ? current.map((lab) => lab.id === laboratory.id ? laboratory : lab) : [...current, laboratory]);
      setSelectedLabId(laboratory.id);
      setMessage(err instanceof Error ? `${err.message} · Se conservó el cambio local.` : "No se pudo persistir el laboratorio.");
    }
  };

  const removeLaboratory = async (laboratory: Laboratory) => {
    if (!isAdmin) return;
    if (!window.confirm(`¿Eliminar ${laboratory.name}? Esta acción elimina también sus VMs registradas en la plataforma.`)) return;
    try {
      if (/^\d+$/.test(laboratory.id)) await api.deleteLaboratory(Number(laboratory.id));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo eliminar el laboratorio.");
      return;
    }
    setLaboratories((current) => current.filter((lab) => lab.id !== laboratory.id));
    setSelectedLabId(null);
    setMessage("Laboratorio eliminado correctamente.");
  };

  const saveVM = async (laboratoryId: string, vm: LabVM) => {
    if (!isAdmin) return;
    const targetLab = laboratories.find((lab) => lab.id === laboratoryId);
    if (!targetLab) return;
    const payload = {
      laboratory_id: Number(laboratoryId),
      name: vm.name,
      os: vm.operatingSystem,
      ip_address: vm.ip || null,
      vlan: vm.vlan || (vm.networkRole === "Atacantes" ? "VLAN 20" : "VLAN 30"),
      role: vm.networkRole || (vm.vlan === "VLAN 20" ? "Atacantes" : "Víctimas"),
      subnet: vm.subnet || (vm.vlan === "VLAN 20" ? "10.10.20.0/24" : "10.10.30.0/24"),
      network_role: vm.networkRole || (vm.vlan === "VLAN 20" ? "Atacantes" : "Víctimas"),
      profile: vm.profile.toLowerCase(),
      status: "ready",
      guacamole_connection_id: vm.guacamoleConnectionId || null,
    } as const;
    try {
      if (/^\d+$/.test(laboratoryId)) {
        const isPersisted = /^\d+$/.test(vm.id);
        const saved = isPersisted ? await api.updateVM(Number(vm.id), payload) : await api.createVM(payload);
        const mapped = mapBackendVM(saved);
        setLaboratories((current) => current.map((lab) => lab.id === laboratoryId ? { ...lab, vms: lab.vms.some((item) => item.id === vm.id) ? lab.vms.map((item) => item.id === vm.id ? mapped : item) : [...lab.vms, mapped] } : lab));
      } else {
        setLaboratories((current) => current.map((lab) => lab.id === laboratoryId ? { ...lab, vms: lab.vms.some((item) => item.id === vm.id) ? lab.vms.map((item) => item.id === vm.id ? vm : item) : [...lab.vms, vm] } : lab));
      }
      setMessage("Máquina virtual guardada correctamente.");
    } catch (err) {
      setLaboratories((current) => current.map((lab) => lab.id === laboratoryId ? { ...lab, vms: lab.vms.some((item) => item.id === vm.id) ? lab.vms.map((item) => item.id === vm.id ? vm : item) : [...lab.vms, vm] } : lab));
      setMessage(err instanceof Error ? `${err.message} · Se conservó el cambio local.` : "No se pudo persistir la VM.");
    }
  };

  const removeVM = async (laboratoryId: string, vm: LabVM) => {
    if (!isAdmin) return;
    if (!window.confirm(`¿Eliminar la VM ${vm.name}?`)) return;
    try {
      if (/^\d+$/.test(vm.id)) await api.deleteVM(Number(vm.id));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo eliminar la VM.");
      return;
    }
    setLaboratories((current) => current.map((lab) => lab.id === laboratoryId ? { ...lab, vms: lab.vms.filter((item) => item.id !== vm.id) } : lab));
    setMessage("VM eliminada correctamente.");
  };

  if (
    user.role ===
    "guest"
  ) {
    return (
      <GuestApp
        user={user}
        onLogout={onLogout}
        theme={theme}
        onToggleTheme={onToggleTheme}
        themePreference={themePreference}
        onThemePreferenceChange={onThemePreferenceChange}
        onUserChange={onUserChange}
      />
    );
  }

  return (
    <div className="app-shell">
      <ManagementSidebar
        view={view}
        setView={setView}
        open={menuOpen}
        onClose={() =>
          setMenuOpen(false)
        }
        role={user.role}
      />

      <div className="page-shell">
        <Header
          user={user}
          roleLabel={roleLabel}
          onLogout={onLogout}
          onOpenMenu={() =>
            setMenuOpen(true)
          }
          theme={theme}
          onToggleTheme={
            onToggleTheme
          }
          themePreference={themePreference}
          onThemePreferenceChange={onThemePreferenceChange}
          onUserChange={onUserChange}
        />

        <main className="main-content">
          {message && (
            <div className="global-message">
              <span>
                {message}
              </span>

              <button
                onClick={() =>
                  setMessage(
                    null
                  )
                }
              >
                ×
              </button>
            </div>
          )}

          {view ===
            "dashboard" && (
            <>
              <section className="hero">
                <div>
                  <span className="eyebrow accent">
                    {isAdmin
                      ? "ADMINISTRACIÓN"
                      : "DISEÑO DE RETOS"}
                  </span>

                  <h1>
                    Panel de{" "}
                    <em>
                      {isAdmin
                        ? "administración"
                        : "instructor"}
                    </em>
                  </h1>

                  <p>
                    {isAdmin
                      ? "Gestiona usuarios, retos, ranking y el estado general de la plataforma."
                      : "Diseña retos, revisa el progreso y supervisa los entornos del laboratorio."}
                  </p>
                </div>

                <div className="level-badge">
                  <span>
                    LABS
                  </span>

                  <strong>
                    {
                      laboratories.length
                    }
                  </strong>
                </div>
              </section>

              <section className="stats-grid">
                <StatCard
                  label="Retos"
                  value={
                    challenges.length
                  }
                  helper={`${published} publicados`}
                  icon="flag"
                  accent="purple"
                />

                <StatCard
                  label="Usuarios activos"
                  value={
                    activeUsers ||
                    ranking.length
                  }
                  helper={`${ranking.length} jugadores en ranking`}
                  icon="users"
                  accent="green"
                />

                <StatCard
                  label="Puntos disponibles"
                  value={points.toLocaleString(
                    "es-ES"
                  )}
                  helper="Catálogo actual"
                  icon="trophy"
                  accent="cyan"
                />

                <StatCard
                  label="Laboratorios"
                  value={
                    laboratories.length
                  }
                  helper="Entornos configurados"
                  icon="lab"
                  accent="blue"
                />
              </section>

              <div className="admin-grid">
                <section className="glass-panel admin-panel">
                  <div className="panel-head">
                    <div>
                      <span className="eyebrow">
                        ACCESOS
                      </span>

                      <h3>
                        Gestión rápida
                      </h3>
                    </div>
                  </div>

                  <div className="admin-actions">
                    <button
                      className="admin-action"
                      onClick={() =>
                        setView(
                          "challenges"
                        )
                      }
                    >
                      <Icon name="flag" />

                      <span>
                        <strong>
                          Gestionar retos
                        </strong>

                        <small>
                          Crear, editar, publicar y
                          desactivar
                        </small>
                      </span>
                    </button>

                    {isAdmin && (
                      <button
                        className="admin-action"
                        onClick={() =>
                          setView(
                            "users"
                          )
                        }
                      >
                        <Icon name="users" />

                        <span>
                          <strong>
                            Gestionar usuarios
                          </strong>

                          <small>
                            Modificar rol y habilitación
                            de cuentas
                          </small>
                        </span>
                      </button>
                    )}

                    <button
                      className="admin-action"
                      onClick={() =>
                        setView(
                          "laboratory"
                        )
                      }
                    >
                      <Icon name="lab" />

                      <span>
                        <strong>
                          Laboratorios / VMs
                        </strong>

                        <small>
                          {
                            laboratories.length
                          }{" "}
                          laboratorios ·{" "}
                          {laboratories.reduce(
                            (
                              sum,
                              lab
                            ) =>
                              sum +
                              lab.vms
                                .length,
                            0
                          )}{" "}
                          VMs
                        </small>
                      </span>
                    </button>

                    <button
                      className="admin-action"
                      onClick={() =>
                        setView(
                          "ranking"
                        )
                      }
                    >
                      <Icon name="trophy" />

                      <span>
                        <strong>
                          Ranking real
                        </strong>

                        <small>
                          Resultados calculados desde
                          los completados
                        </small>
                      </span>
                    </button>
                  </div>
                </section>

                <Ranking
                  rows={ranking}
                  user={user}
                />
              </div>
            </>
          )}

          {view ===
            "challenges" && (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">
                    GESTIÓN DE CONTENIDO
                  </span>

                  <h1>
                    Retos
                  </h1>

                  <p>
                    Administra el catálogo
                    directamente desde la plataforma.
                  </p>
                </div>

                <div className="page-actions">
                  <button
                    className="secondary-action"
                    onClick={() =>
                      void load()
                    }
                  >
                    Actualizar
                  </button>

                  <button
                    className="primary-action"
                    onClick={() => {
                      setEditing(
                        null
                      );

                      setCreating(
                        true
                      );
                    }}
                  >
                    + Nuevo reto
                  </button>
                </div>
              </div>

              <div className="table-panel glass-panel">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nombre</th>
                      <th>Categoría</th>
                      <th>Dificultad</th>
                      <th>MITRE</th>
                      <th>
                        VM / Activo
                      </th>
                      <th>Puntos</th>
                      <th>Estado</th>
                      <th>
                        Acciones
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {challenges.map(
                      (c) => (
                        <tr
                          key={
                            c.id
                          }
                        >
                          <td>
                            {c.code}
                          </td>

                          <td>
                            <strong>
                              {c.name}
                            </strong>
                          </td>

                          <td>
                            <span className="category-tag">
                              {inferCategory(
                                c
                              )}
                            </span>
                          </td>

                          <td>
                            <span
                              className={`difficulty ${
                                difficultyStyle[
                                  c.difficulty
                                ]
                              }`}
                            >
                              {
                                c.difficulty
                              }
                            </span>
                          </td>

                          <td>
                            {
                              c.mitre_technique.split(
                                " — "
                              )[0]
                            }
                          </td>

                          <td>
                            {c.asset_references.join(
                              ", "
                            ) ||
                              "—"}
                          </td>

                          <td>
                            {c.points}
                          </td>

                          <td>
                            <span
                              className={
                                c.is_published
                                  ? "status-published"
                                  : "status-draft"
                              }
                            >
                              {c.is_published
                                ? "Publicado"
                                : "Inactivo"}
                            </span>
                          </td>

                          <td>
                            <div className="row-actions">
                              <button
                                className="table-action"
                                onClick={() => {
                                  setEditing(
                                    c
                                  );

                                  setCreating(
                                    true
                                  );
                                }}
                              >
                                Editar
                              </button>

                              <button
                                className="table-action danger"
                                onClick={() =>
                                  void archive(
                                    c.code
                                  )
                                }
                                disabled={
                                  !c.is_published
                                }
                              >
                                Desactivar
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>

                {challenges.length ===
                  0 && (
                  <div className="empty-card">
                    <strong>
                      No hay retos cargados
                    </strong>
                  </div>
                )}
              </div>
            </section>
          )}

          {view === "groups" && (isAdmin || panelRole === "instructor") && (
            <GroupManagement isAdmin={isAdmin} onMessage={setMessage} />
          )}

          {view === "monitoring" && (isAdmin || panelRole === "instructor") && (
            <section>
              <div className="page-heading">
                <div><span className="eyebrow accent">SEGUIMIENTO</span><h1>Seguimiento de estudiantes</h1><p>Consulta el avance de los estudiantes sobre los retos asignados a sus grupos.</p></div>
                <div className="page-actions"><button className="secondary-action" onClick={() => void api.progressReport().then(setProgressRows).catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar el seguimiento"))}>Actualizar</button></div>
              </div>
              <div className="table-panel glass-panel">
                <table><thead><tr><th>Estudiante</th><th>Reto</th><th>Estado</th><th>Intentos</th><th>Puntos</th><th>Completado</th></tr></thead>
                  <tbody>{progressRows.map((row, i) => <tr key={`${row.user_id}-${row.challenge_code}-${i}`}><td><strong>{row.username}</strong></td><td>{row.challenge_code} · {row.challenge_name}</td><td><span className={row.status === "Completado" ? "status-published" : "status-draft"}>{row.status}</span></td><td>{row.attempts}</td><td>{row.points}</td><td>{row.completed_at ? new Date(row.completed_at).toLocaleString() : "—"}</td></tr>)}</tbody>
                </table>
                {progressRows.length === 0 && <div className="empty-card"><strong>No hay actividad registrada</strong><span>Los resultados aparecerán cuando existan estudiantes en grupos con retos asignados.</span></div>}
              </div>
            </section>
          )}

          {/* ==================================================
              LABORATORIOS Y MÁQUINAS VIRTUALES
              ================================================== */}
          {view === "laboratory" && (
            <section>
              <div className="page-heading">
                <div>
                  <span className="eyebrow accent">INFRAESTRUCTURA</span>
                  <h1>Laboratorios / VMs</h1>
                  <p>
                    Administra los entornos del cyber range, sus máquinas virtuales, redes e IPs desde la plataforma CTF.
                  </p>
                </div>

                <div className="page-actions">
                  <button
                    className="secondary-action"
                    onClick={() => void load()}
                  >
                    Actualizar
                  </button>
                  {isAdmin && (
                    <button
                      className="primary-action"
                      onClick={() => {
                        setLabEditing(null);
                        setLabFormOpen(true);
                      }}
                    >
                      + Nuevo laboratorio
                    </button>
                  )}
                </div>
              </div>

              <div className="stats-grid">
                <StatCard
                  label="Laboratorios"
                  value={laboratories.length}
                  helper="Entornos registrados"
                  icon="lab"
                  accent="blue"
                />
                <StatCard
                  label="Máquinas virtuales"
                  value={laboratories.reduce((sum, lab) => sum + lab.vms.length, 0)}
                  helper="VMs registradas"
                  icon="settings"
                  accent="purple"
                />
                <StatCard
                  label="Víctimas"
                  value={laboratories.reduce((sum, lab) => sum + lab.vms.filter((vm) => vm.networkRole === "Víctimas").length, 0)}
                  helper="VLAN 30 · 10.10.30.0/24"
                  icon="target"
                  accent="green"
                />
                <StatCard
                  label="Atacantes"
                  value={laboratories.reduce((sum, lab) => sum + lab.vms.filter((vm) => vm.networkRole === "Atacantes").length, 0)}
                  helper="VLAN 20 · 10.10.20.0/24"
                  icon="arrow"
                  accent="cyan"
                />
              </div>

              <div className="admin-grid" style={{ marginTop: "13px" }}>
                <section className="glass-panel admin-panel">
                  <div className="panel-head">
                    <div>
                      <span className="eyebrow">INVENTARIO</span>
                      <h3>Laboratorios disponibles</h3>
                    </div>
                    <span className="user-count">{laboratories.length} entorno{laboratories.length === 1 ? "" : "s"}</span>
                  </div>

                  <div className="admin-actions">
                    {laboratories.map((lab) => (
                      <button
                        key={lab.id}
                        type="button"
                        className={`admin-action ${selectedLabId === lab.id ? "active" : ""}`}
                        onClick={() => setSelectedLabId(lab.id)}
                      >
                        <Icon name="lab" />
                        <span>
                          <strong>{lab.name}</strong>
                          <small>
                            {lab.code} · {lab.vms.length} VM{lab.vms.length === 1 ? "" : "s"} · {lab.environment}
                          </small>
                        </span>
                      </button>
                    ))}
                  </div>

                  {laboratories.length === 0 && (
                    <div className="empty-card">
                      <strong>No hay laboratorios registrados</strong>
                      <span>Crea el primer entorno para comenzar a asociar máquinas virtuales.</span>
                    </div>
                  )}
                </section>

                {selectedLab ? (
                  <section className="glass-panel admin-panel">
                    <div className="panel-head">
                      <div>
                        <span className="eyebrow accent">{selectedLab.code}</span>
                        <h3>{selectedLab.name}</h3>
                        <small>{selectedLab.description}</small>
                      </div>
                      <div className="row-actions">
                        <span className={selectedLab.status === "Disponible" ? "status-published" : selectedLab.status === "Mantenimiento" ? "status-draft" : "category-tag"}>
                          {selectedLab.status}
                        </span>
                        {isAdmin && (
                          <button
                            className="table-action"
                            onClick={() => {
                              setLabEditing(selectedLab);
                              setLabFormOpen(true);
                            }}
                          >
                            Editar
                          </button>
                        )}
                        {isAdmin && (
                          <button
                            className="table-action danger"
                            onClick={() => void removeLaboratory(selectedLab)}
                          >
                            Eliminar
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="info-panel">
                      <span className="eyebrow">ENTORNO</span>
                      <p><strong>{selectedLab.environment}</strong></p>
                      <small>Las IPs se controlan desde el backend para evitar duplicados en el inventario.</small>
                    </div>

                    <div className="panel-head" style={{ marginTop: "13px" }}>
                      <div>
                        <span className="eyebrow">MÁQUINAS VIRTUALES</span>
                        <h3>Activos del laboratorio</h3>
                      </div>
                      {isAdmin && (
                        <button
                          className="secondary-action"
                          onClick={() => {
                            setVmEditing(null);
                            setVmFormOpen(true);
                          }}
                        >
                          + Agregar VM
                        </button>
                      )}
                    </div>

                    <div className="table-panel" style={{ marginTop: "10px" }}>
                      <table>
                        <thead>
                          <tr>
                            <th>VM</th>
                            <th>Sistema operativo</th>
                            <th>Red</th>
                            <th>IP</th>
                            <th>Perfil</th>
                            <th>Guacamole</th>
                            <th>Acciones</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedLab.vms.map((vm) => (
                            <tr key={vm.id}>
                              <td><strong>{vm.name}</strong></td>
                              <td>{vm.operatingSystem}</td>
                              <td>
                                <span className="category-tag">
                                  {vm.networkRole || (vm.vlan === "VLAN 20" ? "Atacantes" : "Víctimas")} · {vm.vlan}
                                </span>
                              </td>
                              <td>{vm.ip || "Sin asignar"}</td>
                              <td>{vm.profile}</td>
                              <td>
                                {vm.guacamoleConnectionId ? (
                                  <span className="category-tag">
                                    {guacamoleConnections.find((item) => item.identifier === vm.guacamoleConnectionId)?.name || vm.guacamoleConnectionId}
                                    {vm.guacamoleProtocol ? ` · ${vm.guacamoleProtocol.toUpperCase()}` : ""}
                                  </span>
                                ) : (
                                  <span className="self-label">Sin asociar</span>
                                )}
                              </td>
                              <td>
                                <div className="row-actions">
                                  {isAdmin ? (
                                    <>
                                      <button
                                        className="table-action"
                                        onClick={() => {
                                          setVmEditing(vm);
                                          setVmFormOpen(true);
                                        }}
                                      >
                                        Editar
                                      </button>
                                      <button
                                        className="table-action danger"
                                        onClick={() => void removeVM(selectedLab.id, vm)}
                                      >
                                        Eliminar
                                      </button>
                                    </>
                                  ) : (
                                    <span className="self-label">Solo lectura</span>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {selectedLab.vms.length === 0 && (
                        <div className="empty-card">
                          <strong>Este laboratorio todavía no tiene VMs</strong>
                          <span>Agrega una máquina y define su sistema operativo, red e IP.</span>
                        </div>
                      )}
                    </div>
                  </section>
                ) : (
                  <section className="glass-panel admin-panel">
                    <div className="empty-card">
                      <strong>Selecciona un laboratorio</strong>
                      <span>Elige un entorno del inventario para consultar sus máquinas virtuales.</span>
                    </div>
                  </section>
                )}
              </div>

              <div className="info-panel glass-panel" style={{ marginTop: "13px" }}>
                <span className="eyebrow">MODELO DE RED</span>
                <p>
                  <strong>Atacante:</strong> 192.168.146.134. &nbsp;
                  <strong>Víctima:</strong> 192.168.164.137.
                </p>
              </div>
            </section>
          )}

          {view ===
            "users" &&
            (isAdmin ||
              user.role === "instructor") && (
              <section>
                <div className="page-heading">
                  <div>
                    <span className="eyebrow accent">
                      {isAdmin
                        ? "ADMINISTRACIÓN"
                        : "SUPERVISIÓN"}
                    </span>

                    <h1>
                      Usuarios y roles
                    </h1>

                    <p>
                      {isAdmin
                        ? "Gestiona cuentas, roles, funciones y estado de acceso."
                        : "Consulta las cuentas registradas, sus roles y funciones."}
                    </p>
                  </div>

                  <div className="page-actions">
                    <button
                      className="secondary-action"
                      onClick={() =>
                        void load()
                      }
                    >
                      Actualizar
                    </button>

                    {isAdmin && (
                      <>
                        <button
                          className="secondary-action"
                          onClick={() => {
                            setGuacamoleUserEditing(null);
                            setGuacamoleFormOpen(true);
                          }}
                          title="Crear una cuenta directamente en Apache Guacamole"
                        >
                          + Usuario Guacamole
                        </button>

                        <button
                          className="primary-action"
                          onClick={() => {
                            setUserEditing(null);
                            setUserFormOpen(true);
                          }}
                        >
                          + Nuevo usuario
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <div className="user-toolbar glass-panel">
                  <input
                    className="user-search"
                    value={userSearch}
                    onChange={(e) =>
                      setUserSearch(
                        e.target.value
                      )
                    }
                    placeholder="Buscar por usuario, nombre, correo o función..."
                    aria-label="Buscar usuarios"
                  />

                  <select
                    className="table-select user-role-filter"
                    value={userRoleFilter}
                    onChange={(e) =>
                      setUserRoleFilter(
                        e.target.value as
                          | "Todas"
                          | User["role"]
                      )
                    }
                    aria-label="Filtrar usuarios por rol"
                  >
                    <option value="Todas">
                      Todos los roles
                    </option>
                    <option value="admin">
                      Administrador
                    </option>
                    <option value="instructor">
                      Instructor
                    </option>
                    <option value="player">
                      Jugador
                    </option>
                    <option value="guest">
                      Invitado
                    </option>
                  </select>

                  <span className="user-count">
                    {visibleUsers.length} resultado{visibleUsers.length === 1 ? "" : "s"}
                  </span>
                </div>

                <div className="role-summary">
                  {(
                    [
                      ["admin", "Administradores"],
                      ["instructor", "Instructores"],
                      ["player", "Jugadores"],
                      ["guest", "Invitados"],
                    ] as const
                  )
                    .filter(([roleKey]) => user.role === "admin" || roleKey !== "admin")
                    .map(
                    ([roleKey, label]) => {
                      const total =
                        users.filter(
                          (item) =>
                            item.role ===
                            roleKey
                        ).length;

                      return (
                        <button
                          type="button"
                          key={roleKey}
                          className={`role-summary-card ${
                            userRoleFilter ===
                            roleKey
                              ? "active"
                              : ""
                          }`}
                          onClick={() =>
                            setUserRoleFilter(
                              userRoleFilter ===
                                roleKey
                                ? "Todas"
                                : roleKey
                            )
                          }
                        >
                          <strong>
                            {total}
                          </strong>

                          <span>
                            {label}
                          </span>
                        </button>
                      );
                    }
                  )}
                </div>

                <div className="table-panel glass-panel">
                  <table>
                    <thead>
                      <tr>
                        <th>Usuario</th>
                        <th>Nombre</th>
                        <th>Correo</th>
                        <th>Rol</th>
                        <th>Función</th>
                        <th>Organización</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>

                    <tbody>
                      {visibleUsers.map(
                        (u) => (
                          <tr key={u.id}>
                            <td>
                              <strong>
                                {u.username}
                              </strong>

                              {u.demo && (
                                <span className="self-label">
                                  DEMO
                                </span>
                              )}
                            </td>

                            <td>
                              {u.full_name}
                            </td>

                            <td>
                              {u.email ||
                                "—"}
                            </td>

                            <td>
                              {isAdmin ? (
                                (u.role === "admin" || u.role === "instructor") ? (
                                  <span className="category-tag role-protected" title="Cuenta protegida">
                                    {u.role === "admin" ? "Administrador" : "Instructor"} · Protegido
                                  </span>
                                ) : (
                                  <select
                                    className="table-select"
                                    value={u.role}
                                    title="Asignar rol de plataforma"
                                    onChange={(e) =>
                                      void changeUser(
                                        u.id,
                                        {
                                          role:
                                            e.target
                                              .value as User["role"],
                                        }
                                      )
                                    }
                                  >
                                    <option value="player">
                                      Jugador
                                    </option>
                                    <option value="guest">
                                      Invitado
                                    </option>
                                    <option value="instructor">
                                      Instructor
                                    </option>
                                  </select>
                                )
                              ) : (
                                <span className="category-tag">
                                  {u.role ===
                                  "admin"
                                    ? "Administrador"
                                    : u.role ===
                                        "instructor"
                                      ? "Instructor"
                                      : u.role ===
                                          "player"
                                        ? "Jugador"
                                        : "Invitado"}
                                </span>
                              )}
                            </td>

                            <td>
                              <span className="category-tag">
                                {u.user_function}
                              </span>
                            </td>

                            <td>
                              {u.organization}
                            </td>

                            <td>
                              <span
                                className={
                                  u.is_active
                                    ? "status-published"
                                    : "status-draft"
                                }
                              >
                                {u.is_active
                                  ? "Activo"
                                  : "Deshabilitado"}
                              </span>
                            </td>

                            <td>
                              {isAdmin ? (
                                <div className="row-actions">
                                  <button
                                    className="table-action"
                                    onClick={() => {
                                      setUserEditing(
                                        u
                                      );
                                      setUserFormOpen(
                                        true
                                      );
                                    }}
                                  >
                                    Editar
                                  </button>

                                  <button
                                    className={`table-action ${
                                      u.is_active
                                        ? "danger"
                                        : "success"
                                    }`}
                                    onClick={() =>
                                      void changeUser(
                                        u.id,
                                        {
                                          is_active:
                                            !u.is_active,
                                        }
                                      )
                                    }
                                    disabled={
                                      u.id ===
                                      user.id
                                    }
                                  >
                                    {u.is_active
                                      ? "Deshabilitar"
                                      : "Habilitar"}
                                  </button>

                                  <button
                                    className="table-action danger"
                                    onClick={() =>
                                      deleteManagedUser(
                                        u
                                      )
                                    }
                                    disabled={
                                      u.id ===
                                      user.id
                                    }
                                  >
                                    Eliminar
                                  </button>
                                </div>
                              ) : (
                                <span className="self-label">
                                  Solo lectura
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>

                  {visibleUsers.length ===
                    0 && (
                    <div className="empty-card">
                      <strong>
                        No hay usuarios que coincidan
                      </strong>
                      <span>
                        Cambia el filtro o realiza otra búsqueda.
                      </span>
                    </div>
                  )}
                </div>

                <div className="info-panel glass-panel user-permission-note">
                  <span className="eyebrow">
                    PERMISOS
                  </span>

                  <p>
                    {isAdmin
                      ? "Administrador: puede crear, editar, habilitar, deshabilitar y eliminar usuarios."
                      : "Instructor: puede consultar los usuarios, roles y funciones, pero no puede modificarlos."}
                  </p>
                </div>
              </section>
            )}

          {/* ==================================================
              GUACAMOLE - ADMINISTRACIÓN
              ================================================== */}
          {view === "guacamole" && isAdmin && (
            <section>
              <div className="page-heading"><div><span className="eyebrow accent">INTEGRACIÓN</span><h1>Apache Guacamole</h1><p>Administra usuarios, conexiones y permisos directamente desde la plataforma CTF.</p></div><div className="page-actions"><button className="secondary-action" onClick={()=>void loadGuacamole()}>Actualizar</button><button className="primary-action" onClick={()=>{setGuacamoleConnectionEditing(null);setGuacamoleConnectionFormOpen(true)}}>+ Nueva conexión</button></div></div>
              <div className="stats-grid"><StatCard label="Estado" value={guacamoleMode === "stub" ? "STUB" : "REAL"} helper={guacamoleTested?"Conexión verificada":"Pendiente"} icon="settings" accent="purple"/><StatCard label="Servidor" value="192.168.146.132" helper="Puerto 8080 · Guacamole" icon="lab" accent="blue"/><StatCard label="Conexiones" value={guacamoleConnections.length} helper="Administradas desde CTF" icon="arrow" accent="green"/><StatCard label="Usuarios" value={guacamoleUsers.length} helper="Cuentas remotas" icon="users" accent="cyan"/></div>
              <section className="table-panel glass-panel" style={{marginTop:"13px"}}><div className="panel-head"><div><span className="eyebrow">CONEXIONES</span><h3>Conexiones remotas</h3><small>El backend administra la API de Guacamole; el navegador nunca recibe el token de servicio.</small></div></div><table><thead><tr><th>Nombre</th><th>Protocolo</th><th>Host</th><th>Puerto</th><th>Activas</th><th>Acciones</th></tr></thead><tbody>{guacamoleConnections.map(c=><tr key={c.identifier}><td><strong>{c.name}</strong></td><td>{c.protocol.toUpperCase()}</td><td>{c.hostname||"—"}</td><td>{c.port||"—"}</td><td>{c.active_connections}</td><td><div className="row-actions"><button className="table-action" onClick={()=>{setGuacamoleConnectionEditing(c);setGuacamoleConnectionFormOpen(true)}}>Editar</button><button className="table-action danger" onClick={()=>void deleteGuacamoleManagedConnection(c)} disabled={c.active_connections>0}>Eliminar</button></div></td></tr>)}</tbody></table>{guacamoleConnections.length===0&&<div className="empty-card"><strong>No hay conexiones administradas</strong><span>Crea la primera conexión para una VM del cyber range.</span></div>}</section>
              <section className="table-panel glass-panel guac-groups-panel" style={{marginTop:"13px"}}><div className="panel-head"><div><span className="eyebrow">GRUPOS SINCRONIZADOS</span><h3>Grupos académicos en Guacamole</h3><small>Cada grupo CTF se refleja como User Group de Guacamole para heredar permisos de acceso remoto.</small></div></div><div className="guac-group-grid">{groups.map(g=><div className="guac-group-card" key={g.id}><span className="group-list-icon"><Icon name="users" /></span><div><strong>{g.code}</strong><small>{g.name}</small></div><span className="sync-pill"><span className="status-dot" /> Sincronizado</span></div>)}{groups.length===0&&<div className="empty-card compact"><strong>Aún no hay grupos académicos</strong><span>Al crear un grupo desde CTF se creará su User Group en Guacamole.</span></div>}</div></section>
              <section className="table-panel glass-panel" style={{marginTop:"13px"}}><div className="panel-head"><div><span className="eyebrow">USUARIOS</span><h3>Administración de cuentas remotas</h3></div><button className="secondary-action" onClick={()=>{setGuacamoleUserEditing(null);setGuacamoleFormOpen(true)}}>+ Nuevo usuario</button></div><table><thead><tr><th>Usuario</th><th>Nombre</th><th>Correo</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{guacamoleUsers.map(remote=><tr key={remote.username}><td><strong>{remote.username}</strong></td><td>{remote.attributes?.["guac-full-name"]||"—"}</td><td>{remote.attributes?.["guac-email-address"]||"—"}</td><td><span className={remote.attributes?.disabled === "true" ? "status-draft":"status-published"}>{remote.attributes?.disabled === "true"?"Deshabilitado":"Activo"}</span></td><td><div className="row-actions"><button className="table-action" onClick={()=>{setGuacamoleUserEditing(remote);setGuacamoleFormOpen(true)}}>Editar</button><button className="table-action" onClick={()=>void openGuacamolePermissions(remote.username)}>Permisos</button><button className="table-action danger" disabled={remote.username===guacamoleStatus?.username} onClick={()=>void deleteGuacamoleManagedUser(remote)}>Eliminar</button></div></td></tr>)}</tbody></table></section>
              <div className="info-panel glass-panel" style={{marginTop:"13px"}}><span className="eyebrow">MODELO DE PERMISOS</span><p>Los permisos de sistema de Guacamole y los permisos por conexión se administran independientemente del rol CTF. <strong>ADMINISTER</strong> es el permiso de superusuario de Guacamole.</p></div>
            </section>
          )}

          {userFormOpen && isAdmin && (
            <UserForm
              initial={userEditing}
              onClose={() => {
                setUserFormOpen(false);
                setUserEditing(null);
              }}
              onSave={saveManagedUser}
            />
          )}

          {creating && (
            <ChallengeForm
              initial={editing}
              laboratories={laboratories}
              groups={groups}
              onClose={() => {
                setCreating(false);
                setEditing(null);
              }}
              onSave={saveChallenge}
            />
          )}

          {labFormOpen && (
            <LaboratoryForm
              initial={
                labEditing
              }
              onClose={() => {
                setLabFormOpen(
                  false
                );

                setLabEditing(
                  null
                );
              }}
              onSave={
                saveLaboratory
              }
            />
          )}

          {vmFormOpen &&
            selectedLab && (
              <VMForm
                laboratory={
                  selectedLab
                }
                initial={
                  vmEditing
                }
                onClose={() => {
                  setVmFormOpen(
                    false
                  );

                  setVmEditing(
                    null
                  );
                }}
                onSave={
                  saveVM
                }
                guacamoleConnections={guacamoleConnections}
              />
            )}

          {guacamoleFormOpen && isAdmin && (
            <GuacamoleUserForm
              initial={guacamoleUserEditing}
              onClose={() => { setGuacamoleFormOpen(false); setGuacamoleUserEditing(null); }}
              onSave={saveGuacamoleUser}
            />
          )}
          {guacamoleConnectionFormOpen && isAdmin && (
            <GuacamoleConnectionForm initial={guacamoleConnectionEditing} onClose={()=>{setGuacamoleConnectionFormOpen(false);setGuacamoleConnectionEditing(null)}} onSave={saveGuacamoleConnection} />
          )}
          {guacamolePermissionsOpen && guacamolePermissionsUser && isAdmin && (
            <GuacamolePermissionsForm username={guacamolePermissionsUser} initial={guacamolePermissions} connections={guacamoleConnections} onClose={()=>{setGuacamolePermissionsOpen(false);setGuacamolePermissionsUser(null)}} onSave={saveGuacamolePermissions} />
          )}
        </main>
      </div>
    </div>
  );
}
