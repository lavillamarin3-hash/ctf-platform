from functools import lru_cache
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    redis_url: str
    public_origin: str
    jwt_secret: SecretStr
    jwt_expira_minutos: int = Field(default=60, ge=5, le=240)
    bootstrap_admin: bool = False
    admin_ctf_username: str = "admin_ctf"
    admin_ctf_password: SecretStr = SecretStr("")
    guacamole_api_url: str = "http://10.10.10.10:8080/guacamole"
    guacamole_admin_user: str = ""
    guacamole_admin_password: SecretStr = SecretStr("")
    guacamole_datasource: str = "mysql"
    ssh_injector_enabled: bool = False
    ssh_injector_key_path: str = "/run/secrets/labops_ed25519"
    ssh_injector_known_hosts: str = "/run/secrets/known_hosts"
    ssh_injector_user: str = "labops"
    dvwa_lab_enabled: bool = False
    winrm_injector_enabled: bool = False
    winrm_service_user: str = "labops"
    winrm_service_password: SecretStr = SecretStr("")
    ttl_corrida_basico_min: int = Field(default=30, ge=5, le=120)
    ttl_corrida_medio_min: int = Field(default=45, ge=5, le=120)
    ttl_corrida_avanzado_min: int = Field(default=60, ge=5, le=120)

    @field_validator("jwt_secret")
    @classmethod
    def strong_secret(cls, value):
        if len(value.get_secret_value()) < 64 or "CHANGE_ME" in value.get_secret_value():
            raise ValueError("Genera JWT_SECRET con openssl rand -hex 32")
        return value

    @field_validator("public_origin")
    @classmethod
    def origin(cls, value):
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("PUBLIC_ORIGIN debe contener solamente esquema y autoridad")
        return value.rstrip("/")

    @field_validator("database_url")
    @classmethod
    def postgres(cls, value):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def settings():
    return Settings()
