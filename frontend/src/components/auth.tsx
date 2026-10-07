// ============================================================
// AUTENTICACIÓN
// Responsabilidad: pantalla de acceso y validación del inicio de sesión.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api, session, User } from "../api";
import { Theme } from "../config";
import { ThemeToggle, ErrorMessage, Icon } from "./common";
import LogoDark from "../assets/images/LogoDark.jpg";
import LogoWhite from "../assets/images/LogoWhite.jpg";

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

        {/* ── Panel izquierdo: identidad y bienvenida ── */}
        <div 
          className="login-visual"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "2rem"
          }}
        >
          <div 
            className="login-visual-content"
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
              marginTop: 0,
              zIndex: 10,
              width: "100%"
            }}
          >
            <img
              src={theme === "dark" ? LogoDark : LogoWhite}
              alt="COMCIBER CTF"
              style={{
                maxWidth: "240px",
                width: "80%",
                height: "auto",
                marginBottom: "1.5rem"
              }}
            />
            <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", margin: "0 0 1rem 0", lineHeight: 1.2 }}>
              Bienvenido a la plataforma CTF
            </h1>
            <p style={{ fontSize: "clamp(14px, 1.5vw, 16px)", margin: 0, padding: "0 1rem" }}>
              Pon a prueba tus habilidades. Explora, aprende y supera nuevos retos.
            </p>
          </div>
          <div className="login-cover-overlay" />
          <div className="login-glow glow-one" />
          <div className="login-glow glow-two" />
        </div>

        {/* ── Panel derecho: formulario ── */}
        <form
          className="login-form"
          onSubmit={submit}
        >
          <div className="login-form-head">
            <span className="eyebrow accent">
              COMCIBER CTF
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
