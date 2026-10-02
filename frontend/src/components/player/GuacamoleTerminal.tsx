import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, request } from "../../services/api/client";

type Stream = { sendAck: (message: string, code: number) => void };
type Client = {
  getDisplay: () => { getElement: () => HTMLElement; scale: (n: number) => void };
  connect: (data: string) => void; disconnect: () => void;
  sendSize: (width: number, height: number) => void;
  sendKeyEvent: (pressed: number, keysym: number) => void;
  sendMouseState: (state: unknown, applyScale: boolean) => void;
  createClipboardStream: (mimetype: string) => unknown;
  onstatechange: ((state: number) => void) | null;
  onerror: ((status: unknown) => void) | null;
  onclipboard: ((stream: Stream, mimetype: string) => void) | null;
};
type Keyboard = { onkeydown: (keysym: number) => boolean; onkeyup: (keysym: number) => void; reset: () => void };
type Namespace = {
  WebSocketTunnel: new (url: string) => unknown;
  Client: new (tunnel: unknown) => Client;
  Keyboard: new (element: HTMLElement) => Keyboard;
  Mouse: new (element: HTMLElement) => { onmousedown: (state: unknown) => void; onmouseup: (state: unknown) => void; onmousemove: (state: unknown) => void };
  StringReader: new (stream: Stream) => { ontext: (text: string) => void; onend: () => void };
  StringWriter: new (stream: unknown) => { sendText: (text: string) => void; sendEnd: () => void };
};
declare global { interface Window { Guacamole?: Namespace } }

// Se utiliza el cliente oficial de la instalación, servido bajo el origen CTF.
// Nunca recibe tokens personales/técnicos ni identificadores remotos.
let libraryPromise: Promise<Namespace> | null = null;
function loadClient(): Promise<Namespace> {
  if (window.Guacamole) return Promise.resolve(window.Guacamole);
  if (!libraryPromise) {
    libraryPromise = new Promise<Namespace>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/api/v1/terminal/client.js";
      script.onload = () => window.Guacamole ? resolve(window.Guacamole) : reject(new Error("Cliente no disponible"));
      script.onerror = () => { script.remove(); reject(new Error("Cliente no disponible")); };
      document.head.appendChild(script);
    }).catch((error: unknown) => { libraryPromise = null; throw error; });
  }
  return libraryPromise;
}
type State = "loading" | "connected" | "auth" | "error" | "disconnected";
type Protocol = "ssh" | "rdp";
const ZOOM_STEPS = [0.75, 1, 1.25, 1.5, 1.75, 2];

// La caja externa permanece estable aunque Guacamole agregue/quiete scrollbars.
function terminalDimensions(panel: HTMLElement, scale: number) {
  const bounds = panel.getBoundingClientRect();
  return {
    width: Math.max(320, Math.floor(bounds.width / scale)),
    height: Math.max(240, Math.floor(bounds.height / scale)),
  };
}

