// ============================================================
// UI BASICA Y PREFERENCIAS
// ============================================================

import { createElement, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, User, Challenge, RankingRow } from "../../api";
import { Theme, ThemePreference, PlayerView, ManagementView, ManagedUser, USER_FUNCTIONS, DEMO_USERS, difficultyStyle, categoryMeta, DEFAULT_LABORATORIES, demoLabCount, VM_OS_OPTIONS, NETWORK_IPS, Laboratory, LabVM } from "../../config";

export function ErrorMessage({
  message,
  kind = "error",
}: {
  message: string | null;
  kind?: "error" | "success";
}) {
  if (!message) return null;

  return (
    <div
      className={`notice ${
        kind === "success"
          ? "notice-success"
          : "notice-error"
      }`}
      role="alert"
    >
      <span>{kind === "success" ? "✓" : "!"}</span>
      <span>{message}</span>
    </div>
  );
}

export function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    home: "M3 11 12 3l9 8v9a1 1 0 0 1-1 1h-5v-7H10v7H5a1 1 0 0 1-1-1v-9Z",
    grid: "M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z",
    flag: "M6 21V4m0 1c4-3 7 3 12 0v9c-5 3-8-3-12 0",
    chart: "M4 19V9m5 10V5m5 14v-7m5 7V3",
    trophy:
      "M8 21h8M12 17v4M6 4h12v6a6 6 0 0 1-12 0V4Zm0 2H3v2a4 4 0 0 0 3 4m12-6h3v2a4 4 0 0 1-3 4",
    lab: "M10 3h4m-6 4h8M9 3v5l-4 8a3 3 0 0 0 2.7 4h8.6A3 3 0 0 0 19 16l-4-8V3",
    play: "M8 5v14l11-7L8 5Z",
    user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9a7 7 0 0 1 14 0",
    users:
      "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m7-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7-5a3 3 0 1 1 0 6m3 7v-2a4 4 0 0 0-3-3.87",
    bell:
      "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4",
    lock:
      "M7 10V7a5 5 0 0 1 10 0v3m-12 0h14v10H5V10Z",
    arrow: "M5 12h14m-6-6 6 6-6 6",
    sun:
      "M12 3v2m0 14v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M3 12h2m14 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
    moon:
      "M20.8 15.5A8.5 8.5 0 0 1 8.5 3.2 8.6 8.6 0 1 0 20.8 15.5Z",
    logout:
      "M10 17l5-5-5-5m5 5H3m8-9h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7",
    check: "m5 12 4 4L19 6",
    clock:
      "M12 8v4l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    settings:
      "M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Zm0-12v2m0 13v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M3 12h2m14 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41",
  };

  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="icon"
    >
      <path
        d={paths[name] ?? paths.grid}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Logo() {
  return (
    <div className="brand">
      <div className="brand-mark">
        <span>ϟ</span>
      </div>

      <div>
        <strong>CYBER LAB</strong>
        <small>PLATFORM CTF</small>
      </div>
    </div>
  );
}

export function ThemeToggle({
  theme,
  onToggle,
}: {
  theme: Theme;
  onToggle: () => void;
}) {
  return (
    <button
      className="icon-btn theme-toggle"
      onClick={onToggle}
      aria-label={
        theme === "dark"
          ? "Activar modo claro"
          : "Activar modo oscuro"
      }
      title={
        theme === "dark"
          ? "Modo claro"
          : "Modo oscuro"
      }
    >
      <Icon
        name={
          theme === "dark"
            ? "sun"
            : "moon"
        }
      />
    </button>
  );
}

export function AccessibilityControls() {
  const [fontScale, setFontScale] =
    useState(() => {
      const saved = Number(
        localStorage.getItem(
          "ctf-font-scale"
        )
      );

      return [
        0.9,
        1,
        1.15,
        1.3,
        1.45,
      ].includes(saved)
        ? saved
        : 1;
    });

  useEffect(() => {
    document.documentElement.style.fontSize =
      `${fontScale * 16}px`;

    localStorage.setItem(
      "ctf-font-scale",
      String(fontScale)
    );
  }, [fontScale]);

  const decrease = () => {
    setFontScale((current) => {
      if (current <= 0.9) return 0.9;
      if (current <= 1) return 0.9;
      if (current <= 1.15) return 1;
      if (current <= 1.3) return 1.15;
      return 1.3;
    });
  };

  const normal = () => {
    setFontScale(1);
  };

  const increase = () => {
    setFontScale((current) => {
      if (current >= 1.45) return 1.45;
      if (current < 1) return 1;
      if (current < 1.15) return 1.15;
      if (current < 1.3) return 1.3;
      return 1.45;
    });
  };

  return (
    <div
      className="accessibility-controls"
      aria-label="Controles de tamaño del texto"
    >
      <span className="accessibility-label">
        Tamaño del texto
      </span>

      <button
        type="button"
        className="icon-btn accessibility-btn"
        onClick={decrease}
        aria-label="Reducir tamaño del texto"
      >
        A−
      </button>

      <button
        type="button"
        className="icon-btn accessibility-btn"
        onClick={normal}
        aria-label="Tamaño normal del texto"
      >
        A
      </button>

      <button
        type="button"
        className="icon-btn accessibility-btn"
        onClick={increase}
        aria-label="Aumentar tamaño del texto"
      >
        A+
      </button>
    </div>
  );
}

