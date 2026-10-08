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
      <div className="login-grid" />

      <section className="login-card">

        {/* ── Panel izquierdo: identidad y bienvenida ── */}
        <div 
          className="login-visual"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "2rem",
            position: "relative"
          }}
        >
          {/* Elementos visuales decorativos de fondo (burbujas y cuadrados fragmentados) */}
          <div style={{ position: "absolute", top: "25%", left: "10%", width: "45px", height: "45px", border: "2px solid rgba(123, 108, 246, 0.2)", borderRadius: "8px", transform: "rotate(20deg)", pointerEvents: "none", zIndex: 1 }} />
          <div style={{ position: "absolute", bottom: "35%", right: "15%", width: "80px", height: "80px", border: "1.5px solid rgba(107, 127, 247, 0.15)", borderRadius: "16px", transform: "rotate(-15deg)", pointerEvents: "none", zIndex: 1 }} />
          <div style={{ position: "absolute", top: "60%", left: "5%", width: "30px", height: "30px", border: "2px solid rgba(123, 108, 246, 0.1)", borderRadius: "6px", transform: "rotate(45deg)", pointerEvents: "none", zIndex: 1 }} />
          <div style={{ position: "absolute", bottom: "20%", left: "20%", width: "120px", height: "120px", background: "radial-gradient(circle, rgba(123, 108, 246, 0.05) 0%, transparent 70%)", borderRadius: "50%", pointerEvents: "none", zIndex: 1 }} />

          {/* Logo en semicírculo en la parte superior */}
          <div style={{
            position: "absolute",
            top: 0,
            left: "50%",
            transform: "translateX(-50%)",
            background: theme === "dark" ? "rgba(123, 108, 246, 0.08)" : "rgba(123, 108, 246, 0.06)",
            width: "300px",
            height: "150px",
            borderBottomLeftRadius: "150px",
            borderBottomRightRadius: "150px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            paddingTop: "1rem", 
            zIndex: 10
          }}>
            <img
              src={theme === "dark" ? Logo : Logo}
              alt="COMCIBER CTF"
              style={{
                maxWidth: "200px",
                width: "80%",
                height: "auto",
                filter: theme === "dark" ? "drop-shadow(0 4px 12px rgba(0,0,0,0.3))" : "none"
              }}
            />
          </div>

          <div 
            className="login-visual-content"
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              flexGrow: 1,
              textAlign: "center",
              zIndex: 10,
              width: "100%",
              paddingTop: "80px"
            }}
          >
            <h1 style={{ fontSize: "clamp(28px, 3.5vw, 42px)", margin: "0 0 1rem 0", lineHeight: 1.2, fontWeight: "800", color: theme === "dark" ? "#e9f1fb" : "#14213a" }}>
              Bienvenido a <br/>
              <span className="accent-text" style={{ color: "#7b6cf6" }}>la plataforma CTF</span>
            </h1>
          </div>
          
          <div style={{
            position: "absolute",
            bottom: "3rem",
            left: "0",
            width: "100%",
            textAlign: "center",
            zIndex: 10,
            padding: "0 2rem"
          }}>
            <p style={{ fontSize: "clamp(15px, 1.5vw, 17px)", margin: "0 auto", color: theme === "dark" ? "#93a3bb" : "#637286", lineHeight: 1.6, maxWidth: "480px" }}>
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
          style={{ position: "relative", overflow: "hidden" }}
        >
          {/* Botón de cambio de tema movido dentro de esta sección */}
          <div className="login-theme">
            <ThemeToggle
              theme={theme}
              onToggle={onToggleTheme}
            />
          </div>

          {/* Elementos visuales decorativos - Derecha (Fondo) */}
          <div style={{ position: "absolute", top: "-5%", right: "-10%", width: "180px", height: "180px", background: "radial-gradient(circle, rgba(123, 108, 246, 0.04) 0%, transparent 70%)", borderRadius: "50%", pointerEvents: "none", zIndex: 0 }} />
          <div style={{ position: "absolute", bottom: "10%", left: "-15%", width: "250px", height: "250px", background: "radial-gradient(circle, rgba(107, 127, 247, 0.03) 0%, transparent 70%)", borderRadius: "50%", pointerEvents: "none", zIndex: 0 }} />
          <div style={{ position: "absolute", top: "25%", right: "8%", width: "35px", height: "35px", border: "1.5px solid rgba(123, 108, 246, 0.12)", borderRadius: "8px", transform: "rotate(30deg)", pointerEvents: "none", zIndex: 0 }} />
          <div style={{ position: "absolute", bottom: "35%", right: "12%", width: "20px", height: "20px", border: "2px solid rgba(107, 127, 247, 0.1)", borderRadius: "4px", transform: "rotate(-20deg)", pointerEvents: "none", zIndex: 0 }} />

          <div className="login-form-head" style={{ position: "relative", zIndex: 1 }}>
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
