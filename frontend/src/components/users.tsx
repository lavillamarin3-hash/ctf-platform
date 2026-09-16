// ============================================================
// GESTIÓN DE USUARIOS
// Responsabilidad: formularios de cuentas CTF; no decide navegación.
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { User } from "../api";
import { ManagedUser, UserFunction, USER_FUNCTIONS } from "../config";
import { Icon } from "./common";

export function UserForm({
  initial,
  onClose,
  onSave,
}: {
  initial: ManagedUser | null;
  onClose: () => void;
  onSave: (user: ManagedUser, password: string) => void;
}) {
  const [username, setUsername] =
    useState(initial?.username ?? "");

  const [fullName, setFullName] =
    useState(initial?.full_name ?? "");

  const [email, setEmail] =
    useState(initial?.email ?? "");

  const [role, setRole] =
    useState<User["role"]>(
      initial?.role ?? "player"
    );

  const [userFunction, setUserFunction] =
    useState<UserFunction>(
      initial?.user_function ?? "Estudiante"
    );

  const [organization, setOrganization] =
    useState(
      initial?.organization ?? ""
    );

  const [active, setActive] =
    useState(
      initial?.is_active ?? true
    );

  const [password, setPassword] =
    useState("");

  const protectedStaff = Boolean(
    initial &&
      (initial.role === "admin" || initial.role === "instructor")
  );

  const submit = (
    event: FormEvent
  ) => {
    event.preventDefault();

    if (
      !username.trim() ||
      !fullName.trim()
    ) {
      return;
    }

    if (!initial && password.length < 8) {
      return;
    }

    onSave({
      id: initial?.id ?? 0,
      username:
        username.trim(),
      full_name:
        fullName.trim(),
      email:
        email.trim() ||
        null,
      role,
      user_function:
        userFunction,
      organization:
        organization.trim() ||
        "Sin organización",
      is_active: active,
      demo: initial?.demo,
    }, password);

    onClose();
  };

  return (
    <div className="modal-backdrop">
      <form
        className="modal-card"
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
                : "Nuevo usuario"}
            </h2>

            <small>
              {initial
                ? "Actualiza los datos y permisos de la cuenta."
                : "Crea un registro para verificar la gestión de usuarios."}
            </small>
          </div>

          <button
            type="button"
            className="icon-btn"
            onClick={onClose}
            aria-label="Cerrar"
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
                setUsername(
                  e.target.value
                )
              }
              placeholder="usuario.ctf"
              required
            />
          </label>

          <label>
            Nombre completo

            <input
              value={fullName}
              onChange={(e) =>
                setFullName(
                  e.target.value
                )
              }
              placeholder="Nombre y apellido"
              required
            />
          </label>

          <label>
            Correo

            <input
              type="email"
              value={
                email ?? ""
              }
              onChange={(e) =>
                setEmail(
                  e.target.value
                )
              }
              placeholder="usuario@dominio.local"
            />
          </label>

          {!initial && (
            <label>
              Contraseña

              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                minLength={8}
                required
              />
            </label>
          )}

          <div className="remote-access-notice">
            <span className="remote-access-icon"><Icon name="settings" /></span>
            <span><strong>Acceso remoto sincronizado</strong><small>Al guardar un estudiante, la cuenta CTF se crea también en Apache Guacamole automáticamente.</small></span>
          </div>

          <label>
            Rol de plataforma

            <select
              value={role}
              disabled={protectedStaff}
              onChange={(e) =>
                setRole(
                  e.target
                    .value as User["role"]
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
            <small className="field-help">Administrador e Instructor son cuentas protegidas y no se degradan desde este formulario.</small>
          </label>

          <label>
            Función operativa

            <select
              value={
                userFunction
              }
              disabled={protectedStaff}
              onChange={(e) =>
                setUserFunction(
                  e.target
                    .value as UserFunction
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
              value={
                organization
              }
              onChange={(e) =>
                setOrganization(
                  e.target.value
                )
              }
              placeholder="Cyber Lab"
            />
          </label>
        </div>

        <label className="switch-row">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) =>
              setActive(
                e.target.checked
              )
            }
          />

          Cuenta activa
        </label>

        <div className="modal-actions">
          <button
            type="button"
            className="secondary-action"
            onClick={onClose}
          >
            Cancelar
          </button>

          <button className="primary-action">
            {initial
              ? "Guardar usuario"
              : "Crear usuario"}
          </button>
        </div>
      </form>
    </div>
  );
}
