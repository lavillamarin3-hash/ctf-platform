"""Provisiona solo el servicio SSH de práctica en la VM autorizada, sin sudo."""
import asyncio
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shlex
import time
import paramiko
from ..core import get_settings, submission_fingerprint

CODE = 'ESC-02-BRUTEFORCE'
HOST = '192.168.146.137'
PORT = 2222
WORDS = ['Verde2026!', 'Aula2026!', 'Practica01!', 'Kali2026!', 'Laboratorio7!', 'Alumno123!',
         'CTF2026!', 'Acceso2026!', 'Entrena01!', 'Linux2026!', 'ClaveLocal9!', 'Demo2026!']


def password_for(run):
    index = int(submission_fingerprint(f'ssh-practice:password:{run.user_id}:{run.id}')[:8],16)%len(WORDS)
    return WORDS[index]


def flag_for(run):
    return 'FLAG{ssh_practice_' + submission_fingerprint(f'ssh-practice:flag:{run.user_id}:{run.id}') + '}'


@contextmanager
def connection():
    settings = get_settings(); client = paramiko.SSHClient()
    if settings.flag_injector_known_hosts: client.load_host_keys(settings.flag_injector_known_hosts)
    else: client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy() if settings.flag_injector_strict_host_key else paramiko.AutoAddPolicy())
    kwargs = dict(hostname=HOST,port=settings.flag_injector_ssh_port,username=settings.flag_injector_ssh_user,
                  timeout=8,banner_timeout=8,auth_timeout=8,allow_agent=False,look_for_keys=False)
    if settings.flag_injector_ssh_private_key: kwargs['key_filename']=settings.flag_injector_ssh_private_key
    elif settings.flag_injector_ssh_password: kwargs['password']=settings.flag_injector_ssh_password
    else: raise RuntimeError('No hay acceso SSH configurado para preparar la práctica')
    try:
        client.connect(**kwargs)
        yield client
    finally: client.close()


def _command(client, command):
    _, out, err = client.exec_command(command,timeout=20)
    result = out.read().decode()
    if out.channel.recv_exit_status()!=0:
        raise RuntimeError('La VM no pudo preparar el servicio SSH de práctica')
    return result


def provision(run_id, username, password, flag, expires):
    with connection() as client, client.open_sftp() as sftp:
        home = sftp.normalize('.')
        directory = home+'/.ctf-ssh-practice'
        try: sftp.mkdir(directory,0o700)
        except OSError:
            import stat
            info=sftp.lstat(directory)
            if not stat.S_ISDIR(info.st_mode): raise RuntimeError('Directorio de práctica inválido')
        sftp.chmod(directory,0o700)
        script = Path(__file__).parents[1]/'infrastructure/injection/scripts/linux/ctf-ssh-practice.py'
        remote = directory+'/server.py'
        source = script.read_bytes()
        try:
            with sftp.open(remote, 'rb') as old:
                source_changed = old.read() != source
        except FileNotFoundError:
            source_changed = False
        script_temp = remote + '.' + str(int(run_id)) + '.tmp'
        with sftp.open(script_temp, 'w') as file: file.write(source)
        sftp.chmod(script_temp, 0o600)
        sftp.posix_rename(script_temp, remote)
        config = {'password_sha256':hashlib.sha256(password.encode()).hexdigest(),'flag':flag,'expires_at':expires}
        path = directory+'/'+username+'.json'; temp=path+'.tmp'
        with sftp.open(temp,'w') as file: file.write(json.dumps(config))
        sftp.chmod(temp,0o600); sftp.posix_rename(temp,path)
        if source_changed:
            # Solo recargar nuestro proceso de práctica, con UID y argv exactos.
            # Los registros y la clave de host permanecen en su directorio.
            restart = ("import os,pathlib,signal,time; "
                       f"expected=[b'python3',{remote.encode()!r},b'--directory',{directory.encode()!r}]; "
                       "pids=[]; "
                       "\nfor p in pathlib.Path('/proc').glob('[0-9]*'):"
                       "\n try:"
                       "\n  if p.stat().st_uid==os.getuid() and (p/'cmdline').read_bytes().rstrip(b'\\0').split(b'\\0')==expected: pids.append(int(p.name))"
                       "\n except (OSError,ValueError): pass"
                       "\nfor pid in pids:"
                       "\n try: os.kill(pid,signal.SIGTERM)"
                       "\n except ProcessLookupError: pass"
                       "\nif pids: time.sleep(0.5)")
            _command(client, 'python3 -c ' + shlex.quote(restart))
        # Un lock de archivo evita duplicar servidores al iniciar corridas concurrentes.
        command = ('nohup flock -n '+shlex.quote(directory+'/server.lock')+' python3 '+shlex.quote(remote)
                   +' --directory '+shlex.quote(directory)+' </dev/null >'+shlex.quote(directory+'/server.log')+' 2>&1 &')
        _command(client,command)
        for _ in range(40):
            transport = client.get_transport()
            try:
                # Solo comprobar el socket; el servicio acepta autenticación únicamente desde Kali.
                channel = transport.open_channel('direct-tcpip',(HOST,PORT),('127.0.0.1',0),timeout=2)
                channel.close()
                return
            except (OSError,paramiko.SSHException): time.sleep(0.5)
        raise RuntimeError('El puerto 2222 no está disponible en LNX-VICT')


def remove(run_id):
    with connection() as client, client.open_sftp() as sftp:
        path=sftp.normalize('.')+'/.ctf-ssh-practice/ctf'+str(int(run_id))+'.json'
        try: sftp.remove(path)
        except FileNotFoundError: pass


async def prepare(run):
    try:
        await asyncio.to_thread(provision,run.id,f'ctf{run.id}',password_for(run),flag_for(run),run.expires_at.timestamp())
    except Exception:
        try: await asyncio.to_thread(remove,run.id)
        except Exception: pass
        raise


async def cleanup(run):
    await asyncio.to_thread(remove,run.id)


def instructions(run):
    user=f'ctf{run.id}'
    dictionary="printf '%s\\n' "+' '.join(shlex.quote(w) for w in WORDS)+' > /tmp/ctf-passwords.txt'
    return {'target':f'{HOST}:{PORT}','username':user,'wordlist':WORDS,
            'commands':[dictionary,f'hydra -l {user} -P /tmp/ctf-passwords.txt -t 1 -f -s {PORT} {HOST} ssh',
                        f'ssh -p {PORT} {user}@{HOST}','cat flag.txt'],
            'note':'Servicio SSH real de práctica con shell restringida. No usa cuentas del sistema. Prueba únicamente estos 12 candidatos contra el puerto 2222 indicado; al cerrar o caducar la corrida se invalida el acceso.'}
