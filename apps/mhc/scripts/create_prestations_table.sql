-- Créer la table prestations si elle n'existe pas
-- Pour créer TOUTES les tables (prestations + invoices + invoice_items), exécuter plutôt :
--   scripts/vps_fix_tables_invoices.sql

CREATE TABLE IF NOT EXISTS prestations (
    id SERIAL PRIMARY KEY,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    sinistre_id INTEGER REFERENCES sinistres(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    code_prestation VARCHAR(50) NOT NULL,
    libelle VARCHAR(200) NOT NULL,
    description TEXT,
    montant_unitaire NUMERIC(10, 2) NOT NULL,
    quantite INTEGER NOT NULL DEFAULT 1,
    montant_total NUMERIC(10, 2) NOT NULL,
    date_prestation TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    statut VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_prestations_id ON prestations (id);
CREATE INDEX IF NOT EXISTS ix_prestations_hospital_id ON prestations (hospital_id);
CREATE INDEX IF NOT EXISTS ix_prestations_sinistre_id ON prestations (sinistre_id);
CREATE INDEX IF NOT EXISTS ix_prestations_user_id ON prestations (user_id);
CREATE INDEX IF NOT EXISTS ix_prestations_code_prestation ON prestations (code_prestation);
CREATE INDEX IF NOT EXISTS ix_prestations_statut ON prestations (statut);
