// ============================================================
// LAYOUT Y NAVEGACIÓN
// Responsabilidad: cabecera, sidebars y navegación por rol.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, User, Challenge, RankingRow } from "../../api";
import { Theme, ThemePreference, PlayerView, ManagementView, ManagedUser, USER_FUNCTIONS, DEMO_USERS, difficultyStyle, categoryMeta, DEFAULT_LABORATORIES, demoLabCount, VM_OS_OPTIONS, NETWORK_IPS, Laboratory, LabVM } from "../../config";

import { Icon, Logo, ThemeToggle, AccessibilityControls, CtfAlert, PreferencesModal, AccountSettingsModal } from "./ui";

export function Header({
  user,
  roleLabel,
  onLogout,
  onOpenMenu,
  theme,
  onToggleTheme,
  themePreference,
  onThemePreferenceChange,
  onUserChange,
}: {
  user: User;
  roleLabel: string;
  onLogout: () => void;
  onOpenMenu: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  themePreference: ThemePreference;
  onThemePreferenceChange: (value: ThemePreference) => void;
  onUserChange: (user: User) => void;
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => localStorage.getItem(`ctf-notifications-${user.id}`) !== "false");
  const [notice, setNotice] = useState<{title:string;message:string;type:"success"|"warning"|"error"|"info"}|null>(null);

  const notify = (title: string, message: string, type: "success"|"warning"|"error"|"info" = "info") => {
    setNotice({ title, message, type });
    window.setTimeout(() => setNotice(null), 3600);
  };

  const toggleNotifications = (enabled: boolean) => {
    setNotificationsEnabled(enabled);
    localStorage.setItem(`ctf-notifications-${user.id}`, String(enabled));
    if (enabled) notify("Notificaciones activadas", "Recibirás los avisos operativos de la plataforma.", "success");
  };

  const avatar = localStorage.getItem(`ctf-avatar-${user.id}`) || "";

  return (
    <>
      <header className="topbar">
        <div className="topbar-left">
          <button className="icon-btn mobile-only" onClick={onOpenMenu} aria-label="Abrir menú">☰</button>
          <div className="topbar-title"><span>PLATAFORMA CTF</span><strong>Laboratorio de Ciberseguridad</strong></div>
        </div>
        <div className="topbar-actions">
          {notificationsEnabled && <button className="icon-btn notification" aria-label="Notificaciones" onClick={() => notify("Notificaciones", "No hay alertas nuevas pendientes.", "info")}><Icon name="bell" /><span>3</span></button>}
          <div className="profile-menu-wrap">
            <button className="profile-chip" onClick={() => setProfileOpen((v) => !v)} aria-expanded={profileOpen} title="Abrir menú de usuario">
              <div className="avatar">{avatar ? <img src={avatar} alt="" /> : user.username.slice(0, 2).toUpperCase()}</div>
              <div className="profile-text"><strong>{user.username}</strong><small>{roleLabel}</small></div><span className="profile-arrow">⌄</span>
            </button>
            {profileOpen && (
              <div className="profile-dropdown" role="menu">
                <div className="profile-dropdown-head"><div className="avatar large">{avatar ? <img src={avatar} alt="" /> : user.username.slice(0,2).toUpperCase()}</div><div><strong>{user.username}</strong><small>{roleLabel}</small></div></div>
                <button type="button" onClick={() => { setPreferencesOpen(true); setProfileOpen(false); }}><Icon name="settings" /><span>Preferencias</span></button>
                <button type="button" onClick={() => { setAccountOpen(true); setProfileOpen(false); }}><Icon name="user" /><span>Configuración de cuenta</span></button>
                <button type="button" onClick={() => { toggleNotifications(!notificationsEnabled); setProfileOpen(false); }}><Icon name="bell" /><span>{notificationsEnabled ? "Ocultar notificaciones" : "Mostrar notificaciones"}</span></button>
                <div className="profile-dropdown-divider" />
                <button type="button" className="danger-menu" onClick={onLogout}><Icon name="logout" /><span>Cerrar sesión</span></button>
              </div>
            )}
          </div>
        </div>
      </header>
      {notice && notificationsEnabled && <div className="floating-alert"><CtfAlert type={notice.type} title={notice.title} message={notice.message} /></div>}
      {preferencesOpen && <PreferencesModal preference={themePreference} onPreferenceChange={onThemePreferenceChange} onClose={() => setPreferencesOpen(false)} notificationsEnabled={notificationsEnabled} onNotificationsChange={toggleNotifications} />}
      {accountOpen && <AccountSettingsModal user={user} onClose={() => setAccountOpen(false)} onUserChange={onUserChange} onNotify={notify} />}
    </>
  );
}

