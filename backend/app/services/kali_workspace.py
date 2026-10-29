"""Acceso a la Kali asignada y transferencia de evidencias públicas por portapapeles."""
import base64
import io
import shlex
import zipfile
from fastapi import HTTPException
from sqlalchemy import select
from ..models import VMAsset, Laboratory
STRATEGIES = ('offline_case','dfir_case','ssh_password_lab','http_password_lab','http_files_lab','vm_logic_lab','external_web_lab','dvwa_sql_lab')

# El reto declara exactamente una Kali de este inventario. No se aceptan IPs
# editables como destino de terminal para impedir redirigir al alumno a otra VM.
KALI_ASSETS = {
    'LAB-KALI': '10.10.20.10',
    'LAB-KALI-PURPLE': '10.10.20.11',
    'LAB-KALI-BLUE': '10.10.20.12',
}


def attacker_for(challenge):
    refs = [str(value).strip().upper() for value in (challenge.asset_references or [])]
    attackers = [name for name in refs if name in KALI_ASSETS]
    if len(attackers) != 1:
        return None
    name = attackers[0]
    return name, KALI_ASSETS[name]


def has_attacker(challenge) -> bool:
    return attacker_for(challenge) is not None


def _unique_kali_connections(connections, ip_address: str) -> dict[str, str]:
    targets: dict[str, str] = {}
    for protocol in ('ssh', 'rdp'):
        matches = [
            connection for connection in connections
            if (connection.protocol or '').strip().lower() == protocol
            and (connection.hostname or '').strip() == ip_address
        ]
        if len(matches) == 1:
            targets[protocol] = str(matches[0].identifier)
    return targets


async def context(app, session, user, challenge):
    attacker = attacker_for(challenge)
    if attacker is None:
        raise HTTPException(409, 'El ejercicio debe declarar exactamente una Kali autorizada.')
    name, ip_address = attacker
    vms=list((await session.scalars(select(VMAsset).where(VMAsset.ip_address==ip_address))).all())
    if len(vms)!=1 or vms[0].name!=name or vms[0].status!='ready':
        raise HTTPException(409, f'{name} debe estar registrada una sola vez y en estado listo.')
    vm=vms[0]; lab=await session.get(Laboratory,vm.laboratory_id)
    if not lab or lab.status!='ready': raise HTTPException(409,'El laboratorio Kali no está listo.')
    connections=await app.state.guacamole_admin.list_connections()
    permissions=await app.state.guacamole_admin.get_user_permissions(user.username)
    targets={protocol:identifier for protocol,identifier in _unique_kali_connections(connections, ip_address).items()
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
