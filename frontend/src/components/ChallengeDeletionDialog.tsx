import { useEffect, useId, useRef, type RefObject } from "react";
import { createPortal } from "react-dom";
import type { ChallengeDeletionController } from "../controllers/useChallengeDeletion";
import { challengeDeletionCountLabels } from "../lib/challengeDeletion";

export function ChallengeDeletionDialog({
  controller,
  fallbackFocus,
}: {
  controller: ChallengeDeletionController;
  fallbackFocus: RefObject<HTMLHeadingElement>;
}) {
  const dialog = useRef<HTMLDivElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const close = useRef(controller.close);
  close.current = controller.close;
  const busy = useRef(controller.busy);
  busy.current = controller.busy;
  const titleId = useId();
  const descriptionId = useId();
  const inputId = useId();
  const targetCode = controller.target?.code;

  useEffect(() => {
    if (!targetCode) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    cancel.current?.focus();
    const focusable = () => Array.from(dialog.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), a[href], [tabindex="0"]',
    ) ?? []).filter((element) => element.getClientRects().length > 0);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        if (!busy.current) close.current();
      }
      if (event.key === "Tab") {
        const items = focusable();
        const first = items[0];
        const last = items[items.length - 1];
        if (!first) {
          event.preventDefault();
          dialog.current?.focus();
        } else if (event.shiftKey && (document.activeElement === first || !dialog.current?.contains(document.activeElement))) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || !dialog.current?.contains(document.activeElement))) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    const onFocusIn = (event: FocusEvent) => {
      if (event.target instanceof Node && !dialog.current?.contains(event.target)) {
        (focusable()[0] ?? dialog.current)?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("focusin", onFocusIn);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("focusin", onFocusIn);
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus();
      else fallbackFocus.current?.focus();
    };
  }, [targetCode, fallbackFocus]);

  if (!controller.target) return null;
  const { target, preview, loading, error } = controller;
  return createPortal(
    <div className="modal-backdrop challenge-delete-backdrop">
      <div ref={dialog} className="modal-card challenge-delete-modal" role="dialog" aria-modal="true"
        aria-labelledby={titleId} aria-describedby={descriptionId} aria-busy={controller.busy} tabIndex={-1}>
        <div className="modal-head">
          <div><span className="eyebrow">ELIMINACIÓN PERMANENTE</span><h2 id={titleId}>Eliminar {target.code}</h2></div>
          <button type="button" className="table-action" aria-label="Cerrar eliminación" disabled={controller.busy} onClick={controller.close}>Cerrar</button>
        </div>
        <p><strong>{target.name}</strong></p>
        <p id={descriptionId} className="challenge-delete-warning">
          Se borrará este reto de la plataforma y de la base de datos, incluidos sus resultados, respuestas,
          pistas consultadas, flags y asignaciones. Los puntos obtenidos en este reto se retirarán del ranking.
          Esta acción no se puede deshacer desde la plataforma.
        </p>
        <p>Para conservar el historial, cancela y utiliza «Desactivar».</p>
        {loading && <p role="status">Consultando los datos asociados…</p>}
        {error && <p role="alert" className="challenge-delete-error">{error}</p>}
        {preview && <>
          <h3>Datos que se eliminarán</h3>
          <dl className="challenge-delete-counts">
            {Object.entries(challengeDeletionCountLabels).filter(([key]) => key in preview.counts).map(([key, label]) => (
              <div key={key}><dt>{label}</dt><dd>{preview.counts[key].toLocaleString("es-EC")}</dd></div>
            ))}
          </dl>
          {preview.blockers.length > 0 && <div className="challenge-delete-blockers" role="status">
            <strong>La eliminación está bloqueada</strong>
            <ul>{preview.blockers.map((blocker, index) => <li key={`${blocker.type}-${index}`}>{blocker.message} ({blocker.count})</li>)}</ul>
            <p>Cierra las corridas y completa la limpieza de los recursos antes de volver a comprobar.</p>
          </div>}
        </>}
        <form onSubmit={(event) => { event.preventDefault(); void controller.remove(); }}>
          <label className="challenge-delete-confirm" htmlFor={inputId}>
            Escribe exactamente <strong>{target.code}</strong> para confirmar
            <input id={inputId} value={controller.confirmation} onChange={(event) => controller.setConfirmation(event.target.value)}
              autoComplete="off" autoCapitalize="off" spellCheck={false} disabled={controller.busy} />
          </label>
          <div className="modal-actions">
            <button ref={cancel} type="button" className="secondary-action" disabled={controller.busy} onClick={controller.close}>Cancelar</button>
            <button type="button" className="secondary-action" disabled={loading || controller.busy} onClick={() => void controller.refresh()}>Volver a comprobar</button>
            <button type="submit" className="challenge-delete-submit" disabled={!controller.canDelete}>
              {controller.busy ? "Eliminando…" : "Eliminar definitivamente"}
            </button>
          </div>
          {controller.busy && <p role="status">Eliminando los datos. Espera a que termine la operación.</p>}
        </form>
      </div>
    </div>, document.body,
  );
}