export function GuacamoleTerminal({ runId, preferredProtocol, onClipboard }: {
  runId: number;
  preferredProtocol?: string | null;
  onClipboard: (text: string) => void;
}) {
  const terminalRef = useRef<HTMLElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const clientRef = useRef<Client | null>(null);
  const keyboardRef = useRef<Keyboard | null>(null);
  const clipboardCallback = useRef(onClipboard);
  clipboardCallback.current = onClipboard;
  const [state, setState] = useState<State>("loading");
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [password, setPassword] = useState("");
  const [authenticating, setAuthenticating] = useState(false);
  const [zoom, setZoom] = useState(1.25);
  const [fullscreen, setFullscreen] = useState(false);
  const [protocols, setProtocols] = useState<Protocol[] | null>(null);
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [optionsError, setOptionsError] = useState("");
  const [optionsAttempt, setOptionsAttempt] = useState(0);
  const zoomRef = useRef(zoom);
  const scheduleSizeRef = useRef<(() => void) | null>(null);
  const changeZoom = (direction: -1 | 1) => setZoom((current) => ZOOM_STEPS[Math.max(0, Math.min(ZOOM_STEPS.length - 1, ZOOM_STEPS.indexOf(current) + direction))]);

  useEffect(() => {
    let disposed = false;
    setProtocols(null); setProtocol(null); setOptionsError(""); setState("loading");
    void request<{ protocols: string[] }>(`/runs/${runId}/terminal/options`)
      .then((result) => {
        if (disposed) return;
        const available = result.protocols.filter((value): value is Protocol => value === "ssh" || value === "rdp");
        if (!available.length) throw new Error("No hay conexiones remotas configuradas para esta instancia.");
        setProtocols(available);
        setProtocol(available.includes(preferredProtocol as Protocol) ? preferredProtocol as Protocol : available[0]);
      })
      .catch((error: unknown) => {
        if (!disposed) setOptionsError(error instanceof ApiError ? error.message : error instanceof Error ? error.message : "No se pudieron comprobar las conexiones disponibles.");
      });
    return () => { disposed = true; };
  }, [runId, preferredProtocol, optionsAttempt]);

  useEffect(() => {
    const updateFullscreen = () => setFullscreen(document.fullscreenElement === terminalRef.current);
    document.addEventListener("fullscreenchange", updateFullscreen);
    return () => document.removeEventListener("fullscreenchange", updateFullscreen);
  }, []);
  const toggleFullscreen = async () => {
    try {
      if (document.fullscreenElement === terminalRef.current) await document.exitFullscreen();
      else await terminalRef.current?.requestFullscreen();
    } catch {
      setMessage("El navegador no permitió abrir esta conexión a pantalla completa.");
    }
  };
  const switchProtocol = (next: Protocol) => {
    if (next === protocol || !protocols?.includes(next) || state === "loading") return;
    setState("loading"); setMessage(""); setProtocol(next);
  };

  useEffect(() => {
    if (!protocol) return;
    let disposed = false;
    let observer: ResizeObserver | null = null;
    let client: Client | null = null;
    let keyboard: Keyboard | null = null;
    let resizeTimer = 0;
    let resizeFrame = 0;
    setState("loading"); setMessage("");
    const connect = async () => {
      try {
        const ticket = await request<{ websocket_path: string }>(`/runs/${runId}/terminal/session`, {
          method: "POST", body: JSON.stringify({ protocol }),
        });
        const Guacamole = await loadClient();
        if (disposed || !viewport.current) return;
        if (ticket.websocket_path !== `/api/v1/runs/${runId}/terminal/ws`) throw new Error("Destino no válido");
        const wsScheme = location.protocol === "https:" ? "wss:" : "ws:";
        const tunnel = new Guacamole.WebSocketTunnel(`${wsScheme}//${location.host}${ticket.websocket_path}`);
        const current = new Guacamole.Client(tunnel);
        client = current; clientRef.current = current;
        const display = current.getDisplay();
        const element = display.getElement();
        viewport.current.replaceChildren(element); display.scale(zoomRef.current);
        current.onstatechange = (value) => {
          if (disposed) return;
          if (value === 3) setState("connected");
          else if (value === 5) setState((previous) => previous === "error" ? previous : "disconnected");
        };
        current.onerror = () => {
          if (!disposed) { setState("error"); setMessage("No se pudo mantener el túnel. Revisa tu conexión o reconecta tu cuenta de laboratorio."); }
        };
        current.onclipboard = (stream, mimetype) => {
          if (mimetype !== "text/plain") { stream.sendAck("Solo texto", 0x030F); return; }
          const reader = new Guacamole.StringReader(stream);
          let text = "";
          reader.ontext = (chunk) => {
            if (text.length + chunk.length > 262144) { stream.sendAck("Texto demasiado largo", 0x030D); return; }
            text += chunk; stream.sendAck("OK", 0);
          };
          reader.onend = () => { if (!disposed) clipboardCallback.current(text); };
        };
        keyboard = new Guacamole.Keyboard(viewport.current); keyboardRef.current = keyboard;
        keyboard.onkeydown = (keysym) => { current.sendKeyEvent(1, keysym); return false; };
        keyboard.onkeyup = (keysym) => current.sendKeyEvent(0, keysym);
        const mouse = new Guacamole.Mouse(element);
        mouse.onmousedown = mouse.onmouseup = mouse.onmousemove = (value) => current.sendMouseState(value, true);
        const initialSize = terminalDimensions(viewport.current, zoomRef.current);
        let lastSize = initialSize;
        const sendSizeIfChanged = () => {
          const panel = viewport.current;
          if (!panel || clientRef.current !== current) return;
          const next = terminalDimensions(panel, zoomRef.current);
          if (Math.abs(next.width - lastSize.width) < 3 && Math.abs(next.height - lastSize.height) < 3) return;
          lastSize = next;
          current.sendSize(next.width, next.height);
        };
        const scheduleSize = () => {
          window.clearTimeout(resizeTimer);
          resizeTimer = window.setTimeout(() => {
            resizeFrame = window.requestAnimationFrame(sendSizeIfChanged);
          }, 120);
        };
        scheduleSizeRef.current = scheduleSize;
        observer = new ResizeObserver(scheduleSize);
        observer.observe(viewport.current, { box: "border-box" });
        current.connect(`width=${initialSize.width}&height=${initialSize.height}`);
      } catch (error) {
        if (disposed) return;
        setState(error instanceof ApiError && error.status === 428 ? "auth" : "error");
        setMessage(error instanceof ApiError ? error.message : "No se pudo cargar la terminal. Verifica la disponibilidad de Guacamole.");
      }
    };
    void connect();
    return () => {
      disposed = true; observer?.disconnect(); keyboard?.reset();
      window.clearTimeout(resizeTimer); window.cancelAnimationFrame(resizeFrame);
      scheduleSizeRef.current = null;
      if (client) { client.onstatechange = null; client.onerror = null; client.onclipboard = null; client.disconnect(); }
      viewport.current?.replaceChildren();
      if (clientRef.current === client) clientRef.current = null;
      if (keyboardRef.current === keyboard) keyboardRef.current = null;
    };
  }, [runId, attempt, protocol]);
  useEffect(() => {
    zoomRef.current = zoom;
    const client = clientRef.current; const panel = viewport.current;
    if (client && panel) {
      client.getDisplay().scale(zoom);
      scheduleSizeRef.current?.();
    }
  }, [zoom]);

  const authenticate = async (event: FormEvent) => {
    event.preventDefault(); setAuthenticating(true);
    try { await request("/terminal/auth", { method: "POST", body: JSON.stringify({ password }) }); setAttempt((value) => value + 1); }
    catch (error) { setMessage(error instanceof Error ? error.message : "No se pudo conectar tu cuenta"); }
    finally { setPassword(""); setAuthenticating(false); }
  };
  const labels: Record<State, string> = { loading: "Conectando…", connected: "Conectada", auth: "Conecta tu cuenta", error: "Error de conexión", disconnected: "Desconectada" };
  return <section className="embedded-terminal-panel" ref={terminalRef} aria-label="Conexión remota del laboratorio">
    <div className="embedded-terminal-toolbar">
      <div><span className="eyebrow">CONEXIÓN INTEGRADA</span><strong>{protocol === "rdp" ? "Escritorio RDP" : "Terminal SSH"}</strong></div>
      <span className={`terminal-state ${state}`} role="status">{labels[state]}</span>
      <div className="terminal-zoom-controls">
        <button type="button" aria-label={protocol === "rdp" ? "Reducir vista RDP" : "Reducir texto de terminal"} disabled={zoom <= ZOOM_STEPS[0]} onClick={() => changeZoom(-1)}>A−</button>
        <span aria-live="polite">{Math.round(zoom * 100)}%</span>
        <button type="button" aria-label={protocol === "rdp" ? "Ampliar vista RDP" : "Ampliar texto de terminal"} disabled={zoom >= ZOOM_STEPS[ZOOM_STEPS.length - 1]} onClick={() => changeZoom(1)}>A+</button>
      </div>
      <button type="button" className="secondary-action terminal-fullscreen-action" aria-pressed={fullscreen} onClick={() => void toggleFullscreen()}>{fullscreen ? "Salir de pantalla completa" : "Pantalla completa de conexión"}</button>
    </div>
    <div className="terminal-protocol-selector" role="group" aria-label="Tipo de conexión del laboratorio">
      {(["ssh", "rdp"] as const).map((name) => <button key={name} type="button"
        aria-pressed={protocol === name} disabled={!protocols?.includes(name) || state === "loading"}
        onClick={() => switchProtocol(name)}>{name === "ssh" ? "SSH · Terminal" : "RDP · Escritorio"}</button>)}
      <small role="status">{!protocols ? "Comprobando conexiones disponibles…" : !protocols.includes("rdp")
        ? "RDP no está configurado para esta VM; consulta al instructor."
        : !protocols.includes("ssh") ? "SSH no está configurado para esta VM." : "Elige SSH o RDP; se abre una conexión a la vez."}</small>
    </div>
    <div className="terminal-stage">
      <div className="guacamole-viewport guacamole-canvas" ref={viewport} tabIndex={state === "auth" || !protocol ? -1 : 0} role="region"
        aria-label={protocol === "rdp" ? "Escritorio RDP interactivo" : "Terminal SSH interactiva"}
        aria-hidden={state === "auth" || !protocol}
        onPointerDown={(event) => event.currentTarget.focus()} onBlur={() => keyboardRef.current?.reset()}
        onPaste={(event) => {
          const text = event.clipboardData.getData("text/plain"); const client = clientRef.current;
          if (!text || !client || !window.Guacamole) return;
          event.preventDefault();
          const writer = new window.Guacamole.StringWriter(client.createClipboardStream("text/plain"));
          writer.sendText(text); writer.sendEnd();
        }} />
      {(state === "loading" || (!protocol && !optionsError)) && <p className="terminal-stage-overlay" role="status">{protocol ? `Abriendo ${protocol.toUpperCase()}…` : "Comprobando conexiones disponibles…"}</p>}
      {state === "auth" && <form className="terminal-auth-form" onSubmit={authenticate}>
        <h3>Conecta tu cuenta de laboratorio</h3><p>Usa tu contraseña personal de Guacamole. No se almacena en el navegador.</p>
        <label htmlFor={`terminal-password-${runId}`}>Contraseña personal</label>
        <input id={`terminal-password-${runId}`} type="password" autoComplete="current-password" value={password} maxLength={256} required onChange={(event) => setPassword(event.target.value)} />
        <button className="primary-action" disabled={authenticating}>{authenticating ? "Conectando…" : "Conectar"}</button>
      </form>}
    </div>
    {optionsError && <div className="terminal-connection-notice" role="alert"><p>{optionsError}</p><button type="button" className="secondary-action" onClick={() => setOptionsAttempt((value) => value + 1)}>Reintentar conexiones</button></div>}
    {message && <p className="terminal-connection-notice" role="alert">{message}</p>}
    {(state === "error" || state === "disconnected") && <div className="terminal-connection-notice">
      <button type="button" className="secondary-action" onClick={() => setAttempt((value) => value + 1)}>Reconectar terminal</button>
      <button type="button" className="secondary-action" onClick={() => setState("auth")}>Conectar mi cuenta</button>
    </div>}
    <p className="terminal-connection-notice">{protocol === "rdp" ? "Interactúa con el escritorio asignado. Copia la evidencia y pégala en el campo de envío." : "Haz clic en la terminal para escribir. Selecciona la evidencia para recibirla en el bloc; también puedes pegar la flag en el campo de envío."}</p>
  </section>;
}
