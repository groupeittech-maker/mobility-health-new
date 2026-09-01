-- Tables manquantes pour la migration 2c3b1a84b0e4 (Add validation metadata and invoice link to hospital stays).
-- À exécuter sur le VPS si alembic échoue avec: relation "invoices" does not exist
--
-- Prérequis : users, hospitals, sinistres doivent exister (vps_fix_tables_before_alembic.sql déjà exécuté).
-- Usage : cat scripts/vps_fix_tables_invoices.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health

-- 1. prestations (dépend de hospitals, sinistres, users)
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

-- 2. invoices (sans hospital_stay_id : la migration 2c3b1a84b0e4 l’ajoute)
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE RESTRICT,
    numero_facture VARCHAR(100) NOT NULL UNIQUE,
    montant_ht NUMERIC(12, 2) NOT NULL,
    montant_tva NUMERIC(12, 2) NOT NULL DEFAULT 0,
    montant_ttc NUMERIC(12, 2) NOT NULL,
    date_facture TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    date_echeance TIMESTAMP WITHOUT TIME ZONE,
    statut VARCHAR(30) NOT NULL DEFAULT 'draft',
    validation_medicale VARCHAR(20),
    validation_medicale_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
    validation_medicale_date TIMESTAMP WITHOUT TIME ZONE,
    validation_medicale_notes TEXT,
    validation_sinistre VARCHAR(20),
    validation_sinistre_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
    validation_sinistre_date TIMESTAMP WITHOUT TIME ZONE,
    validation_sinistre_notes TEXT,
    validation_compta VARCHAR(20),
    validation_compta_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
    validation_compta_date TIMESTAMP WITHOUT TIME ZONE,
    validation_compta_notes TEXT,
    notes TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_invoices_id ON invoices (id);
CREATE INDEX IF NOT EXISTS ix_invoices_hospital_id ON invoices (hospital_id);
CREATE INDEX IF NOT EXISTS ix_invoices_numero_facture ON invoices (numero_facture);
CREATE INDEX IF NOT EXISTS ix_invoices_statut ON invoices (statut);
CREATE INDEX IF NOT EXISTS ix_invoices_validation_medicale ON invoices (validation_medicale);
CREATE INDEX IF NOT EXISTS ix_invoices_validation_sinistre ON invoices (validation_sinistre);
CREATE INDEX IF NOT EXISTS ix_invoices_validation_compta ON invoices (validation_compta);

-- 3. invoice_items (dépend de invoices, prestations)
CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    prestation_id INTEGER REFERENCES prestations(id) ON DELETE SET NULL,
    libelle VARCHAR(200) NOT NULL,
    quantite INTEGER NOT NULL DEFAULT 1,
    prix_unitaire NUMERIC(10, 2) NOT NULL,
    montant_ht NUMERIC(10, 2) NOT NULL,
    taux_tva NUMERIC(5, 2) NOT NULL DEFAULT 0,
    montant_ttc NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_invoice_items_id ON invoice_items (id);
CREATE INDEX IF NOT EXISTS ix_invoice_items_invoice_id ON invoice_items (invoice_id);
CREATE INDEX IF NOT EXISTS ix_invoice_items_prestation_id ON invoice_items (prestation_id);
