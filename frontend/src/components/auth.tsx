// ============================================================
// AUTENTICACIÓN
// Responsabilidad: pantalla de acceso y validación del inicio de sesión.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api, session, User } from "../api";
import { Theme } from "../config";
import { ThemeToggle, ErrorMessage, Icon } from "./common";
import Logo from "../assets/images/Logo.png";
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

      <section className="login-card">

        {/* ── Panel izquierdo: identidad y bienvenida ── */}
        <div className="login-visual">

          {/* Elementos decorativos de fondo (cuadrados fragmentados) */}
          <div className="login-deco deco-sq-1" />
          <div className="login-deco deco-sq-2" />
          <div className="login-deco deco-sq-3" />
          <div className="login-deco deco-sq-4" />
          <div className="login-deco deco-blob-1" />
          <div className="login-deco deco-blob-2" />

          {/* TOP — Mensaje de bienvenida */}
          <div className="login-visual-top">
            <h2 className="login-welcome-title">
              Bienvenido a la plataforma CTF
            </h2>
          </div>

          {/* CENTER — Logo grande */}
          <div className="login-visual-center">
            <img
              src={Logo}
              src={Logo}
              alt="COMCIBER CTF"
              className="login-logo-main"
            />
          </div>

          {/* BOTTOM — Subtítulo motivador */}
          <div className="login-visual-bottom">
            <p className="login-tagline">
              Pon a prueba tus habilidades.<br />
              Explora, aprende y supera nuevos retos.
            </p>
          </div>

        </div>

        {/* ── Panel derecho: formulario ── */}
        <div className="login-form-panel">

          {/* Botón de tema — independiente del form, no dispara submit */}
          <div className="login-theme">
            <ThemeToggle
              theme={theme}
              onToggle={onToggleTheme}
            />
          </div>

          {/* Elementos visuales decorativos - Derecha */}
          <div className="login-form-deco deco-right-1" />
          <div className="login-form-deco deco-right-2" />

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
              type="submit"
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
        </div>

      </section>
    </main>
  );
}