export function PlayerSidebar({
  view,
  setView,
  open,
  onClose,
}: {
  view: PlayerView;
  setView: (view: PlayerView) => void;
  open: boolean;
  onClose: () => void;
}) {
  const item = (
    key: PlayerView,
    icon: string,
    label: string
  ) => (
    <button
      className={`nav-item ${
        view === key ? "active" : ""
      }`}
      onClick={() => {
        setView(key);
        onClose();
      }}
    >
      <Icon name={icon} />
      <span>{label}</span>
    </button>
  );

  return (
    <aside
      className={`sidebar ${
        open ? "open" : ""
      }`}
    >
      <div className="sidebar-brand">
        <Logo />

        <button
          className="icon-btn mobile-only"
          onClick={onClose}
        >
          ×
        </button>
      </div>

      <nav>
        <div className="nav-group-label">
          PRINCIPAL
        </div>

        {item(
          "dashboard",
          "home",
          "Dashboard"
        )}

        <div className="nav-group-label">
          CTF
        </div>

        {item(
          "categories",
          "grid",
          "Categorías"
        )}

        {item(
          "challenges",
          "flag",
          "Retos"
        )}

        {item(
          "progress",
          "chart",
          "Mi progreso"
        )}

        {item(
          "ranking",
          "trophy",
          "Ranking"
        )}

        <div className="nav-group-label">
          LABORATORIO
        </div>

        {item(
          "laboratory",
          "lab",
          "Mis conexiones"
        )}
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />
        Sistema operativo
      </div>
    </aside>
  );
}

export function ManagementSidebar({
  view,
  setView,
  open,
  onClose,
  role,
}: {
  view: ManagementView;
  setView: (view: ManagementView) => void;
  open: boolean;
  onClose: () => void;
  role: User["role"];
}) {
  /**
   * Construye una opción del menú.
   * Mantener esta función pequeña facilita agregar o quitar módulos
   * sin duplicar el comportamiento de navegación.
   */
  const item = (
    key: ManagementView,
    icon: string,
    label: string
  ) => (
    <button
      type="button"
      className={`nav-item ${view === key ? "active" : ""}`}
      onClick={() => {
        setView(key);
        onClose();
      }}
    >
      <Icon name={icon} />
      <span>{label}</span>
    </button>
  );

  const isAdmin = role === "admin";
  const canManage = role === "admin" || role === "instructor";

  return (
    <aside
      className={`sidebar ${open ? "open" : ""}`}
      aria-label="Navegación de administración"
    >
      <div className="sidebar-brand">
        <Logo />
        <button
          type="button"
          className="icon-btn mobile-only"
          onClick={onClose}
          aria-label="Cerrar menú"
        >
          ×
        </button>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-group-label">GESTIÓN</div>

        {item("dashboard", "home", "Dashboard")}
        {item("challenges", "flag", "Retos")}
        {item("laboratory", "lab", "Laboratorios / VMs")}
        {item("ranking", "trophy", "Ranking")}

        {canManage && (
          <>
            <div className="nav-group-label">ORGANIZACIÓN</div>

            {item(
              "groups",
              "users",
              "Grupos de estudiantes"
            )}

            {item(
              "monitoring",
              "chart",
              isAdmin ? "Seguimiento" : "Seguimiento"
            )}
          </>
        )}

        {canManage && (
          <>
            <div className="nav-group-label">
              {isAdmin ? "ADMINISTRACIÓN" : "SUPERVISIÓN"}
            </div>

            {item(
              "users",
              "users",
              isAdmin ? "Gestionar usuarios" : "Usuarios"
            )}

            {isAdmin && (
              item(
                "guacamole",
                "settings",
                "Guacamole"
              )
            )}
          </>
        )}
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />
        {isAdmin ? "Administrador" : "Instructor"}
      </div>
    </aside>
  );
}

export function GuestSidebar({
  view,
  setView,
  open,
  onClose,
}: {
  view: ManagementView;
  setView: (view: ManagementView) => void;
  open: boolean;
  onClose: () => void;
}) {
  const item = (
    key: ManagementView,
    icon: string,
    label: string
  ) => (
    <button
      className={`nav-item ${
        view === key ? "active" : ""
      }`}
      onClick={() => {
        setView(key);
        onClose();
      }}
    >
      <Icon name={icon} />
      <span>{label}</span>
    </button>
  );

  return (
    <aside
      className={`sidebar ${
        open ? "open" : ""
      }`}
    >
      <div className="sidebar-brand">
        <Logo />

        <button
          className="icon-btn mobile-only"
          onClick={onClose}
        >
          ×
        </button>
      </div>

      <nav>
        <div className="nav-group-label">
          CONSULTA
        </div>

        {item(
          "dashboard",
          "home",
          "Inicio"
        )}

        {item(
          "challenges",
          "flag",
          "Retos"
        )}

        {item(
          "ranking",
          "trophy",
          "Ranking"
        )}
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />
        Modo invitado · Solo lectura
      </div>
    </aside>
  );
}

