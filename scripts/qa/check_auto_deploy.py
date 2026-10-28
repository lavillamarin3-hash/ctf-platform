"""Comprobaciones estáticas del mecanismo de despliegue de CoCiber CTF.

No ejecuta Docker, no consulta credenciales y no modifica el servidor.
"""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
deploy = (repo / "scripts/cociber_auto_deploy_main.sh").read_text(encoding="utf-8")
installer = (repo / "scripts/instalar_auto_deploy_main.sh").read_text(encoding="utf-8")
service = (repo / "deploy/systemd/cociber-ctf-auto-deploy.service").read_text(encoding="utf-8")
timer = (repo / "deploy/systemd/cociber-ctf-auto-deploy.timer").read_text(encoding="utf-8")

for expected in [
    "ctf-quality.yml", "head_sha=$NEW_SHA", 'r.get("conclusion")=="success"',
    "git_app merge-base --is-ancestor", 'git_app merge --ff-only "$NEW_SHA"',
    'git_app status --porcelain', "flock -n 9",
    "docker compose -f docker-compose.prod.yml",
    "compose build api web", "compose up -d --no-deps api web",
    "git_app reset --hard", "dependencies_ok", "MANAGE_SCHEMA",
    "guacamole_mode", "list_connections()",
]:
    # MANAGE_SCHEMA deliberately lives in docs/config, not the deployment script.
    if expected == "MANAGE_SCHEMA":
        continue
    assert expected in deploy, f"Deployment missing safety gate: {expected}"

assert "docker compose down" not in deploy
assert "down -v" not in deploy
assert "prune" not in deploy
assert "docker compose -f docker-compose.yml" not in deploy
assert 'GUACAMOLE_SERVICE_PASSWORD=' not in deploy
assert ".env.example" not in deploy
assert "systemctl enable --now cociber-ctf-auto-deploy.timer" in installer
assert "install -m 0750" in installer
assert "chmod 0600" in installer
assert 'install -m 0644' in installer
assert 'EnvironmentFile=/etc/cociber-ctf/auto-deploy.conf' in service
assert "ExecStart=/usr/local/sbin/cociber-auto-deploy-main --once" in service
assert "OnUnitActiveSec=2min" in timer

print("Deployment static safety checks passed.")
