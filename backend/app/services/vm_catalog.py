"""Habilitación explícita de Kali y del escenario SSH de contraseñas."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..models import Challenge
from ..api.challenges import require_idle_challenge
from ..domain.challenges.offline import CATALOG
from .bootstrap import write_audit
from .ssh_practice import CODE


async def configure(session):
    challenges=(await session.scalars(select(Challenge).options(selectinload(Challenge.flags)).where(Challenge.code.in_([*CATALOG,'DFIR-01'])).order_by(Challenge.id).with_for_update())).all()
    if len(challenges)!=36: raise ValueError('No se encontró el catálogo completo de 36 casos')
    for c in challenges:
        if (c.scenario or '').startswith('VM-LOGIC-'): continue
        desired=['LAB-KALI','LAB-LNXVICT'] if c.code==CODE else (['DFIR-CASE','LAB-KALI'] if c.code=='DFIR-01' else ['OFFLINE-CASE','LAB-KALI'])
        if c.asset_references==desired and (c.code!=CODE or c.scenario=='SSH-PASSWORD-LAB'): continue
        await require_idle_challenge(session,c.id)
        before={key:getattr(c,key) for key in ('name','description','instructions','scenario','asset_references','mitre_technique','difficulty')}
        await write_audit(session,None,'challenge.vm.enable','challenge',str(c.id),{'code':c.code,'before':before})
        c.asset_references=desired
        if c.code==CODE:
            active=[f for f in c.flags if f.is_active]
            if len(active)!=1 or active[0].mode!='dynamic': raise ValueError('ESC-02 requiere una flag dinámica activa')
            c.name='Fuerza bruta de credenciales · SSH de práctica'
            c.description='Desde Kali encuentra la contraseña de una cuenta temporal en el servicio SSH de práctica de LNX-VICT y recupera su flag.'
            c.instructions=('Inicia la corrida y abre Kali. La pantalla muestra un usuario temporal y un diccionario de 12 contraseñas. '
                'Ejecuta el comando de Hydra indicado contra 192.168.146.137:2222, con un solo intento simultáneo. '
                'Con la contraseña encontrada entra por SSH al mismo puerto y ejecuta cat flag.txt. Envía la flag y cierra el ejercicio. '
                'El servicio es SSH real con shell didáctica restringida; no otorga una cuenta del sistema ni usa el puerto SSH administrativo. '
                'La cuenta caduca en una hora y también se invalida al cerrar. Técnica T1110.001.')
            c.scenario='SSH-PASSWORD-LAB'; c.mitre_technique='T1110.001 — Brute Force: Password Guessing'; c.difficulty='Medio'
        else:
            c.instructions+=' También puedes resolverlo dentro de la VM Kali: usa Copiar comando para preparar archivos y pégalo en la terminal integrada. Trabaja en ~/ctf/corrida-ID con el ID mostrado en pantalla.'
    await session.flush()
    return {'kali_analysis':35,'ssh_practice':1,'existing_vm_labs':2}
