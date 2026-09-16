// ============================================================
// AUTENTICACIÓN
// Responsabilidad: pantalla de acceso y validación del inicio de sesión.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api, session, User } from "../api";
import { Theme } from "../config";
import { Logo, ThemeToggle, ErrorMessage, Icon } from "./common";

export function Login({
  onLogin,
  theme,
  onToggleTheme,
}: {
  onLogin: (user: User) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  const [username, setUsername] =
    useState("usuario");

  const [password, setPassword] =
    useState("");

  const [error, setError] =
    useState<string | null>(null);

  const [loading, setLoading] =
    useState(false);

  const submit = async (
    event: FormEvent
  ) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data =
        await api.login(
          username.trim(),
          password
        );

      session.save(
        data.access_token
      );

      onLogin(data.user);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible iniciar sesión"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-shell">
      <div className="login-grid" />

      <div className="login-theme">
        <ThemeToggle
          theme={theme}
          onToggle={onToggleTheme}
        />
      </div>

      <section className="login-card">
        <div className="login-visual">
          <Logo />

          <div className="login-visual-content">
            <span className="eyebrow">
              LABORATORIO INTERNO
            </span>

            <h1>
              Entrena.
              <br />
              <em>Analiza.</em>
              <br />
              Supera.
            </h1>

            <p>
              Plataforma CTF conectada al
              laboratorio MITRE ATT&amp;CK.
              Resuelve escenarios controlados y
              desarrolla tus habilidades de
              ciberseguridad.
            </p>

            <div className="login-pill-row">
              <span>MITRE ATT&amp;CK</span>
              <span>GUACAMOLE</span>
              <span>SECURITY ONION</span>
            </div>
          </div>

          <div className="login-glow glow-one" />
          <div className="login-glow glow-two" />
        </div>

        <form
          className="login-form"
          onSubmit={submit}
        >
          <div className="login-form-head">
            <span className="eyebrow accent">
              BIENVENIDO
            </span>

            <h2>
              Inicia tu sesión
            </h2>

            <p>
              Utiliza las credenciales asignadas
              para acceder a tu área de trabajo.
            </p>
          </div>

          <ErrorMessage
            message={error}
          />

          <label
            className="input-label"
            htmlFor="username"
          >
            Usuario

            <input
              className="dark-field"
              id="username"
              value={username}
              onChange={(e) =>
                setUsername(
                  e.target.value
                )
              }
              autoComplete="username"
              required
            />
          </label>

          <label
            className="input-label"
            htmlFor="password"
          >
            Contraseña

            <div className="password-field">
              <Icon name="lock" />

              <input
                className="dark-field bare"
                id="password"
                type="password"
                value={password}
                onChange={(e) =>
                  setPassword(
                    e.target.value
                  )
                }
                autoComplete="current-password"
                required
              />
            </div>
          </label>

          <div className="login-helper">
            <span>
              <span className="status-dot" />
              Laboratorio operativo
            </span>

            <span>
              Acceso autenticado por roles
            </span>
          </div>

          <button
            className="primary-action full"
            disabled={loading}
          >
            {loading
              ? "Validando…"
              : "Entrar a la plataforma"}

            <Icon name="arrow" />
          </button>

          <p className="login-note">
            Cada usuario verá únicamente las
            funciones correspondientes a su rol.
          </p>
        </form>
      </section>
    </main>
  );
}
