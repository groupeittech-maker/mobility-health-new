-- À exécuter sur le VPS si "alembic upgrade head" échoue avec: relation "sinistres" does not exist
-- Crée alertes puis sinistres (sinistre_process_steps en dépend).
-- Usage: cat scripts/vps_fix_tables_sinistres.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health

-- 1. alertes (requise par sinistres)
CREATE TABLE IF NOT EXISTS alertes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    souscription_id INTEGER REFERENCES souscriptions(id) ON DELETE SET NULL,
    numero_alerte VARCHAR(100) NOT NULL UNIQUE,
    latitude NUMERIC(10, 8) NOT NULL,
    longitude NUMERIC(11, 8) NOT NULL,
    adresse VARCHAR(500),
    description TEXT,
    statut VARCHAR(20) NOT NULL DEFAULT 'en_attente',
    priorite VARCHAR(20) NOT NULL DEFAULT 'normale',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_alertes_id ON alertes (id);
CREATE INDEX IF NOT EXISTS ix_alertes_user_id ON alertes (user_id);
CREATE INDEX IF NOT EXISTS ix_alertes_souscription_id ON alertes (souscription_id);
CREATE INDEX IF NOT EXISTS ix_alertes_numero_alerte ON alertes (numero_alerte);
CREATE INDEX IF NOT EXISTS ix_alertes_statut ON alertes (statut);

-- 2. sinistres
CREATE TABLE IF NOT EXISTS sinistres (
    id SERIAL PRIMARY KEY,
    alerte_id INTEGER NOT NULL REFERENCES alertes(id) ON DELETE CASCADE,
    souscription_id INTEGER REFERENCES souscriptions(id) ON DELETE SET NULL,
    hospital_id INTEGER REFERENCES hospitals(id) ON DELETE SET NULL,
    numero_sinistre VARCHAR(100) UNIQUE,
    description TEXT,
    statut VARCHAR(20) NOT NULL DEFAULT 'en_cours',
    agent_sinistre_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    medecin_referent_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sinistres_id ON sinistres (id);
CREATE INDEX IF NOT EXISTS ix_sinistres_alerte_id ON sinistres (alerte_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_souscription_id ON sinistres (souscription_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_hospital_id ON sinistres (hospital_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_numero_sinistre ON sinistres (numero_sinistre);
CREATE INDEX IF NOT EXISTS ix_sinistres_statut ON sinistres (statut);
CREATE INDEX IF NOT EXISTS ix_sinistres_agent_sinistre_id ON sinistres (agent_sinistre_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_medecin_referent_id ON sinistres (medecin_referent_id);
