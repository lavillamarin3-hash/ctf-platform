"""Portal SQLi vulnerable exclusivamente para una demostración aislada."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, abort, redirect, render_template_string, request, session, url_for

HOST = os.environ.get("DEMO_WEB_HOST", "10.10.30.20")
PORT = int(os.environ.get("DEMO_WEB_PORT", "8088"))
ALLOWED_SOURCE = os.environ.get("DEMO_WEB_ALLOWED_SOURCE", "10.10.20.11")
STUDENT_USER = os.environ["DEMO_WEB_STUDENT_USER"]
STUDENT_PASSWORD = os.environ["DEMO_WEB_STUDENT_PASSWORD"]
FLAG = os.environ["DEMO_WEB_FLAG"]
DB = Path("/state/demo.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["DEMO_WEB_SESSION_SECRET"]

BASE = """<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portal de prácticas CoCiber</title>
<style>body{font:16px system-ui;background:#07111f;color:#d9e5f3;max-width:720px;margin:6rem auto;padding:0 1rem}main{background:#10233b;padding:2rem;border-radius:12px}input,button{display:block;margin:.7rem 0;padding:.7rem;width:100%;box-sizing:border-box}button{background:#25a4d8;color:#00131d;border:0;font-weight:bold}.warning{color:#ffd166}.error{color:#ff8b8b}code{word-break:break-all}</style>
<main>{body}</main></html>"""


def page(body: str) -> str:
    return render_template_string(BASE.replace("{body}", body))


def connection() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL)")
    db.execute("INSERT OR IGNORE INTO users VALUES (?, ?, 'student')", (STUDENT_USER, STUDENT_PASSWORD))
    db.execute("INSERT OR IGNORE INTO users VALUES ('portal-admin', 'local-demo-only', 'admin')")
    db.commit()
    return db


@app.before_request
def vlan_boundary():
    # network_mode: host preserves the Kali address. El host y loopback pueden
    # consultar health durante la preparación, pero no iniciar sesiones remotas.
    if request.remote_addr not in {ALLOWED_SOURCE, "127.0.0.1"}:
        abort(403)


@app.get("/")
def index():
    return page("""
      <h1>Portal de prácticas</h1>
      <p class='warning'>Entorno vulnerable intencionalmente. Uso exclusivo de la VLAN del laboratorio.</p>
      <p>Accede con la cuenta de práctica o investiga el formulario conforme al reto asignado.</p>
      <form method='post' action='/login'><label>Usuario</label><input name='username' required autofocus>
      <label>Contraseña</label><input name='password' type='password' required><button>Iniciar sesión</button></form>
    """)


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    # VULNERABILIDAD INTENCIONAL: el reto usa una consulta concatenada.
    query = f"SELECT username, role FROM users WHERE username = '{username}' AND password = '{password}'"
    try:
        row = connection().execute(query).fetchone()
    except sqlite3.Error:
        return page("<h1>Error de consulta</h1><p class='error'>La consulta no se pudo procesar.</p><p><a href='/'>Volver</a></p>"), 400
    if row is None:
        return page("<h1>Acceso denegado</h1><p><a href='/'>Volver</a></p>"), 401
    session["user"] = row["username"]
    session["role"] = row["role"]
    return redirect(url_for("portal"))


@app.get("/portal")
def portal():
    if "user" not in session:
        return redirect(url_for("index"))
    if session.get("role") != "admin":
        body = f"<h1>Bienvenido, {session['user']}</h1><p>Tu cuenta no tiene acceso al registro de evidencias.</p><p><a href='/logout'>Cerrar sesión</a></p>"
        return page(body)
    body = f"<h1>Registro administrativo</h1><p>La evidencia del ejercicio es:</p><code>{FLAG}</code><p><a href='/logout'>Cerrar sesión</a></p>"
    return page(body)


@app.get("/health")
def health():
    return {"status": "ok", "service": "cociber-web-demo"}


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    connection().close()
    app.run(host=HOST, port=PORT, debug=False)
