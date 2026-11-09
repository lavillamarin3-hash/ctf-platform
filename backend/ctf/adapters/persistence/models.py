from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def col(*args, **kwargs):
    """Defaults equivalentes en ORM y en el DDL exportado."""
    default = kwargs.get("default")
    if default is uuid4:
        kwargs.setdefault("server_default", text("gen_random_uuid()"))
    elif isinstance(default, bool):
        kwargs.setdefault("server_default", text("true" if default else "false"))
    elif isinstance(default, int):
        kwargs.setdefault("server_default", text(str(default)))
    elif isinstance(default, str):
        kwargs.setdefault("server_default", text("'" + default.replace("'", "''") + "'"))
    return mapped_column(*args, **kwargs)


class Base(DeclarativeBase): pass


class Role(Base):
    __tablename__ = "ROLES"
    id: Mapped[int] = col("rol_id", primary_key=True)
    name: Mapped[str] = col("rol_nombre", String(30), unique=True)


class User(Base):
    __tablename__ = "USUARIOS"
    id: Mapped[UUID] = col("usu_id", primary_key=True, default=uuid4)
    username: Mapped[str] = col("usu_username", String(50), unique=True)
    email: Mapped[str | None] = col("usu_email", String(120), unique=True)
    password_hash: Mapped[str] = col("usu_password_hash", String(200))
    role: Mapped[int] = col("usu_rol_id", ForeignKey("ROLES.rol_id"))
    name: Mapped[str | None] = col("usu_nombre_completo", String(120))
    must_change_password: Mapped[bool] = col("usu_debe_cambiar_clave", Boolean, default=False)
    token_version: Mapped[int] = col("usu_version_sesion", Integer, default=0)
    state: Mapped[str] = col("usu_estado", String(15), default="activo")
    created: Mapped[datetime] = col("usu_creado_en", DateTime(timezone=True), server_default=func.now())
    updated: Mapped[datetime] = col("usu_actualizado_en", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("usu_estado IN ('activo','inactivo','bloqueado')"),)


class Group(Base):
    __tablename__ = "GRUPOS"
    id: Mapped[UUID] = col("gru_id", primary_key=True, default=uuid4)
    code: Mapped[str] = col("gru_codigo", String(30), unique=True)
    name: Mapped[str] = col("gru_nombre", String(100))
    description: Mapped[str] = col("gru_descripcion", Text, default="")
    created: Mapped[datetime] = col("gru_creado_en", DateTime(timezone=True), server_default=func.now())


