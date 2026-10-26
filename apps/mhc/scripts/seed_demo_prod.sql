-- ================================================================
-- SEED PROD : comptes démo @mhc.demo + chaîne de démonstration
-- Adapté aux IDs réels de la prod (hôpital, assureur, courtier, produits).
-- Mot de passe pour tous les comptes : mh@123
-- Idempotent : ON CONFLICT / NOT EXISTS partout.
-- ================================================================

BEGIN;

-- ----------------------------------------------------------------
-- 0) Ancres prod (IDs réels résolus dynamiquement)
--    hôpital   : premier hôpital existant (Polyclinique Internationale)
--    assureur  : NSIA Congo (id 2) — sinon le premier assureur
--    courtier  : premier courtier (IT-tech)
--    produit   : produits existants des assureurs correspondants
-- ----------------------------------------------------------------

-- Réassureur démo si aucun
INSERT INTO reassureurs (nom, code, pays, ville, email, est_actif, cession_defaut_pct, commission_cession_defaut_pct, created_at, updated_at)
SELECT 'Africa Re', 'AFRICARE', 'Côte d''Ivoire', 'Abidjan', 'contact@africare.demo', true, 40, 10, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM reassureurs);

-- ----------------------------------------------------------------
-- 1) UTILISATEURS DÉMO — INTERNES MHC
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('sup.technique@mhc.demo',      'sup.technique',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Superviseur Technique',        'superviseur_technique',          true, false, true, NOW(), NOW()),
    ('agent.production@mhc.demo',   'agent.production.demo',   '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Production',             'production_agent',               true, false, true, NOW(), NOW()),
    ('conformite.prod@mhc.demo',    'conformite.prod',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Production',  'agent_conformite_production',    true, false, true, NOW(), NOW()),
    ('agent.sinistre@mhc.demo',     'agent.sinistre',     '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Sinistre',               'agent_sinistre_mh',              true, false, true, NOW(), NOW()),
    ('conformite.sinistre@mhc.demo','conformite.sinistre','$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Sinistre',    'agent_conformite_sinistre',      true, false, true, NOW(), NOW()),
    ('sup.medical@mhc.demo',        'sup.medical',        '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Superviseur Affaires Médicales','superviseur_affaires_medicales',true, false, true, NOW(), NOW()),
    ('agent.medical@mhc.demo',      'agent.medical',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Médical MHC',            'agent_medical_mhc',              true, false, true, NOW(), NOW()),
    ('conformite.medical@mhc.demo', 'conformite.medical', '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Médical',     'agent_conformite_medical',       true, false, true, NOW(), NOW()),
    ('medecin.conseil@mhc.demo',    'medecin.conseil',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Dr Konan — Médecin-conseil',   'medecin_referent_mh',            true, false, true, NOW(), NOW()),
    ('sup.comptable@mhc.demo',      'sup.comptable',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Superviseur Comptable',        'superviseur_comptable',          true, false, true, NOW(), NOW()),
    ('agent.comptable@mhc.demo',    'agent.comptable',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Comptable MH',           'agent_comptable_mh',             true, false, true, NOW(), NOW()),
    ('conformite.compta@mhc.demo',  'conformite.compta',  '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Comptable',   'agent_conformite_comptable',     true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- ----------------------------------------------------------------
-- 2) UTILISATEURS DÉMO — EXTERNES ASSUREUR (liés à NSIA Congo = premier assureur NSIA, sinon 1er)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('prod.assureur@mhc.demo',      'prod.assureur',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Production NSIA',        'agent_production_assureur',      true, false, true, NOW(), NOW()),
    ('sinistre.assureur@mhc.demo',  'sinistre.assureur',  '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Sinistre NSIA',          'agent_sinistre_assureur',        true, false, true, NOW(), NOW()),
    ('compta.assureur@mhc.demo',    'compta.assureur',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Comptable NSIA',         'agent_comptable_assureur',       true, false, true, NOW(), NOW()),
    ('medical.assureur@mhc.demo',   'medical.assureur',   '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Médical NSIA',           'agent_medical_assureur',         true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO assureur_agents (assureur_id, user_id, type_agent, created_at, updated_at)
SELECT a.id, u.id, v.t, NOW(), NOW()
FROM users u
JOIN (VALUES
    ('prod.assureur@mhc.demo',     'production'),
    ('sinistre.assureur@mhc.demo', 'sinistre'),
    ('compta.assureur@mhc.demo',   'comptable'),
    ('medical.assureur@mhc.demo',  'medical')
) AS v(email, t) ON u.email = v.email
CROSS JOIN LATERAL (
    SELECT id FROM assureurs WHERE nom ILIKE 'NSIA%' ORDER BY id LIMIT 1
) a
ON CONFLICT ON CONSTRAINT uq_assureur_agent_user DO NOTHING;

-- ----------------------------------------------------------------
-- 3) UTILISATEURS DÉMO — COURTIER (premier courtier = IT-tech)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('prod.courtier@mhc.demo',      'prod.courtier',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Production Courtier',    'agent_production_courtier',      true, false, true, NOW(), NOW()),
    ('assistant.souscr@mhc.demo',   'assistant.souscr',   '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Assistant Souscription',       'assistant_souscription',         true, false, true, NOW(), NOW()),
    ('sinistre.courtier@mhc.demo',  'sinistre.courtier',  '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Sinistre Courtier',      'agent_sinistre_courtier',        true, false, true, NOW(), NOW()),
    ('compta.courtier@mhc.demo',    'compta.courtier',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Comptable Courtier',     'agent_comptable_courtier',       true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO courtier_agents (courtier_id, user_id, type_agent, created_at, updated_at)
SELECT c.id, u.id, v.t, NOW(), NOW()
FROM users u
JOIN (VALUES
    ('prod.courtier@mhc.demo',     'production'),
    ('assistant.souscr@mhc.demo',  'souscription'),
    ('sinistre.courtier@mhc.demo', 'sinistre')
) AS v(email, t) ON u.email = v.email
CROSS JOIN LATERAL (
    SELECT id FROM courtiers ORDER BY id LIMIT 1
) c
ON CONFLICT ON CONSTRAINT uq_courtier_agent_user DO NOTHING;

UPDATE courtiers SET agent_comptable_id = (SELECT id FROM users WHERE email = 'compta.courtier@mhc.demo')
WHERE id = (SELECT id FROM courtiers ORDER BY id LIMIT 1);

-- ----------------------------------------------------------------
-- 4) EXTERNE — RÉASSUREUR (Africa Re créée ci-dessus)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, reassureur_id, created_at, updated_at)
SELECT 'verif.reassureur@mhc.demo', 'verif.reassureur', '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Vérificateur Africa Re', 'agent_verificateur_reassureur', true, false, true,
       (SELECT id FROM reassureurs WHERE nom = 'Africa Re' LIMIT 1), NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'verif.reassureur@mhc.demo');

-- ----------------------------------------------------------------
-- 5) PARTENAIRES SANTÉ (liés au premier hôpital prod)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, hospital_id, created_at, updated_at)
SELECT v.email, v.username, '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', v.full_name, v.role, true, false, true,
       (SELECT id FROM hospitals ORDER BY id LIMIT 1), NOW(), NOW()
FROM (VALUES
    ('admin.hopital@mhc.demo',      'admin.hopital',      'Admin Polyclinique',          'hospital_admin'),
    ('medecin.hopital@mhc.demo',    'medecin.hopital.demo',    'Dr Traoré Polyclinique',      'medecin_hopital'),
    ('reception.hopital@mhc.demo',  'reception.hopital.demo',  'Agent Réception Polyclinique','agent_reception_hopital'),
    ('compta.hopital@mhc.demo',     'compta.hopital',     'Agent Comptable Polyclinique','agent_comptable_hopital')
) AS v(email, username, full_name, role)
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.email = v.email);

-- Médecin-conseil référent de l'hôpital
UPDATE hospitals SET medecin_referent_id = (SELECT id FROM users WHERE email = 'medecin.conseil@mhc.demo')
WHERE id = (SELECT id FROM hospitals ORDER BY id LIMIT 1)
  AND medecin_referent_id IS NULL;

-- ----------------------------------------------------------------
-- 6) ASSURÉ DÉMO (client final mobile)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, date_naissance, telephone, sexe, pays_residence, created_at, updated_at)
SELECT 'assure.demo@mhc.demo', 'assure.demo', '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Assuré Démo', 'user', true, false, true,
       '1990-05-12'::date, '+2250707112233', 'M', 'CI', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'assure.demo@mhc.demo');

-- Docteur legacy (dashboard dédié, pas de back-office)
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at)
SELECT 'doctor.demo@mhc.demo', 'doctor.demo', '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Docteur Démo', 'doctor', true, false, true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'doctor.demo@mhc.demo');

