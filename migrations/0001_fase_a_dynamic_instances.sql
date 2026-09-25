-- FASE A: pool de instancias reutilizables para banderas dinámicas.
-- La plataforma actual utiliza INTEGER; por eso se adapta el diseño del
-- documento 20 sin crear una segunda tabla challenges/users.

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_challenge_instances_challenge_state
    ON challenge_instances (challenge_id, state);

CREATE INDEX IF NOT EXISTS ix_challenge_instances_vm_asset_id
    ON challenge_instances (vm_asset_id);
