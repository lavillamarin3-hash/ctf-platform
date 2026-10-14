"""Acceso a la Kali conocida y transferencia de evidencias públicas por portapapeles."""
import base64
import io
import shlex
import zipfile
from fastapi import HTTPException
from sqlalchemy import select
from ..models import VMAsset, Laboratory
from .challenge_runtime import _unique_esc_kali_connections, ESC_ATTACKER_IP, ESC_ATTACKER_NAME

STRATEGIES = ('offline_case','dfir_case','ssh_password_lab','http_password_lab','http_files_lab')


async def context(app, session, user):
    vms=list((await session.scalars(select(VMAsset).where(VMAsset.ip_address==ESC_ATTACKER_IP))).all())
    if len(vms)!=1 or vms[0].name!=ESC_ATTACKER_NAME or vms[0].status!='ready':
        raise HTTPException(409,'Kali debe estar registrada una sola vez y en estado listo.')
    vm=vms[0]; lab=await session.get(Laboratory,vm.laboratory_id)
    if not lab or lab.status!='ready': raise HTTPException(409,'El laboratorio Kali no está listo.')
    connections=await app.state.guacamole_admin.list_connections()
    permissions=await app.state.guacamole_admin.get_user_permissions(user.username)
    targets={protocol:identifier for protocol,identifier in _unique_esc_kali_connections(connections).items()
             if 'READ' in (permissions.get('connectionPermissions',{}).get(identifier) or [])}
    if not targets: raise HTTPException(403,'Tu cuenta necesita permiso de acceso a Kali. Solicita al instructor sincronizar el grupo.')
    return vm,targets


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
