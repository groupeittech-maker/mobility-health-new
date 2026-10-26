-- ================================================================
-- SEED : chaîne sinistre + facture hospitalière de démo
-- Objet : tester le workflow Factures hospitalières
--   (pôle médical → pôle sinistre → comptabilité)
-- Idempotent : vérifie les numéros avant insertion.
-- ================================================================

BEGIN;

-- 0) Table invoice_items — présente dans le modèle ORM mais pas migrée
CREATE TABLE IF NOT EXISTS invoice_items (
    id              SERIAL PRIMARY KEY,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    prestation_id   INTEGER REFERENCES prestations(id) ON DELETE SET NULL,
    libelle         VARCHAR(200) NOT NULL,
    quantite        INTEGER NOT NULL DEFAULT 1,
    prix_unitaire   NUMERIC(10,2) NOT NULL,
    montant_ht      NUMERIC(10,2) NOT NULL,
    taux_tva        NUMERIC(5,2)  NOT NULL DEFAULT 0,
    montant_ttc     NUMERIC(10,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_invoice_items_invoice_id ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS ix_invoice_items_prestation_id ON invoice_items(prestation_id);

-- 1) Assuré démo (patient du sinistre)
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at)
SELECT 'assure.demo@mhc.demo', 'assure.demo', '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Assuré Démo', 'user', true, false, true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'assure.demo@mhc.demo');

-- 2) Alerte SOS
INSERT INTO alertes (user_id, numero_alerte, latitude, longitude, adresse, description, statut, priorite, assigned_role, assigned_at, created_at, updated_at)
SELECT (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       'ALT-2026-DEMO1', 5.34531700, -4.02442900, 'Treichville, Abidjan, Côte d''Ivoire',
       'Malaise grave — transporté au CHU de Treichville', 'en_cours', 'haute', 'alerte_sos', NOW(), NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM alertes WHERE numero_alerte = 'ALT-2026-DEMO1');

