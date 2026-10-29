"""Acceso a la Kali asignada y transferencia de evidencias públicas por portapapeles."""
import base64
import io
import shlex
import zipfile
from fastapi import HTTPException
from sqlalchemy import select
from ..models import VMAsset, Laboratory
STRATEGIES = ('offline_case','dfir_case','ssh_password_lab','http_password_lab','http_files_lab','vm_logic_lab','external_web_lab','dvwa_sql_lab')


# Inventario AHV fijo: las conexiones Guacamole se validan contra IP + protocolo.
# La elección de Kali proviene del reto guardado en PostgreSQL, nunca del navegador.
KALI_VMS = {
    'LAB-KALI': '10.10.20.10',
    'LAB-KALI-PURPLE': '10.10.20.11',
    'LAB-KALI-BLUE': '10.10.20.12',
}


def selected_attacker(challenge=None):
    references = set(getattr(challenge, 'asset_references', None) or [])
    explicit = [name for name in KALI_VMS if name in references]
    if len(explicit) > 1:
        raise HTTPException(409, 'Selecciona una sola Kali atacante para este reto.')
    return explicit[0] if explicit else ESC_ATTACKER_NAME


async def context(app, session, user, challenge=None):
    name = selected_attacker(challenge)
    ip = KALI_VMS[name]
    vms = list((await session.scalars(select(VMAsset).where(VMAsset.ip_address == ip))).all())
    if len(vms) != 1 or vms[0].name != name or vms[0].status != 'ready':
        raise HTTPException(409, f'{name} debe estar registrada una sola vez y en estado listo.')
    vm = vms[0]
    lab = await session.get(Laboratory, vm.laboratory_id)
    if not lab or lab.status != 'ready':
        raise HTTPException(409, 'El laboratorio de la Kali seleccionada no está listo.')
    try:
        connections = await app.state.guacamole_admin.list_connections()
        permissions = await app.state.guacamole_admin.get_user_permissions(user.username)
    except Exception as exc:
        raise HTTPException(503, 'No fue posible consultar las conexiones de Guacamole.') from exc
    readable = {
        str(identifier) for identifier, actions in (permissions.get('connectionPermissions') or {}).items()
        if 'READ' in (actions or [])
    }
    targets = {}
    for protocol in ('ssh', 'rdp'):
        matches = [conn for conn in connections
                   if (conn.protocol or '').strip().lower() == protocol
                   and (conn.hostname or '').strip() == ip]
        # Rechazar conexiones ambiguas, aunque el estudiante tenga READ.
        if len(matches) == 1 and str(matches[0].identifier) in readable:
            targets[protocol] = str(matches[0].identifier)
    if not targets:
        raise HTTPException(403, f'{name} necesita una conexión SSH o RDP única en Guacamole y permiso READ del estudiante.')
    return vm, targets


def transfer_command(run, files):
    # Todos los nombres son generados por el catálogo; no se aceptan rutas del alumno.
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as zipped:
        for name,data in files.items():
            if name.startswith('/') or '..' in name.split('/'): raise ValueError('Ruta inválida')
            zipped.writestr(name,data)
    encoded=base64.b64encode(stream.getvalue()).decode()
    script=("import base64,io,pathlib,zipfile; "
            f"p=pathlib.Path.home()/'ctf'/'corrida-{int(run.id)}'; p.mkdir(parents=True,exist_ok=True); "
            f"zipfile.ZipFile(io.BytesIO(base64.b64decode('{encoded}'))).extractall(p); print('Archivos en:',p)")
    return 'python3 -c '+shlex.quote(script)
