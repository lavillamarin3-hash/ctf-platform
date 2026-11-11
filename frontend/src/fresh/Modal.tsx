import { ReactNode, useEffect, useId, useRef } from 'react';

/** Dialog nativo: foco contenido, fondo inerte y retorno al botón de apertura. */
export function Modal({title, children, onClose, busy = false, error = ''}: {
  title: string; children: ReactNode; onClose: () => void; busy?: boolean; error?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const element = dialog.current!;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    element.showModal();
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
      if (opener?.isConnected) opener.focus();
    };
  }, []);
  return <dialog ref={dialog} className="fresh-modal" aria-labelledby={titleId} aria-busy={busy}
    onCancel={event => {event.preventDefault(); if (!busy) onClose();}}>
    <header className="fresh-modal-head"><h2 id={titleId}>{title}</h2><button type="button" className="fresh-secondary" aria-label="Cerrar ventana" disabled={busy} onClick={onClose}>Cerrar</button></header>
    <div className="fresh-modal-body">{error && <p role="alert" className="fresh-error">{error}</p>}{children}</div>
  </dialog>;
}
