import { useEffect, useRef, useState } from 'react';
import { api } from './client';

export function Terminal({ runId }: { runId: string }) {
  const root = useRef<HTMLDivElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState('');
  useEffect(() => {
    let disposed = false;
    let disconnect = () => {};
    async function open() {
      try {
        setError('');
        if (!window.Guacamole) await new Promise<void>((resolve, reject) => {
          const script = document.createElement('script'); script.src = '/api/v1/terminal/client.js';
          script.onload = () => resolve(); script.onerror = () => { script.remove(); reject(new Error('No se pudo cargar la consola.')); };
          document.head.appendChild(script);
        });
        const ticket = await api<{path: string}>(`/runs/${runId}/terminal`, {});
        if (disposed || !root.current || !window.Guacamole) return;
        const G = window.Guacamole;
        const tunnel = new G.WebSocketTunnel(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${ticket.path}`);
        const client = new G.Client(tunnel);
        root.current.replaceChildren(client.getDisplay().getElement());
        root.current.tabIndex = 0;
        const keyboard = new G.Keyboard(root.current);
        keyboard.onkeydown = key => { client.sendKeyEvent(1, key); return false; };
        keyboard.onkeyup = key => client.sendKeyEvent(0, key);
        const mouse = new G.Mouse(client.getDisplay().getElement());
        mouse.onmousedown = mouse.onmouseup = mouse.onmousemove = state => client.sendMouseState(state, true);
        client.onerror = () => setError('La consola se desconectó. Puedes reintentar si la corrida sigue activa.');
        client.connect('');
        disconnect = () => { keyboard.reset(); client.disconnect(); };
      } catch (e) { if (!disposed) setError((e as Error).message); }
    }
    void open();
    return () => { disposed = true; disconnect(); };
  }, [runId, attempt]);
  return <section><div className="fresh-terminal" ref={root} aria-label="Consola SSH de la Kali asignada" />{error && <p role="alert">{error} <button onClick={() => setAttempt(v => v + 1)}>Reconectar</button></p>}</section>;
}
