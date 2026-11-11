from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from ...domain.laboratory import validate_hints


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=1, max_length=256)


class Password(BaseModel):
    current: str = Field(max_length=256)
    new: str = Field(min_length=10, max_length=256)


class NewUser(Login):
    model_config = ConfigDict(extra="forbid")
    role: Literal[2, 3, 4] = 3
    password: str = Field(min_length=10, max_length=256)


class UpdateUser(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    role: Literal[2, 3, 4] | None = None
    state: Literal["activo", "inactivo", "bloqueado"] | None = None
    password: str | None = Field(default=None, min_length=10, max_length=256)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Indica al menos un cambio, sin valores nulos")
        return self


class DeleteUser(BaseModel):
    confirmation: str = Field(min_length=3, max_length=50)


class GroupInput(BaseModel):
    code: str = Field(min_length=3, max_length=30, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=3, max_length=100)
    users: list[UUID] = Field(default_factory=list, max_length=100)


class LabInput(BaseModel):
    code: str = Field(min_length=3, max_length=30, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=3, max_length=100)
    segment: Literal["VLAN20-10.10.20.0/24", "VLAN30-10.10.30.0/24"]
    machines: list[UUID] = Field(min_length=1, max_length=30)


class HintInput(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    penalty: int = Field(default=0, ge=0, le=500)


class ResourceInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    url: str = Field(max_length=1024)

    @field_validator("url")
    @classmethod
    def safe_url(cls, value):
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username: raise ValueError("Usa un recurso HTTPS sin credenciales")
        return value


class ChallengeInput(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=3, max_length=120)
    difficulty: Literal["basico", "medio", "avanzado"] = "medio"
    victim_id: UUID
    strategy: str = Field(max_length=40)
    points: int | None = Field(default=None, ge=1, le=10000)
    description: str = Field(default="", max_length=10000)
    instructions: str = Field(default="", max_length=10000)
    hints: list[HintInput] = Field(default_factory=list, max_length=3)
    duration_minutes: int | None = Field(default=None, ge=5, le=120)
    resources: list[ResourceInput] = Field(default_factory=list, max_length=5)


class AssignmentInput(BaseModel):
    groups: list[UUID] = Field(min_length=1, max_length=50)


class FlagInput(BaseModel):
    flag: str = Field(min_length=1, max_length=256)


class MachineState(BaseModel):
    state: Literal["ready", "mantenimiento"]


class MaintenanceInput(BaseModel):
    machine_id: UUID
    reason: str = Field(min_length=5, max_length=1000)
