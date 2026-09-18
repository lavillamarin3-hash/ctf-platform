// ============================================================
// PANEL DE ADMINISTRACIÓN / INSTRUCTOR
// Responsabilidad: composición del layout y las capas MVC.
// ============================================================

import { createElement } from "react";
import { User } from "../api";
import { Theme, ThemePreference } from "../config";
import { ManagementSidebar, Header } from "../components/common";
import { GuestApp } from "./GuestApp";
import { useManagementController } from "../controllers/useManagementController";
import { ManagementRouter } from "../views/management/ManagementRouter";
import { ManagementModals } from "../views/management/ManagementModals";

export function ManagementApp({
  user, onLogout, theme, onToggleTheme, themePreference, onThemePreferenceChange, onUserChange, panelRole,
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
  const controller = useManagementController({ user, panelRole });

  if (user.role === "guest") {
    return <GuestApp user={user} onLogout={onLogout} theme={theme} onToggleTheme={onToggleTheme} themePreference={themePreference} onThemePreferenceChange={onThemePreferenceChange} onUserChange={onUserChange} />;
  }

  return (
    <div className="app-shell">
      <ManagementSidebar view={controller.view} setView={controller.setView} open={controller.menuOpen} onClose={() => controller.setMenuOpen(false)} role={user.role} />
      <div className="page-shell">
        <Header user={user} roleLabel={controller.roleLabel} onLogout={onLogout} onOpenMenu={() => controller.setMenuOpen(true)} theme={theme} onToggleTheme={onToggleTheme} themePreference={themePreference} onThemePreferenceChange={onThemePreferenceChange} onUserChange={onUserChange} />
        <main className="main-content">
          {controller.message && <div className="global-message"><span>{controller.message}</span><button onClick={() => controller.setMessage(null)}>×</button></div>}
          <ManagementRouter controller={controller} />
          <ManagementModals controller={controller} />
        </main>
      </div>
    </div>
  );
}
