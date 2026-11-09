from ..adapters.persistence.repository import Repository
from ..adapters.cache import Cache
from ..adapters.injectors import SshInjector
from ..adapters.guacamole import Guacamole
from ..application.runs import RunService
from .settings import settings
from ..adapters.availability import AvailabilityGate


class Runtime:
    def __init__(self):
        self.settings = settings()
        self.repo = Repository(self.settings.database_url)
        self.cache = Cache(self.settings.redis_url)
        self.availability = AvailabilityGate(self.repo, self.cache)
        self.injector = SshInjector(self.settings)
        self.guacamole = Guacamole(self.settings, self.cache)
        self.runs = RunService(self.repo, self.injector, self.guacamole, self.cache)

    async def close(self):
        await self.cache.client.aclose()
        await self.repo.engine.dispose()
