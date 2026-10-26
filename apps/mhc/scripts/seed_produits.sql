-- ================================================================
-- SEED 3 : Produits d'assurance voyage — Mobility Health Care
-- Garanties : [{titre, capitaux}] · Exclusions : [{reference, exclusion}]
-- ================================================================

BEGIN;

-- ----------------------------------------------------------------
-- 16. PRODUITS D'ASSURANCE
-- ----------------------------------------------------------------
INSERT INTO produits_assurance (
    code, nom, description, est_actif, assureur, assureur_id, cout, currency,
    cle_repartition, commission_assureur_pct,
    age_minimum, age_maximum, duree_min_jours, duree_max_jours, duree_validite_jours,
    garanties, exclusions_generales,
    surprime_moins_18_pct, surprime_70_75_pct, surprime_76_80_pct, surprime_81_89_pct,
    pays, created_at, updated_at
)
SELECT
    v.code, v.nom, v.description, true, v.assureur_nom, a.id, v.cout, 'XAF',
    'fixe', v.commission,
    v.age_min, v.age_max, 1, 365, 365,
    v.garanties::json, v.exclusions::json,
    v.sp_m18, v.sp_7075, v.sp_7680, v.sp_8189,
    'Côte d''Ivoire', NOW(), NOW()
FROM assureurs a
JOIN (VALUES
    (
        'MHC-ESSENTIEL', 'MyMHC Essentiel',
        'Assurance voyage économique — couverture médicale d''urgence et rapatriement pour courts séjours en Afrique de l''Ouest.',
        'NSIA Assurance', 8000, 30,
        1, 75,
        '[
            {"titre": "Assistance et suivi médical", "capitaux": ""},
            {"titre": "Frais médicaux et hospitalisations d''urgence à l''étranger", "capitaux": "5 000 000 FCFA"},
            {"titre": "Urgence dentaire à l''étranger", "capitaux": "100 000 FCFA"},
            {"titre": "Transport médicalisé", "capitaux": "1 000 000 FCFA"},
            {"titre": "Rapatriement sanitaire ou funéraire", "capitaux": "3 000 000 FCFA"}
        ]',
        '[
            {"reference": "Exclusion 1", "exclusion": "Maladies préexistantes non déclarées à la souscription"},
            {"reference": "Exclusion 2", "exclusion": "Sports à risque (parachutisme, alpinisme, sports mécaniques)"},
            {"reference": "Exclusion 3", "exclusion": "Grossesse au-delà du 6e mois et accouchement"},
            {"reference": "Exclusion 4", "exclusion": "Actes volontaires de l''assuré, ébriété, stupéfiants"},
            {"reference": "Exclusion 5", "exclusion": "Guerre, émeutes, actes de terrorisme"}
        ]',
        30, 15, 40, 80
    ),
    (
        'MHC-CONFORT', 'MyMHC Confort',
        'Couverture intermédiaire — frais médicaux étendus, assistance famille et hébergement en cas d''immobilisation.',
        'NSIA Assurance', 15000, 30,
        1, 80,
        '[
            {"titre": "Assistance et suivi médical", "capitaux": ""},
            {"titre": "Frais médicaux et hospitalisations d''urgence à l''étranger", "capitaux": "15 000 000 FCFA"},
            {"titre": "Urgence dentaire à l''étranger", "capitaux": "100 000 FCFA"},
            {"titre": "Transport médicalisé", "capitaux": "1 000 000 FCFA"},
            {"titre": "Rapatriement sanitaire ou funéraire", "capitaux": "5 000 000 FCFA soit 1 000 000 FCFA achat cercueil"},
            {"titre": "Rapatriement des proches parents", "capitaux": "1 billet d''avion A/R en éco"},
            {"titre": "Visite d''un proche parent", "capitaux": "1 billet d''avion A/R en éco"},
            {"titre": "Prise en charge des frais d''hébergement", "capitaux": "7 jours max / 50 000 FCFA par nuit"},
            {"titre": "Perte ou vol de bagages", "capitaux": "500 000 FCFA"}
        ]',
        '[
            {"reference": "Exclusion 1", "exclusion": "Maladies préexistantes non déclarées à la souscription"},
            {"reference": "Exclusion 2", "exclusion": "Sports à risque sauf option souscrite"},
            {"reference": "Exclusion 3", "exclusion": "Grossesse au-delà du 6e mois et accouchement"},
            {"reference": "Exclusion 4", "exclusion": "Voyages entrepris contre avis médical"},
            {"reference": "Exclusion 5", "exclusion": "Pays en état de guerre déclarée"}
        ]',
        30, 15, 30, 60
    ),
    (
        'MHC-PREMIUM', 'MyMHC Premium',
        'Couverture haut de gamme toutes destinations — capitaux élevés, accompagnement enfants, extensions seniors.',
        'Allianz Côte d''Ivoire', 30000, 28,
        1, 89,
        '[
            {"titre": "Assistance et suivi médical", "capitaux": ""},
            {"titre": "Frais médicaux et hospitalisations d''urgence à l''étranger", "capitaux": "50 000 000 FCFA"},
            {"titre": "Urgence dentaire à l''étranger", "capitaux": "300 000 FCFA"},
            {"titre": "Transport médicalisé", "capitaux": "Illimité"},
            {"titre": "Rapatriement sanitaire ou funéraire", "capitaux": "10 000 000 FCFA soit 2 000 000 FCFA achat cercueil"},
            {"titre": "Rapatriement des proches parents", "capitaux": "2 billets d''avion A/R en éco"},
            {"titre": "Accompagnement des enfants de moins de 15 ans", "capitaux": "1 billet d''avion A/R en éco"},
            {"titre": "Voyage d''un parent sur le lieu du décès", "capitaux": "1 billet d''avion A/R en éco"},
            {"titre": "Prise en charge des frais d''hébergement", "capitaux": "14 jours max / 100 000 FCFA par nuit"},
            {"titre": "Perte, vol ou retard de bagages", "capitaux": "1 500 000 FCFA"},
            {"titre": "Retard de vol (>4h)", "capitaux": "200 000 FCFA pour la durée du séjour"},
            {"titre": "Responsabilité civile vie privée à l''étranger", "capitaux": "30 000 000 FCFA"}
        ]',
        '[
            {"reference": "Exclusion 1", "exclusion": "Maladies préexistantes non déclarées à la souscription"},
            {"reference": "Exclusion 2", "exclusion": "Compétitions sportives professionnelles"},
            {"reference": "Exclusion 3", "exclusion": "Affections psychiatriques et cures de désintoxication"},
            {"reference": "Exclusion 4", "exclusion": "Voyages entrepris dans le but de se faire soigner (sauf accord préalable)"},
            {"reference": "Exclusion 5", "exclusion": "Zones exclues par les autorités sanitaires internationales"}
        ]',
        25, 15, 25, 40
    )
) AS v(code, nom, description, assureur_nom, cout, commission, age_min, age_max, garanties, exclusions, sp_m18, sp_7075, sp_7680, sp_8189)
ON a.nom = v.assureur_nom
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------
-- 17. MATRICE TARIFAIRE PRODUIT — MyMHC Confort (exemple dérogatoire)
--    Zone × fenêtre de durée, toutes tranches d'âge (18-69 par défaut)
-- ----------------------------------------------------------------
INSERT INTO produit_prime_tarif (produit_assurance_id, duree_min_jours, duree_max_jours, zone_code, age_min, age_max, prix, currency, ordre_priorite, created_at, updated_at)
SELECT p.id, v.dmin, v.dmax, v.zone, 18, 69, v.prix, 'XAF', v.priorite, NOW(), NOW()
FROM produits_assurance p
JOIN (VALUES
    ('INTRA_AFRIQUE', 1, 7,   13500, 1),
    ('INTRA_AFRIQUE', 8, 15,  20000, 2),
    ('INTRA_AFRIQUE', 16, 30, 30000, 3),
    ('EXTRA_AFRIQUE', 1, 7,   28000, 4),
    ('EXTRA_AFRIQUE', 8, 15,  46000, 5),
    ('EXTRA_AFRIQUE', 16, 30, 75000, 6)
) AS v(zone, dmin, dmax, prix, priorite) ON p.code = 'MHC-CONFORT'
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------
-- 18. SURPRIMES PRODUIT — MyMHC Premium (tranches seniors renforcées)
-- ----------------------------------------------------------------
INSERT INTO produit_surprimes (produit_id, age_min, age_max, taux_pct, montant_fixe, formule, created_at, updated_at)
SELECT p.id, v.amin, v.amax, v.taux, NULL, 'pct', NOW(), NOW()
FROM produits_assurance p
JOIN (VALUES
    (0, 17, 25),
    (70, 75, 15),
    (76, 80, 25),
    (81, 89, 40)
) AS v(amin, amax, taux) ON p.code = 'MHC-PREMIUM'
ON CONFLICT DO NOTHING;

COMMIT;

SELECT 'produits' AS ref, code, nom, cout FROM produits_assurance ORDER BY code;
SELECT 'matrice_confort' AS ref, zone_code, duree_min_jours, duree_max_jours, prix
FROM produit_prime_tarif t JOIN produits_assurance p ON p.id = t.produit_assurance_id ORDER BY t.ordre_priorite;
SELECT 'surprimes_premium' AS ref, age_min, age_max, taux_pct
FROM produit_surprimes s JOIN produits_assurance p ON p.id = s.produit_id;
