import { useState } from "react";
import type { InputHTMLAttributes } from "react";

/** A single accessible, reusable password input with an inset visibility control. */
type PasswordFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label?: string;
};

export function PasswordField({ label = "contraseña", className = "", ...props }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  const title = visible ? `Ocultar ${label}` : `Mostrar ${label}`;
  return (
    <span className="ctf-password-control">
      <input {...props} type={visible ? "text" : "password"} className={className} />
      <button type="button" className="ctf-password-toggle" aria-label={title}
        title={title} aria-pressed={visible} disabled={props.disabled}
        onClick={() => setVisible((old) => !old)}>
        {visible ? (
          <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true" fill="none"
            stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 4l16 16M10.6 10.7a2 2 0 002.7 2.7" />
            <path d="M9.9 5.3A10.5 10.5 0 0112 5c4.7 0 8.4 3.1 10 7a12 12 0 01-3.4 4.3M6.3 6.3A12 12 0 002 12c1.6 3.9 5.3 7 10 7a10 10 0 005.7-1.7" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true" fill="none"
            stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </span>
  );
}
