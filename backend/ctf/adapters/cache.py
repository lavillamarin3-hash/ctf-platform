from datetime import datetime, timezone
import hashlib
import json
import secrets
from redis.asyncio import Redis


class Cache:
    def __init__(self, url):
        self.client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3)

    async def lock(self, run):
        ttl = max(120, int((run.expires - datetime.now(timezone.utc)).total_seconds()))
        for key, seconds in ((f"lock:reto:{run.challenge_id}", 120), (f"lock:maquina:{run.attacker_id}", ttl)):
            # Un fallo Redis no suplanta la reserva ya confirmada en PostgreSQL.
            try: await self.client.set(key, run.id, nx=True, ex=seconds)
            except Exception: pass

    async def unlock(self, run):
        script = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) end return 0"
        for key in (f"lock:reto:{run.challenge_id}", f"lock:maquina:{run.attacker_id}"):
            try: await self.client.eval(script, 1, key, run.id)
            except Exception: pass

    async def login_attempt(self, username):
        # HMAC no necesario: no contiene contraseña; hash evita claves arbitrarias.
        key = "rate:login:" + hashlib.sha256(username.lower().encode()).hexdigest()
        script = "local n=redis.call('incr',KEYS[1]); if n==1 then redis.call('expire',KEYS[1],60) end; return n"
        return int(await self.client.eval(script, 1, key)) <= 8

    async def ticket(self, run_id, user_id, claims):
        token = secrets.token_urlsafe(32)
        await self.client.set("terminal:ticket:" + hashlib.sha256(token.encode()).hexdigest(), json.dumps([run_id, str(user_id), claims]), ex=45)
        return token

    async def consume(self, token):
        value = await self.client.getdel("terminal:ticket:" + hashlib.sha256(token.encode()).hexdigest())
        return json.loads(value) if value else None