-- ----------------------------------------------------------------
-- 7) CHAÎNE FINANCIÈRE DE DÉMO — souscriptions + paiements + attestations
--    produit cible : premier produit de l'assureur NSIA
-- ----------------------------------------------------------------
INSERT INTO souscriptions (user_id, produit_assurance_id, numero_souscription, prix_applique,
                           prime_assurance, cout_police, frais_services, taxes, taxes_total,
                           canal_distribution, courtier_id, date_debut, date_fin, statut,
                           validation_medicale, validation_technique, validation_finale,
                           created_at, updated_at)
SELECT u.id,
       (SELECT p.id FROM produits_assurance p
        JOIN assureurs a ON a.id = p.assureur_id AND a.nom ILIKE 'NSIA%'
        ORDER BY p.id LIMIT 1),
       'SOU-2026-DEMO1', 85000, 65000, 5000, 15000, '[]'::json, 0,
       'direct', NULL, NOW() - interval '30 days', NOW() + interval '11 months', 'active',
       'approved', 'approved', 'approved', NOW() - interval '30 days', NOW()
FROM users u WHERE u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM souscriptions WHERE numero_souscription = 'SOU-2026-DEMO1');

INSERT INTO paiements (souscription_id, user_id, montant, type_paiement, statut, date_paiement,
                       reference_transaction, reference_externe, notes, created_at, updated_at)
