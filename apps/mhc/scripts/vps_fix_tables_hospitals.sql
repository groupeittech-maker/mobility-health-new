-- À exécuter sur le VPS si "alembic upgrade head" échoue avec: relation "hospitals" does not exist
-- Usage: cat scripts/vps_fix_tables_hospitals.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health

CREATE TABLE IF NOT EXISTS hospitals (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(200) NOT NULL,
    adresse VARCHAR(500),
    ville VARCHAR(100),
    pays VARCHAR(100),
    code_postal VARCHAR(20),
    telephone VARCHAR(50),
    email VARCHAR(255),
    latitude NUMERIC(10, 8) NOT NULL DEFAULT 0,
    longitude NUMERIC(11, 8) NOT NULL DEFAULT 0,
    est_actif BOOLEAN NOT NULL DEFAULT true,
    specialites TEXT,
    capacite_lits INTEGER,
    notes TEXT,
    medecin_referent_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_hospitals_id ON hospitals (id);
CREATE INDEX IF NOT EXISTS ix_hospitals_nom ON hospitals (nom);
CREATE INDEX IF NOT EXISTS ix_hospitals_medecin_referent_id ON hospitals (medecin_referent_id);
