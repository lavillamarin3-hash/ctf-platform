// ============================================================
// APLICACIÓN PRINCIPAL
// Responsabilidad única: autenticación de sesión y enrutamiento por rol.
// La lógica específica de cada perfil vive en sus respectivos módulos.
// ============================================================

import { useEffect, useState } from "react";
import { api, session, User } from "./api";
import { Theme, ThemePreference } from "./config";
import { Login } from "./components/auth";
import { AdminApp } from "./pages/AdminApp";
import { InstructorApp } from "./pages/InstructorApp";
import { PlayerApp } from "./pages/PlayerApp";
import { GuestApp } from "./pages/GuestApp";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(Boolean(session.get()));
  const [themePreference, setThemePreference] = useState<ThemePreference>(() => {
    const saved = localStorage.getItem("ctf-theme-preference");
    return saved === "system" || saved === "light" || saved === "dark" ? saved : "dark";
  });
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem("ctf-theme");
    return saved === "light" ? "light" : "dark";
  });

  // Resuelve la preferencia de tema y sincroniza la preferencia del sistema.
  useEffect(() => {
    const apply = () => {
      const resolved = themePreference === "system"
        ? (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark")
        : themePreference;
      setTheme(resolved);
      document.documentElement.dataset.theme = resolved;
      document.documentElement.style.colorScheme = resolved;
      localStorage.setItem("ctf-theme", resolved);
      localStorage.setItem("ctf-theme-preference", themePreference);
    };
    apply();
    const media = window.matchMedia("(prefers-color-scheme: light)");
    media.addEventListener?.("change", apply);
    return () => media.removeEventListener?.("change", apply);
  }, [themePreference]);

  const toggleTheme = () => setThemePreference((current) => current === "dark" ? "light" : "dark");

  const handleUserChange = (updated: User) => setUser(updated);

  // Recuperamos la sesión JWT existente antes de decidir qué panel renderizar.
  useEffect(() => {
    if (!session.get()) {
      setChecking(false);
      return;
    }
    api.me()
      .then(setUser)
      .catch(() => {
        session.clear();
        setUser(null);
      })
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <main className="loading-screen">
        <div className="loader-ring" />
        <span>Recuperando sesión…</span>
      </main>
    );
  }

  if (!user) {
    return <Login onLogin={setUser} theme={theme} onToggleTheme={toggleTheme} />;
  }

  const handleLogout = () => {
    session.clear();
    setUser(null);
  };

  switch (user.role) {
    case "player":
      return <PlayerApp user={user} onLogout={handleLogout} theme={theme} onToggleTheme={toggleTheme} themePreference={themePreference} onThemePreferenceChange={setThemePreference} onUserChange={handleUserChange} />;
    case "guest":
      return <GuestApp user={user} onLogout={handleLogout} theme={theme} onToggleTheme={toggleTheme} themePreference={themePreference} onThemePreferenceChange={setThemePreference} onUserChange={handleUserChange} />;
    case "instructor":
      return <InstructorApp user={user} onLogout={handleLogout} theme={theme} onToggleTheme={toggleTheme} themePreference={themePreference} onThemePreferenceChange={setThemePreference} onUserChange={handleUserChange} />;
    case "admin":
    default:
      return <AdminApp user={user} onLogout={handleLogout} theme={theme} onToggleTheme={toggleTheme} themePreference={themePreference} onThemePreferenceChange={setThemePreference} onUserChange={handleUserChange} />;
  }
}