SELECT s.id, u.id, 85000, 'MOBILE_MONEY_ORANGE', 'VALIDE', NOW() - interval '29 days',
       'OM-88231-TRX-9041', 'ORANGE-MONEY-CI', 'Paiement prime souscription démo 1', NOW(), NOW()
FROM souscriptions s, users u
WHERE s.numero_souscription = 'SOU-2026-DEMO1' AND u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM paiements p WHERE p.reference_transaction = 'OM-88231-TRX-9041');

INSERT INTO attestations (souscription_id, paiement_id, type_attestation, numero_attestation,
                          chemin_fichier_minio, bucket_minio, est_valide, created_at, updated_at)
SELECT s.id, p.id, 'definitive', 'ATT-DEF-2026-0001',
       'attestations/ATT-DEF-2026-0001.pdf', 'mhc-documents', true, NOW(), NOW()
FROM souscriptions s
JOIN paiements p ON p.souscription_id = s.id AND p.reference_transaction = 'OM-88231-TRX-9041'
WHERE s.numero_souscription = 'SOU-2026-DEMO1'
  AND NOT EXISTS (SELECT 1 FROM attestations WHERE numero_attestation = 'ATT-DEF-2026-0001');

-- SOU-2026-DEMO2 — via courtier (reçu provisoire)
INSERT INTO souscriptions (user_id, produit_assurance_id, numero_souscription, prix_applique,
                           prime_assurance, cout_police, frais_services, taxes, taxes_total,
                           canal_distribution, courtier_id, date_debut, date_fin, statut,
                           validation_medicale, validation_technique, validation_finale,
                           created_at, updated_at)
