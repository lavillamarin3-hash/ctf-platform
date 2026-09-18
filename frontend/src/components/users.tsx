// ============================================================
// GESTIÓN DE USUARIOS
// Responsabilidad: formularios de cuentas CTF; no decide navegación.
// ============================================================

import { createElement, FormEvent, useState } from "react";

import { User } from "../api";
import { ManagedUser, UserFunction, USER_FUNCTIONS } from "../config";

export function UserForm({
  initial,
  onClose,
  onSave,
}: {
  initial: ManagedUser | null;
  onClose: () => void;
  onSave: (user: ManagedUser, password: string) => Promise<void>;
}) {
  const [username, setUsername] = useState(
    initial?.username ?? ""
  );

  const [fullName, setFullName] = useState(
    initial?.full_name ?? ""
  );

  const [email, setEmail] = useState(
    initial?.email ?? ""
  );

  const [role, setRole] = useState<User["role"]>(
    initial?.role ?? "player"
  );

  const [userFunction, setUserFunction] =
    useState<UserFunction>(
      initial?.user_function ?? "Estudiante"
    );

  const [organization, setOrganization] = useState(
    initial?.organization ?? ""
  );

  const [active, setActive] = useState(
    initial?.is_active ?? true
  );

  const [password, setPassword] = useState("");

  const [busy, setBusy] = useState(false);

  const [error, setError] = useState<string | null>(
    null
  );

  const protectedStaff = Boolean(
    initial &&
      (initial.role === "admin" ||
        initial.role === "instructor")
  );

  const submit = async (
    event: FormEvent
  ) => {
    event.preventDefault();

    setError(null);

    const cleanUsername = username.trim();
    const cleanFullName = fullName.trim();
    const cleanEmail = email.trim();
    const cleanOrganization =
      organization.trim() || "Sin organización";

    if (!cleanUsername) {
      setError("Debes ingresar un nombre de usuario.");
      return;
    }

    if (!cleanFullName) {
      setError("Debes ingresar el nombre completo.");
      return;
    }

    if (!initial && password.length < 8) {
      setError(
        "La contraseña debe tener al menos 8 caracteres."
      );
      return;
    }

    setBusy(true);

    try {
      await onSave(
        {
          id: initial?.id ?? 0,
          username: cleanUsername,
          full_name: cleanFullName,
          email: cleanEmail || null,
          role,
          user_function: userFunction,
          organization: cleanOrganization,
          is_active: active,
          demo: initial?.demo,
        },
        password
      );

      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No se pudo guardar el usuario."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <form
        className="modal-card user-form-card"
        onSubmit={submit}
      >
        <div className="modal-head">
          <div>
            <span className="eyebrow accent">
              ADMINISTRACIÓN
            </span>

            <h2>
              {initial
                ? "Editar usuario"
                : "Crear nuevo usuario"}
            </h2>

            <small>
              {initial
                ? "Actualiza los datos y permisos de la cuenta."
                : "Registra un nuevo usuario en la plataforma CTF."}
            </small>
          </div>

          <button
            type="button"
            className="icon-btn"
            onClick={onClose}
            aria-label="Cerrar"
            disabled={busy}
          >
            ×
          </button>
        </div>

        <div className="form-grid">
          <label>
            Usuario

            <input
              value={username}
              onChange={(e) =>
                setUsername(e.target.value)
              }
              placeholder="usuario.ctf"
              disabled={Boolean(initial) || busy}
              required
            />

            {!initial && (
              <small className="field-help">
                Será el identificador utilizado para
                iniciar sesión.
              </small>
            )}
          </label>

          <label>
            Nombre completo

            <input
              value={fullName}
              onChange={(e) =>
                setFullName(e.target.value)
              }
              placeholder="Nombre y apellido"
              disabled={busy}
              required
            />
          </label>

          <label>
            Correo electrónico

            <input
              type="email"
              value={email ?? ""}
              onChange={(e) =>
                setEmail(e.target.value)
              }
              placeholder="usuario@dominio.local"
              disabled={busy}
            />
          </label>

          {!initial && (
            <label>
              Contraseña

              <input
                type="password"
                value={password}
                onChange={(e) =>
                  setPassword(e.target.value)
                }
                placeholder="Mínimo 8 caracteres"
                minLength={8}
                autoComplete="new-password"
                disabled={busy}
                required
              />

              <small className="field-help">
                Mínimo 8 caracteres.
              </small>
            </label>
          )}

          <label>
            Rol de plataforma

            <select
              value={role}
              disabled={
                protectedStaff || busy
              }
              onChange={(e) =>
                setRole(
                  e.target.value as User["role"]
                )
              }
            >
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

            <small className="field-help">
              Define el nivel de acceso dentro de
              la plataforma.
            </small>
          </label>

          <label>
            Función operativa

            <select
              value={userFunction}
              disabled={
                protectedStaff || busy
              }
              onChange={(e) =>
                setUserFunction(
                  e.target.value as UserFunction
                )
              }
            >
              {USER_FUNCTIONS.map(
                (item) => (
                  <option
                    key={item}
                    value={item}
                  >
                    {item}
                  </option>
                )
              )}
            </select>
          </label>

          <label>
            Organización

            <input
              value={organization}
              onChange={(e) =>
                setOrganization(
                  e.target.value
                )
              }
              placeholder="Universidad / institución"
              disabled={busy}
            />
          </label>
        </div>

        <div className="form-section-divider" />

        <label className="switch-row user-active-toggle">
          <input
            type="checkbox"
            checked={active}
            disabled={busy}
            onChange={(e) =>
              setActive(e.target.checked)
            }
          />

          <span>
            <strong>Cuenta activa</strong>
            <small>
              El usuario podrá acceder a la
              plataforma cuando esté habilitado.
            </small>
          </span>
        </label>

        {protectedStaff && (
          <div className="notice notice-info">
            <span>i</span>
            <span>
              Las cuentas de Administrador e
              Instructor están protegidas.
            </span>
          </div>
        )}

        {error && (
          <div className="notice notice-error user-form-error">
            <span>!</span>
            <span>{error}</span>
          </div>
        )}

        <div className="modal-actions">
          <button
            type="button"
            className="secondary-action"
            onClick={onClose}
            disabled={busy}
          >
            Cancelar
          </button>

          <button
            type="submit"
            className="primary-action"
            disabled={busy}
          >
            {busy
              ? "Guardando…"
              : initial
                ? "Guardar usuario"
                : "Crear usuario"}
          </button>
        </div>
      </form>
    </div>
  );
}