declare global {
  interface HTMLElementTagNameMap {
    "ctf-alert": HTMLElement;
  }
}

if (typeof window !== "undefined" && !customElements.get("ctf-alert")) {
  class CtfAlertElement extends HTMLElement {
    static get observedAttributes() { return ["type", "title", "message"]; }

    connectedCallback() { this.render(); }
    attributeChangedCallback() { this.render(); }

    render() {
      const escape = (value: string) => value.replace(/[&<>\"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[char] || char));
      const type = this.getAttribute("type") || "info";
      const title = escape(this.getAttribute("title") || "Notificación");
      const message = escape(this.getAttribute("message") || "");
      const icon = type === "success" ? "✓" : type === "error" ? "!" : type === "warning" ? "⚠" : "i";
      this.innerHTML = `
        <style>
          :host{display:block;font:600 12px/1.5 system-ui,sans-serif}
          .alert{display:flex;gap:10px;align-items:flex-start;padding:12px 14px;border:1px solid #233651;border-radius:12px;background:rgba(8,17,29,.94);color:#dbe7f5;box-shadow:0 16px 30px rgba(0,0,0,.18)}
          .icon{width:24px;height:24px;border-radius:8px;display:grid;place-items:center;background:rgba(109,77,230,.16);color:#9a8cff;font-weight:900;flex:none}
          .title{font-weight:900}.message{margin-top:2px;color:#8fa1b7;font-weight:500}
          :host([type="success"]) .icon{color:#62d98a;background:rgba(63,170,95,.12)}
          :host([type="error"]) .icon{color:#ff7b88;background:rgba(211,65,82,.12)}
          :host([type="warning"]) .icon{color:#f2be63;background:rgba(185,125,29,.12)}
        </style>
        <div class="alert"><div class="icon">${icon}</div><div><div class="title">${title}</div><div class="message">${message}</div></div></div>`;
    }
  }
  customElements.define("ctf-alert", CtfAlertElement);
}

export function CtfAlert({ type = "info", title, message }: { type?: "success" | "info" | "warning" | "error"; title: string; message: string }) {
  return createElement("ctf-alert" as any, { type, title, message });
}

export function applyFontScale(scale: number) {
  document.documentElement.style.fontSize = `${scale * 16}px`;
  localStorage.setItem("ctf-font-scale", String(scale));
}

export function PreferencesModal({
  preference,
  onPreferenceChange,
  onClose,
  notificationsEnabled,
  onNotificationsChange,
}: {
  preference: ThemePreference;
  onPreferenceChange: (value: ThemePreference) => void;
  onClose: () => void;
  notificationsEnabled: boolean;
  onNotificationsChange: (value: boolean) => void;
}) {
  const [scale, setScale] = useState(() => {
    const saved = Number(localStorage.getItem("ctf-font-scale"));
    return [0.9, 1, 1.15, 1.3, 1.45].includes(saved) ? saved : 1;
  });

  useEffect(() => { applyFontScale(scale); }, [scale]);

  return (
    <div className="modal-backdrop">
      <div className="modal-card preferences-modal">
        <div className="modal-head">
          <div><span className="eyebrow accent">PREFERENCIAS</span><h2>Configuración general</h2><small>Personaliza la experiencia sin modificar tus permisos.</small></div>
          <button type="button" className="icon-btn" onClick={onClose}>×</button>
        </div>
        <div className="preference-section">
          <span className="preference-label">Tema del sistema</span>
          <div className="segmented-control">
            {(["system", "light", "dark"] as ThemePreference[]).map((item) => (
              <button key={item} type="button" className={preference === item ? "active" : ""} onClick={() => onPreferenceChange(item)}>
                {item === "system" ? "Sistema" : item === "light" ? "Claro" : "Oscuro"}
              </button>
            ))}
          </div>
        </div>
        <div className="preference-section">
          <span className="preference-label">Tamaño de fuente</span>
          <div className="font-stepper">
            <button type="button" className="secondary-action" onClick={() => setScale((v) => Math.max(.9, [0.9,1,1.15,1.3,1.45][Math.max(0,[0.9,1,1.15,1.3,1.45].indexOf(v)-1)]))}>A−</button>
            <strong>{Math.round(scale * 100)}%</strong>
            <button type="button" className="secondary-action" onClick={() => setScale((v) => Math.min(1.45, [0.9,1,1.15,1.3,1.45][Math.min(4,[0.9,1,1.15,1.3,1.45].indexOf(v)+1)]))}>A+</button>
          </div>
        </div>
        <div className="preference-section switch-preference">
          <div><span className="preference-label">Notificaciones</span><small>Mostrar avisos y alertas operativas de la plataforma.</small></div>
          <label className="toggle-switch"><input type="checkbox" checked={notificationsEnabled} onChange={(e) => onNotificationsChange(e.target.checked)} /><span /></label>
        </div>
        <div className="modal-actions"><button type="button" className="primary-action" onClick={onClose}>Guardar preferencias</button></div>
      </div>
    </div>
  );
}

export function AccountSettingsModal({
  user,
  onClose,
  onUserChange,
  onNotify,
}: {
  user: User;
  onClose: () => void;
  onUserChange: (user: User) => void;
  onNotify: (title: string, message: string, type?: "success" | "warning" | "error" | "info") => void;
}) {
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [avatar, setAvatar] = useState(() => localStorage.getItem(`ctf-avatar-${user.id}`) || "");
  const [busy, setBusy] = useState(false);

  const handleAvatar = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith("image/") || file.size > 2_000_000) {
      onNotify("Foto no válida", "Usa una imagen de máximo 2 MB.", "warning");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setAvatar(String(reader.result || ""));
    reader.readAsDataURL(file);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (newPassword && newPassword !== confirmPassword) {
      onNotify("Contraseña", "Las contraseñas nuevas no coinciden.", "warning");
      return;
    }
    if (newPassword && newPassword.length < 8) {
      onNotify("Contraseña", "La nueva contraseña debe tener al menos 8 caracteres.", "warning");
      return;
    }
    setBusy(true);
    try {
      let updated = user;
      if (username.trim() !== user.username || email.trim() !== (user.email || "")) {
        updated = await api.updateProfile({ username: username.trim(), email: email.trim() || null });
        onUserChange(updated);
      }
      if (newPassword) {
        if (!currentPassword) throw new Error("Debes indicar la contraseña actual.");
        await api.changePassword({ current_password: currentPassword, new_password: newPassword });
      }
      if (avatar) localStorage.setItem(`ctf-avatar-${user.id}`, avatar);
      else localStorage.removeItem(`ctf-avatar-${user.id}`);
      onNotify("Cuenta actualizada", "Los cambios de tu cuenta se guardaron correctamente.", "success");
      onClose();
    } catch (err) {
      onNotify("No se pudo guardar", err instanceof Error ? err.message : "No se pudo actualizar la cuenta.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <form className="modal-card account-modal" onSubmit={submit}>
        <div className="modal-head">
          <div><span className="eyebrow accent">CUENTA</span><h2>Configuración de cuenta</h2><small>Actualiza tus datos personales y credenciales.</small></div>
          <button type="button" className="icon-btn" onClick={onClose}>×</button>
        </div>
        <div className="account-avatar-row">
          <div className="account-avatar-preview">{avatar ? <img src={avatar} alt="Foto de perfil" /> : user.username.slice(0,2).toUpperCase()}</div>
          <div><strong>Foto de perfil</strong><small>JPG, PNG o WebP · máximo 2 MB</small><div className="row-actions"><label className="secondary-action file-button">Cambiar foto<input type="file" accept="image/*" hidden onChange={(e) => handleAvatar(e.target.files?.[0])} /></label><button type="button" className="table-action danger" onClick={() => setAvatar("")}>Eliminar</button></div></div>
        </div>
        <div className="form-grid">
          <label>Nombre de usuario<input value={username} onChange={(e) => setUsername(e.target.value)} minLength={3} required /></label>
          <label>Correo<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>Contraseña actual<input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} autoComplete="current-password" /></label>
          <label>Nueva contraseña<input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} minLength={8} autoComplete="new-password" /></label>
          <label>Confirmar contraseña<input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} minLength={8} autoComplete="new-password" /></label>
        </div>
        <div className="modal-actions"><button type="button" className="secondary-action" onClick={onClose}>Cancelar</button><button className="primary-action" disabled={busy}>{busy ? "Guardando…" : "Guardar cambios"}</button></div>
      </form>
    </div>
  );
}

