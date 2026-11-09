import re
from argon2 import PasswordHasher, Type

hasher = PasswordHasher(type=Type.ID)


async def create_first_admin(repository, username, password):
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,50}", username) or not 10 <= len(password) <= 256:
        raise ValueError("Usuario de 3–50 caracteres y contraseña de 10–256 caracteres requeridos")
    await repository.create_first_admin(username, hasher.hash(password))


async def bootstrap(repository, settings):
    if not settings.bootstrap_admin: return
    # Reiniciar con bootstrap habilitado nunca modifica una cuenta existente.
    if await repository.admin_exists(): return
    await create_first_admin(repository, settings.admin_ctf_username, settings.admin_ctf_password.get_secret_value())
