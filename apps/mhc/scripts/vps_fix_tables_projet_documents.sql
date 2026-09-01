-- Crée la table projet_voyage_documents si elle n'existe pas.
-- À exécuter sur le VPS si la migration 0d2e6a1b8c34 est "stampée" sans être exécutée
-- (colonne questionnaire_type déjà présente dans projets_voyage).
-- Usage : cat scripts/vps_fix_tables_projet_documents.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health

CREATE TABLE IF NOT EXISTS projet_voyage_documents (
    id SERIAL PRIMARY KEY,
    projet_voyage_id INTEGER NOT NULL REFERENCES projets_voyage(id) ON DELETE CASCADE,
    doc_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    bucket_name VARCHAR(63) NOT NULL,
    object_name VARCHAR(512) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    minio_etag VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_projet_voyage_documents_id ON projet_voyage_documents (id);
CREATE INDEX IF NOT EXISTS ix_projet_voyage_documents_projet_voyage_id ON projet_voyage_documents (projet_voyage_id);
CREATE INDEX IF NOT EXISTS ix_projet_voyage_documents_doc_type ON projet_voyage_documents (doc_type);
