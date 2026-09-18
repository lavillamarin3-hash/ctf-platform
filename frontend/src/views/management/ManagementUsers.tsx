// ============================================================
// VISTA: ManagementUsers
// Responsabilidad: presentación de una sección del panel.
// ============================================================

import { createElement } from "react";
import type { User } from "../../api";
import type { ManagementController } from "../../controllers/useManagementController";

export function ManagementUsers({ controller }: { controller: ManagementController }) {
  // Estado y datos que esta vista presenta.
  const {
    user, isAdmin, users, visibleUsers, userSearch,
    userRoleFilter, published, draft,
  } = controller;

  // Acciones proporcionadas por el controlador.
  const {
    load, setUserSearch, setUserRoleFilter, setUserEditing,
    setUserFormOpen, setGuacamoleUserEditing, setGuacamoleFormOpen, deleteManagedUser,
    changeUser,
  } = controller;
  return (
<section>
      <div className="page-heading">
        <div>
          <span className="eyebrow accent">
            {isAdmin
              ? "ADMINISTRACIÓN"
              : "SUPERVISIÓN"}
          </span>

          <h1>
            Usuarios y roles
          </h1>

          <p>
            {isAdmin
              ? "Gestiona cuentas, roles, funciones y estado de acceso."
              : "Consulta las cuentas registradas, sus roles y funciones."}
          </p>
        </div>

        <div className="page-actions">
          <button
            className="secondary-action"
            onClick={() =>
              void load()
            }
          >
            Actualizar
          </button>

          {isAdmin && (
            <>
              <button
                className="secondary-action"
                onClick={() => {
                  setGuacamoleUserEditing(null);
                  setGuacamoleFormOpen(true);
                }}
                title="Crear una cuenta directamente en Apache Guacamole"
              >
                + Usuario Guacamole
              </button>

              <button
                className="primary-action"
                onClick={() => {
                  setUserEditing(null);
                  setUserFormOpen(true);
                }}
              >
                + Nuevo usuario
              </button>
            </>
          )}
        </div>
      </div>

      <div className="user-toolbar glass-panel">
        <input
          className="user-search"
          value={userSearch}
          onChange={(e) =>
            setUserSearch(
              e.target.value
            )
          }
          placeholder="Buscar por usuario, nombre, correo o función..."
          aria-label="Buscar usuarios"
        />

        <select
          className="table-select user-role-filter"
          value={userRoleFilter}
          onChange={(e) =>
            setUserRoleFilter(
              e.target.value as
                | "Todas"
                | User["role"]
            )
          }
          aria-label="Filtrar usuarios por rol"
        >
          <option value="Todas">
            Todos los roles
          </option>
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

        <span className="user-count">
          {visibleUsers.length} resultado{visibleUsers.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="role-summary">
        {(
          [
            ["admin", "Administradores"],
            ["instructor", "Instructores"],
            ["player", "Jugadores"],
            ["guest", "Invitados"],
          ] as const
        )
          .filter(([roleKey]) => user.role === "admin" || roleKey !== "admin")
          .map(
          ([roleKey, label]) => {
            const total =
              users.filter(
                (item) =>
                  item.role ===
                  roleKey
              ).length;

            return (
              <button
                type="button"
                key={roleKey}
                className={`role-summary-card ${
                  userRoleFilter ===
                  roleKey
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  setUserRoleFilter(
                    userRoleFilter ===
                      roleKey
                      ? "Todas"
                      : roleKey
                  )
                }
              >
                <strong>
                  {total}
                </strong>

                <span>
                  {label}
                </span>
              </button>
            );
          }
        )}
      </div>

      <div className="table-panel glass-panel">
        <table>
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Nombre</th>
              <th>Correo</th>
              <th>Rol</th>
              <th>Función</th>
              <th>Organización</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>

          <tbody>
            {visibleUsers.map(
              (u) => (
                <tr key={u.id}>
                  <td>
                    <strong>
                      {u.username}
                    </strong>

                    {u.demo && (
                      <span className="self-label">
                        DEMO
                      </span>
                    )}
                  </td>

                  <td>
                    {u.full_name}
                  </td>

                  <td>
                    {u.email ||
                      "—"}
                  </td>

                  <td>
                    {isAdmin ? (
                      (u.role === "admin" || u.role === "instructor") ? (
                        <span className="category-tag role-protected" title="Cuenta protegida">
                          {u.role === "admin" ? "Administrador" : "Instructor"} · Protegido
                        </span>
                      ) : (
                        <select
                          className="table-select"
                          value={u.role}
                          title="Asignar rol de plataforma"
                          onChange={(e) =>
                            void changeUser(
                              u.id,
                              {
                                role:
                                  e.target
                                    .value as User["role"],
                              }
                            )
                          }
                        >
                          <option value="player">
                            Jugador
                          </option>
                          <option value="guest">
                            Invitado
                          </option>
                          <option value="instructor">
                            Instructor
                          </option>
                        </select>
                      )
                    ) : (
                      <span className="category-tag">
                        {u.role ===
                        "admin"
                          ? "Administrador"
                          : u.role ===
                              "instructor"
                            ? "Instructor"
                            : u.role ===
                                "player"
                              ? "Jugador"
                              : "Invitado"}
                      </span>
                    )}
                  </td>

                  <td>
                    <span className="category-tag">
                      {u.user_function}
                    </span>
                  </td>

                  <td>
                    {u.organization}
                  </td>

                  <td>
                    <span
                      className={
                        u.is_active
                          ? "status-published"
                          : "status-draft"
                      }
                    >
                      {u.is_active
                        ? "Activo"
                        : "Deshabilitado"}
                    </span>
                  </td>

                  <td>
                    {isAdmin ? (
                      <div className="row-actions">
                        <button
                          className="table-action"
                          onClick={() => {
                            setUserEditing(
                              u
                            );
                            setUserFormOpen(
                              true
                            );
                          }}
                        >
                          Editar
                        </button>

                        <button
                          className={`table-action ${
                            u.is_active
                              ? "danger"
                              : "success"
                          }`}
                          onClick={() =>
                            void changeUser(
                              u.id,
                              {
                                is_active:
                                  !u.is_active,
                              }
                            )
                          }
                          disabled={
                            u.id ===
                            user.id
                          }
                        >
                          {u.is_active
                            ? "Deshabilitar"
                            : "Habilitar"}
                        </button>

                        <button
                          className="table-action danger"
                          onClick={() =>
                            deleteManagedUser(
                              u
                            )
                          }
                          disabled={
                            u.id ===
                            user.id
                          }
                        >
                          Eliminar
                        </button>
                      </div>
                    ) : (
                      <span className="self-label">
                        Solo lectura
                      </span>
                    )}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>

        {visibleUsers.length ===
          0 && (
          <div className="empty-card">
            <strong>
              No hay usuarios que coincidan
            </strong>
            <span>
              Cambia el filtro o realiza otra búsqueda.
            </span>
          </div>
        )}
      </div>

      <div className="info-panel glass-panel user-permission-note">
        <span className="eyebrow">
          PERMISOS
        </span>

        <p>
          {isAdmin
            ? "Administrador: puede crear, editar, habilitar, deshabilitar y eliminar usuarios."
            : "Instructor: puede consultar los usuarios, roles y funciones, pero no puede modificarlos."}
        </p>
      </div>
    </section>

  );
}
