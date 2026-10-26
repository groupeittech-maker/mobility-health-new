-- ================================================================
-- SEED : chaîne financière de démo (souscriptions + paiements + attestations)
-- Objet : alimenter le portail comptable / grand livre / encaissements
--   1) SOU-2026-DEMO1 : payé - attestation définitive (direct)
--   2) SOU-2026-DEMO2 : reçu provisoire (via courtier Cabinet Koffi)
--   3) SOU-2026-DEMO3 : remboursé - refus du dossier
-- Idempotent : numéros uniques vérifiés avant insertion.
-- ================================================================

BEGIN;

-- ----------------------------------------------------------------
-- 1) SOU-2026-DEMO1 — NSIA / MyMHC Confort — paiement validé + attestation définitive
-- ----------------------------------------------------------------
INSERT INTO souscriptions (user_id, produit_assurance_id, numero_souscription, prix_applique,
                           prime_assurance, cout_police, frais_services, taxes, taxes_total,
                           canal_distribution, courtier_id, date_debut, date_fin, statut,
                           validation_medicale, validation_technique, validation_finale,
                           created_at, updated_at)
SELECT u.id, 1, 'SOU-2026-DEMO1', 85000, 65000, 5000, 15000, '[]'::json, 0,
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

-- ----------------------------------------------------------------
-- 2) SOU-2026-DEMO2 — Allianz / MyMHC Premium via Cabinet Koffi — attestation provisoire
-- ----------------------------------------------------------------
INSERT INTO souscriptions (user_id, produit_assurance_id, numero_souscription, prix_applique,
                           prime_assurance, cout_police, frais_services, taxes, taxes_total,
                           canal_distribution, courtier_id, date_debut, date_fin, statut,
                           validation_medicale, validation_technique, validation_finale,
                           created_at, updated_at)
SELECT u.id, 3, 'SOU-2026-DEMO2', 120000, 95000, 5000, 20000, '[]'::json, 0,
       'courtier', (SELECT id FROM courtiers WHERE nom = 'Cabinet Koffi & Associés'),
       NOW() - interval '10 days', NOW() + interval '11 months', 'en_attente_paiement',
       'approved', 'approved', 'pending', NOW() - interval '10 days', NOW()
FROM users u WHERE u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM souscriptions WHERE numero_souscription = 'SOU-2026-DEMO2');

INSERT INTO paiements (souscription_id, user_id, montant, type_paiement, statut, date_paiement,
                       reference_transaction, reference_externe, notes, created_at, updated_at)
SELECT s.id, u.id, 120000, 'VIREMENT', 'VALIDE', NOW() - interval '9 days',
       'VIR-44910-TRX-2230', 'SGCI-VIR', 'Paiement prime souscription démo 2', NOW(), NOW()
FROM souscriptions s, users u
WHERE s.numero_souscription = 'SOU-2026-DEMO2' AND u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM paiements p WHERE p.reference_transaction = 'VIR-44910-TRX-2230');

INSERT INTO attestations (souscription_id, paiement_id, type_attestation, numero_attestation,
                          chemin_fichier_minio, bucket_minio, est_valide, created_at, updated_at)
SELECT s.id, p.id, 'provisoire', 'ATT-PROV-2026-0002',
       'attestations/ATT-PROV-2026-0002.pdf', 'mhc-documents', true, NOW(), NOW()
FROM souscriptions s
JOIN paiements p ON p.souscription_id = s.id AND p.reference_transaction = 'VIR-44910-TRX-2230'
WHERE s.numero_souscription = 'SOU-2026-DEMO2'
  AND NOT EXISTS (SELECT 1 FROM attestations WHERE numero_attestation = 'ATT-PROV-2026-0002');

-- ----------------------------------------------------------------
-- 3) SOU-2026-DEMO3 — Sanlam / remboursé (dossier refusé)
-- ----------------------------------------------------------------
INSERT INTO souscriptions (user_id, produit_assurance_id, numero_souscription, prix_applique,
                           prime_assurance, cout_police, frais_services, taxes, taxes_total,
                           canal_distribution, courtier_id, date_debut, date_fin, statut,
                           validation_medicale, validation_technique, validation_finale,
                           validation_finale_notes, created_at, updated_at)
SELECT u.id, 2, 'SOU-2026-DEMO3', 60000, 45000, 5000, 10000, '[]'::json, 0,
       'direct', NULL, NOW() - interval '20 days', NOW() + interval '11 months', 'refusee',
       'rejected', 'rejected', 'rejected', 'Dossier refusé : motif médical.', NOW() - interval '20 days', NOW()
FROM users u WHERE u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM souscriptions WHERE numero_souscription = 'SOU-2026-DEMO3');

INSERT INTO paiements (souscription_id, user_id, montant, type_paiement, statut, date_paiement,
                       reference_transaction, reference_externe, montant_rembourse, notes,
                       created_at, updated_at)
SELECT s.id, u.id, 60000, 'CARTE_BANCAIRE', 'REMBOURSE', NOW() - interval '19 days',
       'CB-77120-TRX-5510', 'CINETPAY-CI', 60000, 'Remboursé suite refus dossier', NOW(), NOW()
FROM souscriptions s, users u
WHERE s.numero_souscription = 'SOU-2026-DEMO3' AND u.email = 'assure.demo@mhc.demo'
  AND NOT EXISTS (SELECT 1 FROM paiements p WHERE p.reference_transaction = 'CB-77120-TRX-5510');

COMMIT;