class Member(Base):
    __tablename__ = "GRUPOS_MIEMBROS"
    id: Mapped[UUID] = col("grm_id", primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = col("grm_grupo_id", ForeignKey("GRUPOS.gru_id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = col("grm_usuario_id", ForeignKey("USUARIOS.usu_id", ondelete="CASCADE"))
    created: Mapped[datetime] = col("grm_agregado_en", DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("grm_grupo_id", "grm_usuario_id"),)


class Machine(Base):
    __tablename__ = "MAQUINAS_VIRTUALES"
    id: Mapped[UUID] = col("maq_id", primary_key=True, default=uuid4)
    name: Mapped[str] = col("maq_nombre", String(60), unique=True)
    kind: Mapped[str] = col("maq_tipo", String(12))
    os: Mapped[str] = col("maq_so", String(60))
    ip: Mapped[str] = col("maq_ip", INET, unique=True)
    vlan: Mapped[int] = col("maq_vlan", Integer)
    state: Mapped[str] = col("maq_estado", String(15), default="planned")
    created: Mapped[datetime] = col("maq_creado_en", DateTime(timezone=True), server_default=func.now())
    updated: Mapped[datetime] = col("maq_actualizado_en", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("maq_tipo IN ('atacante','victima')"), CheckConstraint("maq_estado IN ('planned','ready','en_uso','mantenimiento','dirty')"), Index("ix_maq_tipo_estado", "maq_tipo", "maq_estado"))


class Connection(Base):
    __tablename__ = "CONEXIONES_GUACAMOLE"
    id: Mapped[UUID] = col("con_id", primary_key=True, default=uuid4)
    machine_id: Mapped[UUID] = col("con_maquina_id", ForeignKey("MAQUINAS_VIRTUALES.maq_id"))
    name: Mapped[str] = col("con_nombre", String(80))
    protocol: Mapped[str] = col("con_protocolo", String(10), default="ssh")
    port: Mapped[int] = col("con_puerto", Integer, default=22)
    external_id: Mapped[str | None] = col("con_guacamole_id_externo", String(80))
    created: Mapped[datetime] = col("con_creado_en", DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("con_protocolo IN ('ssh','rdp','vnc')"),)


class Laboratory(Base):
    __tablename__ = "LABORATORIOS"
    id: Mapped[UUID] = col("lab_id", primary_key=True, default=uuid4)
    code: Mapped[str] = col("lab_codigo", String(30), unique=True)
    name: Mapped[str] = col("lab_nombre", String(100))
    description: Mapped[str] = col("lab_descripcion", Text, default="")
    segment: Mapped[str] = col("lab_segmento", String(40))
    state: Mapped[str] = col("lab_estado", String(15), default="planned")


class LabMachine(Base):
    __tablename__ = "LABORATORIO_MAQUINAS"
    id: Mapped[UUID] = col("lbm_id", primary_key=True, default=uuid4)
    lab_id: Mapped[UUID] = col("lbm_laboratorio_id", ForeignKey("LABORATORIOS.lab_id", ondelete="CASCADE"))
    machine_id: Mapped[UUID] = col("lbm_maquina_id", ForeignKey("MAQUINAS_VIRTUALES.maq_id", ondelete="CASCADE"))
    __table_args__ = (UniqueConstraint("lbm_laboratorio_id", "lbm_maquina_id"),)


class Challenge(Base):
    __tablename__ = "RETOS"
    id: Mapped[UUID] = col("ret_id", primary_key=True, default=uuid4)
    code: Mapped[str] = col("ret_codigo", String(40), unique=True)
    name: Mapped[str] = col("ret_nombre", String(120))
    category: Mapped[str] = col("ret_categoria", String(40), default="LAB")
    difficulty: Mapped[str] = col("ret_dificultad", String(10))
    mitre: Mapped[str] = col("ret_tecnica_mitre", String(20))
    points: Mapped[int] = col("ret_puntos", Integer)
    description: Mapped[str] = col("ret_descripcion", Text, default="")
    instructions: Mapped[str] = col("ret_instrucciones", Text, default="")
    strategy: Mapped[str] = col("ret_estrategia", String(40))
    victim_id: Mapped[UUID] = col("ret_maquina_victima_id", ForeignKey("MAQUINAS_VIRTUALES.maq_id"))
    state: Mapped[str] = col("ret_estado", String(12), default="draft")
    pilot_passed: Mapped[bool] = col("ret_piloto_aprobado", Boolean, default=False)
    duration_minutes: Mapped[int | None] = col("ret_duracion_minutos", Integer)
    resources: Mapped[list] = col("ret_recursos", JSONB, default=list, server_default=text("'[]'::jsonb"))
    creator_id: Mapped[UUID | None] = col("ret_creado_por", ForeignKey("USUARIOS.usu_id"))
    created: Mapped[datetime] = col("ret_creado_en", DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("ret_dificultad IN ('basico','medio','avanzado')"), CheckConstraint("ret_estado IN ('draft','published','archived')"), CheckConstraint("ret_puntos > 0"))


class Hint(Base):
    __tablename__ = "RETOS_PISTAS"
    id: Mapped[UUID] = col("pis_id", primary_key=True, default=uuid4)
    challenge_id: Mapped[UUID] = col("pis_reto_id", ForeignKey("RETOS.ret_id", ondelete="CASCADE"))
    order: Mapped[int] = col("pis_orden", Integer)
    title: Mapped[str] = col("pis_titulo", String(80), default="Pista")
    text: Mapped[str] = col("pis_texto", Text)
    penalty: Mapped[int] = col("pis_descuento_puntos", Integer, default=0)
    __table_args__ = (UniqueConstraint("pis_reto_id", "pis_orden"), CheckConstraint("pis_orden BETWEEN 1 AND 3"),)


class Assignment(Base):
    __tablename__ = "RETOS_GRUPOS"
    id: Mapped[UUID] = col("rgp_id", primary_key=True, default=uuid4)
    challenge_id: Mapped[UUID] = col("rgp_reto_id", ForeignKey("RETOS.ret_id", ondelete="CASCADE"))
    group_id: Mapped[UUID] = col("rgp_grupo_id", ForeignKey("GRUPOS.gru_id", ondelete="CASCADE"))
    __table_args__ = (UniqueConstraint("rgp_reto_id", "rgp_grupo_id"),)


class HintUse(Base):
    __tablename__ = "PISTAS_USADAS"
    id: Mapped[UUID] = col("pud_id", primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = col("pud_usuario_id", ForeignKey("USUARIOS.usu_id"))
    challenge_id: Mapped[UUID] = col("pud_reto_id", ForeignKey("RETOS.ret_id"))
    hint_id: Mapped[UUID] = col("pud_pista_id", ForeignKey("RETOS_PISTAS.pis_id"))
    penalty: Mapped[int] = col("pud_descuento", Integer, default=0)
    __table_args__ = (UniqueConstraint("pud_usuario_id", "pud_pista_id"),)


class Run(Base):
    __tablename__ = "CORRIDAS"
    id: Mapped[str] = col("cor_id", String(12), primary_key=True)
    challenge_id: Mapped[UUID] = col("cor_reto_id", ForeignKey("RETOS.ret_id"))
    user_id: Mapped[UUID] = col("cor_usuario_id", ForeignKey("USUARIOS.usu_id"))
    victim_id: Mapped[UUID] = col("cor_maquina_victima_id", ForeignKey("MAQUINAS_VIRTUALES.maq_id"))
    attacker_id: Mapped[UUID | None] = col("cor_maquina_atacante_id", ForeignKey("MAQUINAS_VIRTUALES.maq_id"))
    flag_hash: Mapped[str] = col("cor_flag_hash", String(64), default="")
    state: Mapped[str] = col("cor_estado", String(15), default="en_cola")
    outcome: Mapped[str | None] = col("cor_resultado", String(15))
    pilot: Mapped[bool] = col("cor_piloto", Boolean, default=False)
    connection_id: Mapped[str | None] = col("cor_conexion_externa", String(80))
    started: Mapped[datetime] = col("cor_iniciado_en", DateTime(timezone=True), server_default=func.now())
    expires: Mapped[datetime] = col("cor_expira_en", DateTime(timezone=True))
    finished: Mapped[datetime | None] = col("cor_finalizado_en", DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("cor_id ~ '^[a-f0-9]{12}$'"),
        CheckConstraint("cor_estado IN ('en_cola','reservada','activa','resuelta','expirada','cancelada','reiniciando','liberada')"),
        Index("uq_cor_reto_vivo", "cor_reto_id", unique=True, postgresql_where=text("cor_estado IN ('reservada','activa','reiniciando')")),
        Index("uq_cor_atacante_vivo", "cor_maquina_atacante_id", unique=True, postgresql_where=text("cor_estado IN ('reservada','activa','reiniciando') AND cor_maquina_atacante_id IS NOT NULL")),
        # Una víctima que requiere restauración no se comparte entre retos.
        Index("uq_cor_victima_viva", "cor_maquina_victima_id", unique=True, postgresql_where=text("cor_estado IN ('reservada','activa','reiniciando')")),
        Index("uq_cor_usuario_pendiente", "cor_usuario_id", "cor_reto_id", unique=True, postgresql_where=text("cor_estado IN ('en_cola','reservada','activa','reiniciando')")),
    )


class Attempt(Base):
    __tablename__ = "CORRIDAS_INTENTOS"
    id: Mapped[UUID] = col("int_id", primary_key=True, default=uuid4)
    run_id: Mapped[str] = col("int_corrida_id", ForeignKey("CORRIDAS.cor_id"))
    value_hash: Mapped[str] = col("int_valor_hash", String(64))
    correct: Mapped[bool] = col("int_resultado", Boolean)
    created: Mapped[datetime] = col("int_enviado_en", DateTime(timezone=True), server_default=func.now())


class Completion(Base):
    __tablename__ = "RETOS_COMPLETADOS"
    id: Mapped[UUID] = col("rcp_id", primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = col("rcp_usuario_id", ForeignKey("USUARIOS.usu_id"))
    challenge_id: Mapped[UUID] = col("rcp_reto_id", ForeignKey("RETOS.ret_id"))
    points: Mapped[int] = col("rcp_puntos", Integer)
    created: Mapped[datetime] = col("rcp_creado_en", DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("rcp_usuario_id", "rcp_reto_id"),)


class Ranking(Base):
    __tablename__ = "RANKING"
    user_id: Mapped[UUID] = col("ran_usuario_id", ForeignKey("USUARIOS.usu_id"), primary_key=True)
    points: Mapped[int] = col("ran_puntos_totales", Integer, default=0)
    completed: Mapped[int] = col("ran_retos_completados", Integer, default=0)
    updated: Mapped[datetime] = col("ran_actualizado_en", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Audit(Base):
    __tablename__ = "AUDITORIA"
    id: Mapped[UUID] = col("aud_id", primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = col("aud_usuario_id", ForeignKey("USUARIOS.usu_id"))
    action: Mapped[str] = col("aud_accion", String(60))
    entity: Mapped[str] = col("aud_entidad", String(40))
    entity_id: Mapped[str] = col("aud_entidad_id", String(60))
    details: Mapped[dict] = col("aud_detalle", JSONB, default=dict)
    created: Mapped[datetime] = col("aud_creado_en", DateTime(timezone=True), server_default=func.now())


class Maintenance(Base):
    __tablename__ = "MANTENIMIENTO_SNAPSHOTS"
    id: Mapped[UUID] = col("snp_id", primary_key=True, default=uuid4)
    machine_id: Mapped[UUID] = col("snp_maquina_id", ForeignKey("MAQUINAS_VIRTUALES.maq_id"))
    reason: Mapped[str] = col("snp_motivo", Text)
    state: Mapped[str] = col("snp_estado", String(15), default="pendiente")
    tested: Mapped[bool] = col("snp_prueba_aprobada", Boolean, default=False)
    created: Mapped[datetime] = col("snp_solicitado_en", DateTime(timezone=True), server_default=func.now())
    resolved: Mapped[datetime | None] = col("snp_resuelto_en", DateTime(timezone=True))
    resolver_id: Mapped[UUID | None] = col("snp_resuelto_por", ForeignKey("USUARIOS.usu_id"))
    __table_args__ = (CheckConstraint("snp_estado IN ('pendiente','en_proceso','confirmado')"),)
