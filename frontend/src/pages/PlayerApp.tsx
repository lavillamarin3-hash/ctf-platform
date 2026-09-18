// ============================================================
// PORTAL DEL JUGADOR
// Responsabilidad: composición del layout, navegación y vistas MVC.
// La lógica de estado vive en usePlayerController.
// ============================================================

import { createElement } from "react";
import { User } from "../api";
import { Theme, ThemePreference } from "../config";
import { PlayerSidebar, Header } from "../components/common";
import { usePlayerController } from "../controllers/usePlayerController";
import { PlayerRouter } from "../views/player/PlayerRouter";

export function PlayerApp({
  user,
  onLogout,
  theme,
  onToggleTheme,
  themePreference,
  onThemePreferenceChange,
  onUserChange,
}: {
  user: User;
  onLogout: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  themePreference: ThemePreference;
  onThemePreferenceChange: (value: ThemePreference) => void;
  onUserChange: (user: User) => void;
}) {
  const controller = usePlayerController();

  return (
    <div className="app-shell">
      <PlayerSidebar
        view={controller.view}
        setView={controller.setView}
        open={controller.menuOpen}
        onClose={() => controller.setMenuOpen(false)}
      />

      <div className="page-shell">
        <Header
          user={user}
          roleLabel="Jugador / Estudiante"
          onLogout={onLogout}
          onOpenMenu={() => controller.setMenuOpen(true)}
          theme={theme}
          onToggleTheme={onToggleTheme}
          themePreference={themePreference}
          onThemePreferenceChange={onThemePreferenceChange}
          onUserChange={onUserChange}
        />

        <main className="main-content">
          {controller.message && (
            <div className="global-message">
              <span>{controller.message}</span>
              <button onClick={() => controller.setMessage(null)}>×</button>
            </div>
          )}

          <PlayerRouter controller={controller} user={user} />
        </main>
      </div>
    </div>
  );
}
