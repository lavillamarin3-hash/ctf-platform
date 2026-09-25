# ============================================================
# ACCESO A DATOS
# Responsabilidad: crear el engine, sesiones y esquema inicial de PostgreSQL.
# ============================================================

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from .core import get_settings
from .models import Base


def make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(session_factory: async_sessionmaker[AsyncSession]) -> None:
    engine = session_factory.kw["bind"]
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        # Compatibilidad con volúmenes PostgreSQL ya existentes.
        await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(160)"))
        await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(160)"))
        await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS user_function VARCHAR(80)"))
        await connection.execute(text("ALTER TABLE challenges ADD COLUMN IF NOT EXISTS category VARCHAR(48) DEFAULT 'MISC'"))
        await connection.execute(text("ALTER TABLE challenges ADD COLUMN IF NOT EXISTS scenario VARCHAR(64)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenges_category ON challenges (category)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenges_scenario ON challenges (scenario)"))
        await connection.execute(text("ALTER TABLE laboratories ADD COLUMN IF NOT EXISTS code VARCHAR(64)"))
        await connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_laboratories_code ON laboratories (code) WHERE code IS NOT NULL"))
        await connection.execute(text("ALTER TABLE vm_assets ADD COLUMN IF NOT EXISTS network_role VARCHAR(64) DEFAULT 'Víctimas'"))
        await connection.execute(text("ALTER TABLE vm_assets ADD COLUMN IF NOT EXISTS subnet VARCHAR(64) DEFAULT '10.10.30.0/24'"))
        await connection.execute(text("ALTER TABLE vm_assets ADD COLUMN IF NOT EXISTS guacamole_connection_id VARCHAR(160)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_vm_assets_guacamole_connection_id ON vm_assets (guacamole_connection_id)"))
        await connection.execute(text("""
            CREATE TABLE IF NOT EXISTS challenge_instances (
                id SERIAL PRIMARY KEY,
                challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
                vm_asset_id INTEGER NOT NULL REFERENCES vm_assets(id) ON DELETE CASCADE,
                run_id INTEGER UNIQUE REFERENCES challenge_runs(id) ON DELETE SET NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                state VARCHAR(20) NOT NULL DEFAULT 'disponible',
                ip_address VARCHAR(64),
                guacamole_connection_id VARCHAR(160),
                reserved_at TIMESTAMPTZ,
                expires_at TIMESTAMPTZ,
                last_error VARCHAR(500),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenge_instances_challenge_state ON challenge_instances (challenge_id, state)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenge_instances_vm_asset_id ON challenge_instances (vm_asset_id)"))
        await connection.execute(text("ALTER TABLE challenge_flags ADD COLUMN IF NOT EXISTS mode VARCHAR(16) DEFAULT 'static'"))
        await connection.execute(text("ALTER TABLE challenge_flags ADD COLUMN IF NOT EXISTS template VARCHAR(512)"))
        await connection.execute(text("CREATE TABLE IF NOT EXISTS challenge_run_flags (id SERIAL PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES challenge_runs(id) ON DELETE CASCADE, flag_id INTEGER NOT NULL REFERENCES challenge_flags(id) ON DELETE CASCADE, flag_hash VARCHAR(512) NOT NULL, fingerprint VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, CONSTRAINT uq_run_flag UNIQUE (run_id, flag_id))"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenge_run_flags_run_id ON challenge_run_flags(run_id)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenge_run_flags_fingerprint ON challenge_run_flags(fingerprint)"))
        await connection.execute(text("CREATE TABLE IF NOT EXISTS student_groups (id SERIAL PRIMARY KEY, name VARCHAR(120) NOT NULL, code VARCHAR(64) NOT NULL, description VARCHAR(300) NOT NULL DEFAULT '', is_active BOOLEAN NOT NULL DEFAULT TRUE, guacamole_group_identifier VARCHAR(128), created_by INTEGER REFERENCES users(id), created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP)"))
        await connection.execute(text("ALTER TABLE student_groups ADD COLUMN IF NOT EXISTS guacamole_group_identifier VARCHAR(128)"))
        await connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_student_groups_guacamole_identifier ON student_groups(guacamole_group_identifier) WHERE guacamole_group_identifier IS NOT NULL"))
        await connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_student_group_name ON student_groups(name)"))
        await connection.execute(text("CREATE TABLE IF NOT EXISTS group_memberships (id SERIAL PRIMARY KEY, group_id INTEGER NOT NULL REFERENCES student_groups(id) ON DELETE CASCADE, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, CONSTRAINT uq_group_member UNIQUE(group_id,user_id))"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_group_memberships_group_id ON group_memberships(group_id)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_group_memberships_user_id ON group_memberships(user_id)"))
        await connection.execute(text("CREATE TABLE IF NOT EXISTS challenge_group_assignments (id SERIAL PRIMARY KEY, challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE, group_id INTEGER NOT NULL REFERENCES student_groups(id) ON DELETE CASCADE, created_by INTEGER REFERENCES users(id), created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, CONSTRAINT uq_challenge_group UNIQUE(challenge_id,group_id))"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenge_group_assignments_challenge_id ON challenge_group_assignments(challenge_id)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_challenge_group_assignments_group_id ON challenge_group_assignments(group_id)"))