-- 3) Sinistre (rattaché à l'alerte + hôpital CHU de Treichville id=1)
INSERT INTO sinistres (alerte_id, souscription_id, hospital_id, numero_sinistre, description, statut, agent_sinistre_id, created_at, updated_at)
SELECT (SELECT id FROM alertes WHERE numero_alerte = 'ALT-2026-DEMO1'),
       NULL, 1, 'SIN-2026-DEMO1',
       'Hospitalisation suite alerte SOS Abidjan', 'en_cours',
       (SELECT id FROM users WHERE email = 'agent.sinistre@mhc.demo'),
       NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1');

-- 4) Séjour hospitalier
INSERT INTO hospital_stays (sinistre_id, hospital_id, patient_id, status, report_status, service_concerne, chambre, started_at, created_at, updated_at)
SELECT (SELECT id FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1'),
       1, (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       'in_progress', 'submitted', 'Urgences', 'B-214', NOW() - interval '2 days', NOW(), NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM hospital_stays hs
    JOIN sinistres s ON s.id = hs.sinistre_id
    WHERE s.numero_sinistre = 'SIN-2026-DEMO1'
);

-- 5) Prestations facturables (statut pending → rattachées à la facture)
INSERT INTO prestations (hospital_id, sinistre_id, user_id, code_prestation, libelle, description, montant_unitaire, quantite, montant_total, date_prestation, statut, created_at)
SELECT 1, (SELECT id FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1'),
       (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       'CONS-URG', 'Consultation urgences', 'Prise en charge initiale + constantes',
       15000, 1, 15000, NOW() - interval '2 days', 'invoiced', NOW()
WHERE NOT EXISTS (SELECT 1 FROM prestations p JOIN sinistres s ON s.id = p.sinistre_id WHERE s.numero_sinistre = 'SIN-2026-DEMO1' AND p.code_prestation = 'CONS-URG');

INSERT INTO prestations (hospital_id, sinistre_id, user_id, code_prestation, libelle, description, montant_unitaire, quantite, montant_total, date_prestation, statut, created_at)
SELECT 1, (SELECT id FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1'),
       (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       'SEJ-URG-2J', 'Hospitalisation 2 nuits', 'Chambre + soins infirmiers',
       45000, 2, 90000, NOW() - interval '2 days', 'invoiced', NOW()
WHERE NOT EXISTS (SELECT 1 FROM prestations p JOIN sinistres s ON s.id = p.sinistre_id WHERE s.numero_sinistre = 'SIN-2026-DEMO1' AND p.code_prestation = 'SEJ-URG-2J');

-- 6) Facture : HT 105 000, TVA 20 %, TTC 126 000 — accord médical déjà donné
INSERT INTO invoices (hospital_id, hospital_stay_id, numero_facture, montant_ht, montant_tva, montant_ttc,
                      date_facture, date_echeance, statut,
                      validation_medicale, validation_medicale_par, validation_medicale_date, validation_medicale_notes,
                      validation_sinistre, validation_compta, notes, created_at, updated_at)
SELECT 1,
       (SELECT hs.id FROM hospital_stays hs JOIN sinistres s ON s.id = hs.sinistre_id WHERE s.numero_sinistre = 'SIN-2026-DEMO1'),
       'INV-1-20261013-DEMO1',
       105000.00, 21000.00, 126000.00,
       NOW() - interval '1 day', NOW() + interval '29 days', 'pending_sinistre',
       'approved', (SELECT id FROM users WHERE email = 'medecin.conseil@mhc.demo'), NOW() - interval '1 day', 'Accord médical conforme au dossier.',
       'pending', NULL, 'Facture de démonstration — workflow sinistre',
       NOW() - interval '1 day', NOW()
WHERE NOT EXISTS (SELECT 1 FROM invoices WHERE numero_facture = 'INV-1-20261013-DEMO1');

-- 7) Lignes de facture
INSERT INTO invoice_items (invoice_id, prestation_id, libelle, quantite, prix_unitaire, montant_ht, taux_tva, montant_ttc)
SELECT i.id, p.id, p.libelle, p.quantite, p.montant_unitaire, p.montant_total, 0.20, p.montant_total * 1.2
FROM invoices i
JOIN sinistres s ON s.numero_sinistre = 'SIN-2026-DEMO1'
JOIN prestations p ON p.sinistre_id = s.id AND p.code_prestation IN ('CONS-URG', 'SEJ-URG-2J')
WHERE i.numero_facture = 'INV-1-20261013-DEMO1'
  AND NOT EXISTS (SELECT 1 FROM invoice_items ii WHERE ii.invoice_id = i.id);

-- 8) Historique de la facture
INSERT INTO invoice_history (invoice_id, action, previous_status, new_status, previous_stage, new_stage, actor_id, notes, created_at)
SELECT i.id, 'invoice_created', NULL, 'pending_medical', NULL, 'medical',
       (SELECT id FROM users WHERE email = 'admin@mhc.com'), 'Facture créée par l''hôpital.', NOW() - interval '1 day'
FROM invoices i WHERE i.numero_facture = 'INV-1-20261013-DEMO1'
  AND NOT EXISTS (SELECT 1 FROM invoice_history h WHERE h.invoice_id = i.id);

INSERT INTO invoice_history (invoice_id, action, previous_status, new_status, previous_stage, new_stage, actor_id, notes, created_at)
SELECT i.id, 'medical_approved', 'pending_medical', 'pending_sinistre', 'medical', 'sinistre',
       (SELECT id FROM users WHERE email = 'medecin.conseil@mhc.demo'), 'Accord médical conforme au dossier.', NOW() - interval '1 day'
FROM invoices i WHERE i.numero_facture = 'INV-1-20261013-DEMO1'
  AND (SELECT COUNT(*) FROM invoice_history h WHERE h.invoice_id = i.id) = 1;

COMMIT;