SELECT u.id, (SELECT id FROM produits_assurance ORDER BY id LIMIT 1),
       'SOU-2026-DEMO2', 120000, 95000, 5000, 20000, '[]'::json, 0,
       'courtier', (SELECT id FROM courtiers ORDER BY id LIMIT 1),
       NOW() - interval '10 days', NOW() + interval '355 days', 'active',
       'approved', 'approved', 'approved', NOW() - interval '10 days', NOW()
FROM users u WHERE u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM souscriptions WHERE numero_souscription = 'SOU-2026-DEMO2');

INSERT INTO paiements (souscription_id, user_id, montant, type_paiement, statut, date_paiement,
                       reference_transaction, reference_externe, notes, created_at, updated_at)
SELECT s.id, u.id, 120000, 'ESPECES', 'VALIDE', NOW() - interval '9 days',
       'CASH-KOFFI-1024', 'CAISSE-COURTIER', 'Prime encaissée au cabinet', NOW(), NOW()
FROM souscriptions s, users u
WHERE s.numero_souscription = 'SOU-2026-DEMO2' AND u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM paiements p WHERE p.reference_transaction = 'CASH-KOFFI-1024');

INSERT INTO attestations (souscription_id, paiement_id, type_attestation, numero_attestation,
                          chemin_fichier_minio, bucket_minio, est_valide, created_at, updated_at)
SELECT s.id, p.id, 'provisoire', 'ATT-PROV-2026-0001',
       'attestations/ATT-PROV-2026-0001.pdf', 'mhc-documents', true, NOW(), NOW()
FROM souscriptions s
JOIN paiements p ON p.souscription_id = s.id AND p.reference_transaction = 'CASH-KOFFI-1024'
WHERE s.numero_souscription = 'SOU-2026-DEMO2'
  AND NOT EXISTS (SELECT 1 FROM attestations WHERE numero_attestation = 'ATT-PROV-2026-0001');

-- SOU-2026-DEMO3 — remboursée (refus du dossier)
INSERT INTO souscriptions (user_id, produit_assurance_id, numero_souscription, prix_applique,
                           prime_assurance, cout_police, frais_services, taxes, taxes_total,
                           canal_distribution, courtier_id, date_debut, date_fin, statut,
                           validation_medicale, validation_technique, validation_finale,
                           created_at, updated_at)
SELECT u.id, (SELECT id FROM produits_assurance ORDER BY id DESC LIMIT 1),
       'SOU-2026-DEMO3', 60000, 45000, 5000, 10000, '[]'::json, 0,
       'direct', NULL, NOW() - interval '20 days', NOW() + interval '11 months', 'refusee',
       'rejected', 'approved', 'rejected', NOW() - interval '20 days', NOW()
FROM users u WHERE u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM souscriptions WHERE numero_souscription = 'SOU-2026-DEMO3');

INSERT INTO paiements (souscription_id, user_id, montant, type_paiement, statut, date_paiement,
                       reference_transaction, reference_externe, notes, created_at, updated_at)
SELECT s.id, u.id, -60000, 'VIREMENT', 'VALIDE', NOW() - interval '5 days',
       'REMBOURS-DEMO3', 'BANQUE-MHC', 'Remboursement suite refus dossier', NOW(), NOW()
FROM souscriptions s, users u
WHERE s.numero_souscription = 'SOU-2026-DEMO3' AND u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM paiements p WHERE p.reference_transaction = 'REMBOURS-DEMO3');

-- ----------------------------------------------------------------
-- 8) CHAÎNE SINISTRE DE DÉMO — alerte → sinistre → séjour → facture
--    hôpital : premier hôpital prod ; médecin assigné : medecin.hopital
-- ----------------------------------------------------------------

