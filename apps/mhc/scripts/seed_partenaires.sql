-- ================================================================
-- SEED 2 : Partenaires & Produits — Mobility Health Care
-- ================================================================

BEGIN;

-- ----------------------------------------------------------------
-- 8. ASSUREURS
-- ----------------------------------------------------------------
INSERT INTO assureurs (nom, pays, adresse, telephone, created_at, updated_at) VALUES
    ('NSIA Assurance', 'Côte d''Ivoire', 'Abidjan Plateau, Av. Chardy', '+225 20 30 31 00', NOW(), NOW()),
    ('Allianz Côte d''Ivoire', 'Côte d''Ivoire', 'Abidjan, Bd de Marseille', '+225 20 25 75 00', NOW(), NOW()),
    ('Sanlam Assurance', 'Côte d''Ivoire', 'Abidjan, Rue des Jardins', '+225 27 20 33 40', NOW(), NOW())
ON CONFLICT (nom) DO NOTHING;

-- ----------------------------------------------------------------
-- 9. RÉASSUREURS
-- ----------------------------------------------------------------
INSERT INTO reassureurs (nom, code, pays, ville, adresse, telephone, email, contact_nom, est_actif, cession_defaut_pct, commission_cession_defaut_pct, created_at, updated_at) VALUES
    ('Africa Re', 'AFRICARE', 'Nigeria', 'Lagos', 'Africa Re House, Lagos', '+234 1 2800 000', 'contact@africa-re.com', 'Amadou Diallo', true, 30, 5, NOW(), NOW()),
    ('CICA-RE', 'CICARE', 'Togo', 'Lomé', 'Boulevard du 13 Janvier', '+228 22 21 50 00', 'info@cica-re.com', 'Kossi Mensah', true, 25, 4, NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------
-- 10. COURTIERS (rattachés à un assureur)
-- ----------------------------------------------------------------
INSERT INTO courtiers (nom, pays, adresse, telephone, assureur_id, commission_pct, created_at, updated_at)
SELECT v.nom, v.pays, v.adresse, v.tel, a.id, v.commission, NOW(), NOW()
FROM assureurs a
JOIN (VALUES
    ('Cabinet Koffi & Associés', 'Côte d''Ivoire', 'Abidjan Cocody, Rue des Cannes', '+225 07 08 09 10', 'NSIA Assurance', 15),
    ('Afrique Courtage', 'Côte d''Ivoire', 'Abidjan Plateau, Immeuble Alpha 2000', '+225 20 22 44 55', 'Allianz Côte d''Ivoire', 12),
    ('Sahel Insurance Brokers', 'Sénégal', 'Dakar, Avenue Pompidou', '+221 33 823 45 67', 'Sanlam Assurance', 10)
) AS v(nom, pays, adresse, tel, assureur_nom, commission) ON a.nom = v.assureur_nom
ON CONFLICT (nom) DO NOTHING;

-- ----------------------------------------------------------------
-- 11. HÔPITAUX / PARTENAIRES SANTÉ
-- ----------------------------------------------------------------
INSERT INTO hospitals (nom, adresse, ville, pays, telephone, email, latitude, longitude, est_actif, specialites, capacite_lits, created_at, updated_at) VALUES
    ('CHU de Treichville', 'Boulevard de Marseille', 'Abidjan', 'Côte d''Ivoire', '+225 21 24 85 10', 'contact@chu-treichville.ci', 5.2919, -4.0130, true, 'Urgences, Chirurgie, Médecine interne', 300, NOW(), NOW()),
    ('Hôpital Principal de Dakar', 'Avenue Nelson Mandela', 'Dakar', 'Sénégal', '+221 33 839 50 50', 'info@hpd.sn', 14.6708, -17.4381, true, 'Urgences, Cardiologie, Maternité', 450, NOW(), NOW()),
    ('Clinique les Cocotiers', 'Rue de la Paix, Plateau', 'Abidjan', 'Côte d''Ivoire', '+225 20 21 45 67', 'accueil@clinique-cocotiers.ci', 5.3235, -4.0167, true, 'Médecine générale, Pédiatrie, Imagerie', 80, NOW(), NOW()),
    ('PISAM', 'Boulevard de Marseille, Marcory', 'Abidjan', 'Côte d''Ivoire', '+225 21 26 34 34', 'contact@pisam.ci', 5.2986, -3.9877, true, 'Chirurgie, Cardiologie, Urgences', 120, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------
-- 12. TARIFS ACTES MÉDICAUX (par hôpital)
-- ----------------------------------------------------------------
INSERT INTO hospital_act_tarifs (hospital_id, code, nom, description, montant, created_at, updated_at)
SELECT h.id, v.code, v.nom, v.description, v.montant, NOW(), NOW()
FROM hospitals h
JOIN (VALUES
    ('CHU de Treichville', 'CONS_GEN', 'Consultation générale', 'Consultation médecine générale', 10000),
    ('CHU de Treichville', 'CONS_SPEC', 'Consultation spécialiste', 'Consultation médecin spécialiste', 20000),
    ('CHU de Treichville', 'URG', 'Prise en charge urgence', 'Passage aux urgences + examen initial', 25000),
    ('CHU de Treichville', 'HOSP_J', 'Hospitalisation / jour', 'Chambre commune par jour', 35000),
    ('CHU de Treichville', 'CHIR_MINEURE', 'Chirurgie mineure', 'Intervention mineure en ambulatoire', 150000),
    ('Hôpital Principal de Dakar', 'CONS_GEN', 'Consultation générale', 'Consultation médecine générale', 12000),
    ('Hôpital Principal de Dakar', 'URG', 'Prise en charge urgence', 'Passage aux urgences', 28000),
    ('Hôpital Principal de Dakar', 'HOSP_J', 'Hospitalisation / jour', 'Par jour en hospitalisation', 40000),
    ('Clinique les Cocotiers', 'CONS_GEN', 'Consultation générale', NULL, 15000),
    ('Clinique les Cocotiers', 'CONS_PED', 'Consultation pédiatrique', NULL, 20000),
    ('Clinique les Cocotiers', 'HOSP_J', 'Hospitalisation / jour', 'Chambre individuelle', 50000),
    ('PISAM', 'CONS_GEN', 'Consultation générale', NULL, 25000),
    ('PISAM', 'URG', 'Prise en charge urgence', NULL, 50000),
    ('PISAM', 'HOSP_J', 'Hospitalisation / jour', 'Chambre individuelle soins intensifs', 100000)
) AS v(hnom, code, nom, description, montant) ON h.nom = v.hnom
ON CONFLICT ON CONSTRAINT uq_hospital_act_tarifs_hospital_nom DO NOTHING;

-- ----------------------------------------------------------------
-- 13. TARIFS EXAMENS (par hôpital)
-- ----------------------------------------------------------------
INSERT INTO hospital_exam_tarifs (hospital_id, nom, montant, created_at, updated_at)
SELECT h.id, v.nom, v.montant, NOW(), NOW()
FROM hospitals h
JOIN (VALUES
    ('CHU de Treichville', 'Radiographie standard', 15000),
    ('CHU de Treichville', 'Scanner (CT)', 80000),
    ('CHU de Treichville', 'IRM', 120000),
    ('CHU de Treichville', 'Échographie', 20000),
    ('CHU de Treichville', 'Bilan sanguin complet', 25000),
    ('CHU de Treichville', 'ECG', 10000),
    ('Hôpital Principal de Dakar', 'Radiographie standard', 18000),
    ('Hôpital Principal de Dakar', 'Scanner (CT)', 90000),
    ('Hôpital Principal de Dakar', 'Échographie', 22000),
    ('Hôpital Principal de Dakar', 'Bilan sanguin complet', 28000),
    ('Clinique les Cocotiers', 'Radiographie standard', 20000),
    ('Clinique les Cocotiers', 'Échographie', 25000),
    ('Clinique les Cocotiers', 'Bilan sanguin complet', 30000),
    ('PISAM', 'IRM', 150000),
    ('PISAM', 'Scanner (CT)', 100000),
    ('PISAM', 'Coronarographie', 450000)
) AS v(hnom, nom, montant) ON h.nom = v.hnom
ON CONFLICT ON CONSTRAINT uq_hospital_exam_tarifs_hospital_nom DO NOTHING;

-- ----------------------------------------------------------------
-- 14. HÔTELS & HÉBERGEMENTS
-- ----------------------------------------------------------------
INSERT INTO hotels (nom, adresse, ville, pays, telephone, email, latitude, longitude, categorie, contact_nom, est_actif) VALUES
    ('Hôtel Ivoire', 'Bd Hassan II, Cocody', 'Abidjan', 'Côte d''Ivoire', '+225 22 48 10 45', 'resa@hotelivoire.ci', 5.3599, -3.9985, '5 étoiles', 'Marie Touré', true),
    ('Azalaï Hôtel', 'Rue Joseph Gomis', 'Dakar', 'Sénégal', '+221 33 889 10 00', 'contact@azalai.sn', 14.6928, -17.4467, '4 étoiles', 'Fatou Ndiaye', true),
    ('Hôtel La Maison Blanche', 'Rue du Commerce, Plateau', 'Abidjan', 'Côte d''Ivoire', '+225 20 30 40 50', 'info@maisonblanche.ci', 5.3199, -4.0267, '3 étoiles', 'Jean Kouassi', true),
    ('Radisson Blu Ouaga', 'Avenue de l''OUA', 'Ouagadougou', 'Burkina Faso', '+226 25 33 33 33', 'ouaga@radisson.com', 12.3714, -1.5197, '4 étoiles', 'Aïcha Ouedraogo', true)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------
-- 15. TRANSPORTEURS MÉDICAUX
-- ----------------------------------------------------------------
INSERT INTO transport_providers (nom, type_vehicule, ville, pays, telephone, email, contact_nom, est_actif) VALUES
    ('Ambulance Plus CI', 'Ambulance médicalisée', 'Abidjan', 'Côte d''Ivoire', '+225 07 77 88 99', 'urgence@ambulanceplus.ci', 'Dr. Yao N''Guessan', true),
    ('SAMU Dakar', 'Ambulance + VSL', 'Dakar', 'Sénégal', '+221 77 123 45 67', 'samu@samudakar.sn', 'Ibrahima Fall', true),
    ('Air Medical Assistance', 'Avion sanitaire', 'Abidjan', 'Côte d''Ivoire', '+225 27 22 11 00', 'ops@airmedical.aero', 'Claude Bamba', true),
    ('Trans-Santé Afrique', 'VSL + Ambulance', 'Ouagadougou', 'Burkina Faso', '+226 70 20 30 40', 'contact@transsante.bf', 'Moussa Sawadogo', true)
ON CONFLICT DO NOTHING;

COMMIT;

SELECT 'assureurs' AS ref, COUNT(*) FROM assureurs
UNION ALL SELECT 'reassureurs', COUNT(*) FROM reassureurs
UNION ALL SELECT 'courtiers', COUNT(*) FROM courtiers
UNION ALL SELECT 'hospitals', COUNT(*) FROM hospitals
UNION ALL SELECT 'act_tarifs', COUNT(*) FROM hospital_act_tarifs
UNION ALL SELECT 'exam_tarifs', COUNT(*) FROM hospital_exam_tarifs
UNION ALL SELECT 'hotels', COUNT(*) FROM hotels
UNION ALL SELECT 'transport_providers', COUNT(*) FROM transport_providers;
