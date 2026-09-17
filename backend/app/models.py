# ============================================================
# MODELOS DE DATOS
# Responsabilidad: definir las entidades SQLAlchemy y sus relaciones persistentes.
# ============================================================

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(String(160))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(32), index=True)
    full_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(160), nullable=True)
    user_function: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")


class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(16), index=True)
    category: Mapped[str] = mapped_column(String(48), index=True, default="MISC")
    scenario: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    mitre_technique: Mapped[str] = mapped_column(String(64), index=True)
    asset_references: Mapped[list[str]] = mapped_column(JSON, default=list)
    points: Mapped[int] = mapped_column(Integer)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    flags: Mapped[list["ChallengeFlag"]] = relationship(back_populates="challenge", cascade="all, delete-orphan", order_by="ChallengeFlag.flag_order")


class ChallengeFlag(Base):
    __tablename__ = "challenge_flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(120))
    flag_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    validator: Mapped[str] = mapped_column(String(32), default="exact_hash")
    mode: Mapped[str] = mapped_column(String(16), default="static")
    template: Mapped[str | None] = mapped_column(String(512), nullable=True)
    flag_order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    challenge: Mapped[Challenge] = relationship(back_populates="flags")


class ChallengeRunFlag(Base):
    __tablename__ = "challenge_run_flags"
    __table_args__ = (UniqueConstraint("run_id", "flag_id", name="uq_run_flag"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("challenge_runs.id", ondelete="CASCADE"), index=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("challenge_flags.id", ondelete="CASCADE"), index=True)
    flag_hash: Mapped[str] = mapped_column(String(512))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"), index=True)
    flag_id: Mapped[int | None] = mapped_column(ForeignKey("challenge_flags.id"), nullable=True)
    submitted_value_hmac: Mapped[str] = mapped_column(String(64))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user: Mapped[User] = relationship(back_populates="submissions")


class ChallengeCompletion(Base):
    __tablename__ = "challenge_completions"
    __table_args__ = (UniqueConstraint("user_id", "challenge_id", name="uq_completion_user_challenge"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    awarded_points: Mapped[int] = mapped_column(Integer)


class ChallengeRun(Base):
    __tablename__ = "challenge_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    workspace_strategy: Mapped[str] = mapped_column(String(32), default="per_user_account")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignment: Mapped[Optional["RemoteAccessAssignment"]] = relationship(back_populates="run", cascade="all, delete-orphan", uselist=False)


class RemoteAccessAssignment(Base):
    __tablename__ = "remote_access_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("challenge_runs.id", ondelete="CASCADE"), unique=True)
    provider: Mapped[str] = mapped_column(String(32), default="guacamole")
    external_reference: Mapped[str] = mapped_column(String(160), unique=True)
    launch_url: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    run: Mapped[ChallengeRun] = relationship(back_populates="assignment")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class StudentGroup(Base):
    __tablename__ = "student_groups"
    __table_args__ = (UniqueConstraint("name", name="uq_student_group_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    guacamole_group_identifier: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    members: Mapped[list["GroupMembership"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    challenge_assignments: Mapped[list["ChallengeGroupAssignment"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("student_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    group: Mapped[StudentGroup] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class ChallengeGroupAssignment(Base):
    __tablename__ = "challenge_group_assignments"
    __table_args__ = (UniqueConstraint("challenge_id", "group_id", name="uq_challenge_group"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("student_groups.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    group: Mapped[StudentGroup] = relationship(back_populates="challenge_assignments")
    challenge: Mapped[Challenge] = relationship()


class Laboratory(Base):
    __tablename__ = "laboratories"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    segment: Mapped[str] = mapped_column(String(64), default="VLAN 30")
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vms: Mapped[list["VMAsset"]] = relationship(back_populates="laboratory", cascade="all, delete-orphan")


class ResetOperation(Base):
    __tablename__ = "reset_operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    laboratory_id: Mapped[int] = mapped_column(ForeignKey("laboratories.id", ondelete="CASCADE"), index=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), default="baseline")
    reason: Mapped[str] = mapped_column(String(300), default="Reset solicitado por administrador")
    status: Mapped[str] = mapped_column(String(32), default="requested", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class VMAsset(Base):
    __tablename__ = "vm_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    laboratory_id: Mapped[int] = mapped_column(ForeignKey("laboratories.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    os: Mapped[str] = mapped_column(String(120), default="Por definir")
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vlan: Mapped[str] = mapped_column(String(32), default="VLAN 30")
    role: Mapped[str] = mapped_column(String(120), default="Máquina de laboratorio")
    network_role: Mapped[str] = mapped_column(String(64), default="Víctimas")
    subnet: Mapped[str] = mapped_column(String(64), default="10.10.30.0/24")
    profile: Mapped[str] = mapped_column(String(32), default="standard")
    baseline: Mapped[str | None] = mapped_column(String(160), nullable=True)
    nutanix_vm_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    guacamole_connection_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    laboratory: Mapped[Laboratory] = relationship(back_populates="vms")