-- Alerte SOS
INSERT INTO alertes (user_id, numero_alerte, latitude, longitude, adresse, description, statut, priorite, assigned_role, assigned_at, created_at, updated_at)
SELECT (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       'ALT-2026-DEMO1', 5.34531700, -4.02442900, 'Abidjan, Côte d''Ivoire',
       'Malaise grave — transporté en urgence', 'en_cours', 'haute', 'alerte_sos', NOW(), NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM alertes WHERE numero_alerte = 'ALT-2026-DEMO1');

-- Sinistre rattaché à l'alerte + hôpital + souscription démo
INSERT INTO sinistres (alerte_id, souscription_id, hospital_id, numero_sinistre, description, statut, agent_sinistre_id, created_at, updated_at)
SELECT (SELECT id FROM alertes WHERE numero_alerte = 'ALT-2026-DEMO1'),
       (SELECT id FROM souscriptions WHERE numero_souscription = 'SOU-2026-DEMO1'),
       (SELECT id FROM hospitals ORDER BY id LIMIT 1),
       'SIN-2026-DEMO1',
       'Hospitalisation suite alerte SOS', 'en_cours',
       (SELECT id FROM users WHERE email = 'agent.sinistre@mhc.demo'),
       NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1');

-- Lier la souscription au sinistre (sinistre déjà existant sans souscription → rattacher)
UPDATE sinistres SET souscription_id = (SELECT id FROM souscriptions WHERE numero_souscription = 'SOU-2026-DEMO1'),
                     updated_at = NOW()
WHERE numero_sinistre = 'SIN-2026-DEMO1' AND souscription_id IS NULL;

