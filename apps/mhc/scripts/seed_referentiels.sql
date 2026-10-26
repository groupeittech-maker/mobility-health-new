-- ================================================================
-- SEED : Données de paramétrage de test — Mobility Health Care
-- Contexte : assurance voyage, Côte d'Ivoire, FCFA
-- Idempotent : ON CONFLICT DO NOTHING partout où possible
-- ================================================================

BEGIN;

-- ----------------------------------------------------------------
-- 1. ZONES TARIFAIRES
-- ----------------------------------------------------------------
INSERT INTO tarification_zones (code, nom, description, coefficient, ordre_affichage, est_actif, created_at, updated_at) VALUES
    ('INTRA_AFRIQUE', 'Intra-Afrique (CEDEAO/CEMAC)', 'Voyages à l''intérieur de l''Afrique subsaharienne', 1.0, 1, true, NOW(), NOW()),
    ('RSA_MAGHREB', 'Afrique du Nord & RSA', 'Maghreb et Afrique du Sud', 1.15, 2, true, NOW(), NOW()),
    ('INTER_AFRIQUE', 'Inter-Afrique élargie', 'Trajets entre sous-régions africaines', 1.1, 3, true, NOW(), NOW()),
    ('EXTRA_AFRIQUE', 'Hors Afrique', 'Europe, Amériques, Asie, Moyen-Orient', 1.8, 4, true, NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------
-- 2. FENÊTRES DE DURÉE
-- ----------------------------------------------------------------
INSERT INTO tarification_fenetres_duree (libelle, duree_min_jours, duree_max_jours, coefficient, ordre_priorite, est_actif, created_at, updated_at) VALUES
    ('1 à 7 jours', 1, 7, 1.0, 1, true, NOW(), NOW()),
    ('8 à 15 jours', 8, 15, 1.0, 2, true, NOW(), NOW()),
    ('16 à 30 jours', 16, 30, 1.0, 3, true, NOW(), NOW()),
    ('31 à 90 jours', 31, 90, 1.0, 4, true, NOW(), NOW()),
    ('91 jours à 1 an', 91, 365, 1.0, 5, true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------
-- 3. TRANCHES D'ÂGE
-- ----------------------------------------------------------------
INSERT INTO tarification_tranches_age (libelle, age_min, age_max, coefficient, ordre_priorite, est_actif, created_at, updated_at) VALUES
    ('Moins de 18 ans', NULL, 17, 1.30, 1, true, NOW(), NOW()),
    ('18 à 69 ans (standard)', 18, 69, 1.0, 2, true, NOW(), NOW()),
    ('70 à 75 ans', 70, 75, 1.15, 3, true, NOW(), NOW()),
    ('76 à 80 ans', 76, 80, 1.30, 4, true, NOW(), NOW()),
    ('81 à 89 ans', 81, 89, 1.60, 5, true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------
-- 4. PAYS DE DESTINATION
-- ----------------------------------------------------------------
INSERT INTO destination_countries (code, nom, est_actif, ordre_affichage, notes, created_at, updated_at) VALUES
    ('CI', 'Côte d''Ivoire', true, 1, 'Pays de résidence principal', NOW(), NOW()),
    ('SN', 'Sénégal', true, 2, NULL, NOW(), NOW()),
    ('ML', 'Mali', true, 3, NULL, NOW(), NOW()),
    ('BF', 'Burkina Faso', true, 4, NULL, NOW(), NOW()),
    ('NE', 'Niger', true, 5, NULL, NOW(), NOW()),
    ('TG', 'Togo', true, 6, NULL, NOW(), NOW()),
    ('BJ', 'Bénin', true, 7, NULL, NOW(), NOW()),
    ('GH', 'Ghana', true, 8, NULL, NOW(), NOW()),
    ('GN', 'Guinée', true, 9, NULL, NOW(), NOW()),
    ('CM', 'Cameroun', true, 10, 'CEMAC', NOW(), NOW()),
    ('GA', 'Gabon', true, 11, 'CEMAC', NOW(), NOW()),
    ('CG', 'Congo', true, 12, 'CEMAC', NOW(), NOW()),
    ('CD', 'RD Congo', true, 13, NULL, NOW(), NOW()),
    ('MA', 'Maroc', true, 14, 'Maghreb', NOW(), NOW()),
    ('DZ', 'Algérie', true, 15, 'Maghreb', NOW(), NOW()),
    ('TN', 'Tunisie', true, 16, 'Maghreb', NOW(), NOW()),
    ('ZA', 'Afrique du Sud', true, 17, NULL, NOW(), NOW()),
    ('KE', 'Kenya', true, 18, NULL, NOW(), NOW()),
    ('ET', 'Éthiopie', true, 19, 'Siège UA', NOW(), NOW()),
    ('NG', 'Nigeria', true, 20, NULL, NOW(), NOW()),
    ('FR', 'France', true, 30, 'Europe — Schengen', NOW(), NOW()),
    ('BE', 'Belgique', true, 31, 'Europe — Schengen', NOW(), NOW()),
    ('CH', 'Suisse', true, 32, 'Europe — Schengen', NOW(), NOW()),
    ('GB', 'Royaume-Uni', true, 33, 'Europe — hors Schengen', NOW(), NOW()),
    ('US', 'États-Unis', true, 34, 'Amérique du Nord', NOW(), NOW()),
    ('CA', 'Canada', true, 35, 'Amérique du Nord', NOW(), NOW()),
    ('AE', 'Émirats arabes unis', true, 36, 'Moyen-Orient — hub Dubaï', NOW(), NOW()),
    ('TR', 'Turquie', true, 37, 'Hub Istanbul', NOW(), NOW()),
    ('CN', 'Chine', true, 38, 'Asie', NOW(), NOW()),
    ('IN', 'Inde', true, 39, 'Asie — tourisme médical', NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------
-- 5. VILLES (quelques-unes par pays clé)
-- ----------------------------------------------------------------
INSERT INTO destination_cities (pays_id, nom, est_actif, ordre_affichage, created_at, updated_at)
SELECT c.id, v.nom, true, v.ordre, NOW(), NOW()
FROM destination_countries c
JOIN (VALUES
    ('CI', 'Abidjan', 1), ('CI', 'Yamoussoukro', 2), ('CI', 'Bouaké', 3), ('CI', 'San-Pédro', 4),
    ('SN', 'Dakar', 1), ('SN', 'Thiès', 2), ('SN', 'Saint-Louis', 3),
    ('ML', 'Bamako', 1), ('ML', 'Sikasso', 2),
    ('BF', 'Ouagadougou', 1), ('BF', 'Bobo-Dioulasso', 2),
    ('TG', 'Lomé', 1),
    ('BJ', 'Cotonou', 1), ('BJ', 'Porto-Novo', 2),
    ('GH', 'Accra', 1), ('GH', 'Kumasi', 2),
    ('CM', 'Douala', 1), ('CM', 'Yaoundé', 2),
    ('GA', 'Libreville', 1),
    ('CG', 'Brazzaville', 1), ('CG', 'Pointe-Noire', 2),
    ('MA', 'Casablanca', 1), ('MA', 'Rabat', 2), ('MA', 'Marrakech', 3),
    ('ZA', 'Johannesburg', 1), ('ZA', 'Le Cap', 2),
    ('FR', 'Paris', 1), ('FR', 'Lyon', 2), ('FR', 'Marseille', 3),
    ('BE', 'Bruxelles', 1),
    ('GB', 'Londres', 1),
    ('US', 'New York', 1), ('US', 'Washington', 2), ('US', 'Atlanta', 3),
    ('CA', 'Montréal', 1), ('CA', 'Toronto', 2),
    ('AE', 'Dubaï', 1), ('AE', 'Abou Dabi', 2),
    ('TR', 'Istanbul', 1)
) AS v(code, nom, ordre) ON c.code = v.code
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------
-- 6. RATTACHEMENT PAYS ↔ ZONES
-- ----------------------------------------------------------------
-- Intra-Afrique : CEDEAO + CEMAC + quelques pays voisins
INSERT INTO tarification_zone_pays (zone_id, destination_country_id, created_at, updated_at)
SELECT z.id, c.id, NOW(), NOW()
FROM tarification_zones z, destination_countries c
WHERE z.code = 'INTRA_AFRIQUE'
  AND c.code IN ('CI','SN','ML','BF','NE','TG','BJ','GH','GN','CM','GA','CG','CD','NG')
ON CONFLICT (zone_id, destination_country_id) DO NOTHING;

-- RSA/Maghreb : Afrique du Nord + Afrique du Sud
INSERT INTO tarification_zone_pays (zone_id, destination_country_id, created_at, updated_at)
SELECT z.id, c.id, NOW(), NOW()
FROM tarification_zones z, destination_countries c
WHERE z.code = 'RSA_MAGHREB'
  AND c.code IN ('MA','DZ','TN','ZA','KE','ET')
ON CONFLICT (zone_id, destination_country_id) DO NOTHING;

-- Extra-Afrique : Europe, Amériques, Asie, Moyen-Orient
INSERT INTO tarification_zone_pays (zone_id, destination_country_id, created_at, updated_at)
SELECT z.id, c.id, NOW(), NOW()
FROM tarification_zones z, destination_countries c
WHERE z.code = 'EXTRA_AFRIQUE'
  AND c.code IN ('FR','BE','CH','GB','US','CA','AE','TR','CN','IN')
ON CONFLICT (zone_id, destination_country_id) DO NOTHING;

-- Inter-Afrique : certains pays CEDEAO aussi en "inter" (exemple double rattachement)
INSERT INTO tarification_zone_pays (zone_id, destination_country_id, created_at, updated_at)
SELECT z.id, c.id, NOW(), NOW()
FROM tarification_zones z, destination_countries c
WHERE z.code = 'INTER_AFRIQUE'
  AND c.code IN ('CM','GA','CG','CD','KE','ET','NG','GH')
ON CONFLICT (zone_id, destination_country_id) DO NOTHING;

-- ----------------------------------------------------------------
-- 7. GRILLE DE PRIX DE RÉFÉRENCE (zone × fenêtre, en FCFA)
-- ----------------------------------------------------------------
INSERT INTO tarification_grille_prix (zone_id, fenetre_duree_id, prix, created_at, updated_at)
SELECT z.id, f.id, v.prix, NOW(), NOW()
FROM tarification_zones z
JOIN tarification_fenetres_duree f ON true
JOIN (VALUES
    -- zone, fenêtre (libellé), prix
    ('INTRA_AFRIQUE', '1 à 7 jours',        12000),
    ('INTRA_AFRIQUE', '8 à 15 jours',       18500),
    ('INTRA_AFRIQUE', '16 à 30 jours',      27500),
    ('INTRA_AFRIQUE', '31 à 90 jours',      55000),
    ('INTRA_AFRIQUE', '91 jours à 1 an',   120000),
    ('INTER_AFRIQUE', '1 à 7 jours',        14000),
    ('INTER_AFRIQUE', '8 à 15 jours',       21000),
    ('INTER_AFRIQUE', '16 à 30 jours',      32000),
    ('INTER_AFRIQUE', '31 à 90 jours',      63000),
    ('INTER_AFRIQUE', '91 jours à 1 an',   138000),
    ('RSA_MAGHREB',   '1 à 7 jours',        16000),
    ('RSA_MAGHREB',   '8 à 15 jours',       24000),
    ('RSA_MAGHREB',   '16 à 30 jours',      36000),
    ('RSA_MAGHREB',   '31 à 90 jours',      70000),
    ('RSA_MAGHREB',   '91 jours à 1 an',   155000),
    ('EXTRA_AFRIQUE', '1 à 7 jours',        25000),
    ('EXTRA_AFRIQUE', '8 à 15 jours',       42000),
    ('EXTRA_AFRIQUE', '16 à 30 jours',      68000),
    ('EXTRA_AFRIQUE', '31 à 90 jours',     135000),
    ('EXTRA_AFRIQUE', '91 jours à 1 an',   290000)
) AS v(zcode, flibelle, prix) ON z.code = v.zcode AND f.libelle = v.flibelle
ON CONFLICT ON CONSTRAINT uq_tarif_grille_zone_fenetre DO NOTHING;

COMMIT;

-- Vérification
SELECT 'zones' AS ref, COUNT(*) FROM tarification_zones
UNION ALL SELECT 'fenetres_duree', COUNT(*) FROM tarification_fenetres_duree
UNION ALL SELECT 'tranches_age', COUNT(*) FROM tarification_tranches_age
UNION ALL SELECT 'pays', COUNT(*) FROM destination_countries
UNION ALL SELECT 'villes', COUNT(*) FROM destination_cities
UNION ALL SELECT 'zone_pays', COUNT(*) FROM tarification_zone_pays
UNION ALL SELECT 'grille_prix', COUNT(*) FROM tarification_grille_prix;