-- Séjour hospitalier (médecin assigné = medecin.hopital)
INSERT INTO hospital_stays (sinistre_id, hospital_id, patient_id, assigned_doctor_id, status, report_status, service_concerne, chambre, started_at, created_at, updated_at)
SELECT (SELECT id FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1'),
       (SELECT id FROM hospitals ORDER BY id LIMIT 1),
       (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       (SELECT id FROM users WHERE email = 'medecin.hopital@mhc.demo'),
       'in_progress', 'submitted', 'Urgences', 'B-214', NOW() - interval '2 days', NOW(), NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM hospital_stays hs
    JOIN sinistres s ON s.id = hs.sinistre_id
    WHERE s.numero_sinistre = 'SIN-2026-DEMO1'
);

-- Assigner le médecin si le séjour existait sans docteur
UPDATE hospital_stays SET assigned_doctor_id = (SELECT id FROM users WHERE email = 'medecin.hopital@mhc.demo'), updated_at = NOW()
WHERE assigned_doctor_id IS NULL
  AND sinistre_id = (SELECT id FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1');

-- Prestations facturables
INSERT INTO prestations (hospital_id, sinistre_id, user_id, code_prestation, libelle, description, montant_unitaire, quantite, montant_total, date_prestation, statut, created_at)
SELECT (SELECT id FROM hospitals ORDER BY id LIMIT 1), (SELECT id FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1'),
       (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       'CONS-URG', 'Consultation urgences', 'Prise en charge initiale + constantes',
       15000, 1, 15000, NOW() - interval '2 days', 'invoiced', NOW()
WHERE NOT EXISTS (SELECT 1 FROM prestations p JOIN sinistres s ON s.id = p.sinistre_id WHERE s.numero_sinistre = 'SIN-2026-DEMO1' AND p.code_prestation = 'CONS-URG');

INSERT INTO prestations (hospital_id, sinistre_id, user_id, code_prestation, libelle, description, montant_unitaire, quantite, montant_total, date_prestation, statut, created_at)
SELECT (SELECT id FROM hospitals ORDER BY id LIMIT 1), (SELECT id FROM sinistres WHERE numero_sinistre = 'SIN-2026-DEMO1'),
       (SELECT id FROM users WHERE email = 'assure.demo@mhc.demo'),
       'SEJ-URG-2J', 'Hospitalisation 2 nuits', 'Chambre + soins infirmiers',
       45000, 2, 90000, NOW() - interval '2 days', 'invoiced', NOW()
WHERE NOT EXISTS (SELECT 1 FROM prestations p JOIN sinistres s ON s.id = p.sinistre_id WHERE s.numero_sinistre = 'SIN-2026-DEMO1' AND p.code_prestation = 'SEJ-URG-2J');

-- Facture : HT 105 000, TVA 20 %, TTC 126 000 — accord médical déjà donné
INSERT INTO invoices (hospital_id, hospital_stay_id, numero_facture, montant_ht, montant_tva, montant_ttc,
                      date_facture, date_echeance, statut,
                      validation_medicale, validation_medicale_par, validation_medicale_date, validation_medicale_notes,
                      validation_sinistre, validation_compta, notes, created_at, updated_at)
SELECT (SELECT id FROM hospitals ORDER BY id LIMIT 1),
       (SELECT hs.id FROM hospital_stays hs JOIN sinistres s ON s.id = hs.sinistre_id WHERE s.numero_sinistre = 'SIN-2026-DEMO1'),
       'INV-1-20261014-DEMO1',
       105000.00, 21000.00, 126000.00,
       NOW() - interval '1 day', NOW() + interval '29 days', 'pending_sinistre',
       'approved', (SELECT id FROM users WHERE email = 'medecin.conseil@mhc.demo'), NOW() - interval '1 day', 'Accord médical conforme au dossier.',
       'pending', NULL, 'Facture de démonstration — workflow sinistre',
       NOW() - interval '1 day', NOW()
WHERE NOT EXISTS (SELECT 1 FROM invoices WHERE numero_facture = 'INV-1-20261014-DEMO1');

-- Lignes de facture
INSERT INTO invoice_items (invoice_id, prestation_id, libelle, quantite, prix_unitaire, montant_ht, taux_tva, montant_ttc)
SELECT i.id, p.id, p.libelle, p.quantite, p.montant_unitaire, p.montant_total, 0.20, p.montant_total * 1.2
FROM invoices i
JOIN sinistres s ON s.numero_sinistre = 'SIN-2026-DEMO1'
JOIN prestations p ON p.sinistre_id = s.id AND p.code_prestation IN ('CONS-URG', 'SEJ-URG-2J')
WHERE i.numero_facture = 'INV-1-20261014-DEMO1'
  AND NOT EXISTS (SELECT 1 FROM invoice_items ii WHERE ii.invoice_id = i.id);

-- Historique de la facture
INSERT INTO invoice_history (invoice_id, action, previous_status, new_status, previous_stage, new_stage, actor_id, notes, created_at)
SELECT i.id, 'invoice_created', NULL, 'pending_medical', NULL, 'medical',
       (SELECT id FROM users WHERE email = 'admin@mhc.com'), 'Facture créée par l''hôpital.', NOW() - interval '1 day'
FROM invoices i WHERE i.numero_facture = 'INV-1-20261014-DEMO1'
  AND NOT EXISTS (SELECT 1 FROM invoice_history h WHERE h.invoice_id = i.id);

INSERT INTO invoice_history (invoice_id, action, previous_status, new_status, previous_stage, new_stage, actor_id, notes, created_at)
SELECT i.id, 'medical_approved', 'pending_medical', 'pending_sinistre', 'medical', 'sinistre',
       (SELECT id FROM users WHERE email = 'medecin.conseil@mhc.demo'), 'Accord médical conforme au dossier.', NOW() - interval '1 day'
FROM invoices i WHERE i.numero_facture = 'INV-1-20261014-DEMO1'
  AND (SELECT COUNT(*) FROM invoice_history h WHERE h.invoice_id = i.id) = 1;

COMMIT;

-- Récapitulatif
SELECT role, COUNT(*) AS nb, string_agg(email, ', ' ORDER BY email) AS comptes
FROM users
WHERE email LIKE '%mhc.demo'
GROUP BY role
ORDER BY role;
