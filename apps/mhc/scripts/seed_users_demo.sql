-- ================================================================
-- SEED 4 : Comptes génériques de démo — tous les profils MHC
-- Mot de passe pour tous : mh@123
-- Hash bcrypt pré-calculé
-- ================================================================

BEGIN;

-- Variable pour le hash (factorisé)
-- $2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO  =  mh@123

-- ----------------------------------------------------------------
-- INTERNES MHC — PÔLE TECHNIQUE
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('sup.technique@mhc.demo',      'sup.technique',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Superviseur Technique',        'superviseur_technique',          true, false, true, NOW(), NOW()),
    ('agent.production@mhc.demo',   'agent.production',   '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Production',             'production_agent',               true, false, true, NOW(), NOW()),
    ('conformite.prod@mhc.demo',    'conformite.prod',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Production',  'agent_conformite_production',    true, false, true, NOW(), NOW()),
    ('agent.sinistre@mhc.demo',     'agent.sinistre',     '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Sinistre',               'agent_sinistre_mh',              true, false, true, NOW(), NOW()),
    ('conformite.sinistre@mhc.demo','conformite.sinistre','$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Sinistre',    'agent_conformite_sinistre',      true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- ----------------------------------------------------------------
-- INTERNES MHC — PÔLE AFFAIRES MÉDICALES
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('sup.medical@mhc.demo',        'sup.medical',        '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Superviseur Affaires Médicales','superviseur_affaires_medicales',true, false, true, NOW(), NOW()),
    ('agent.medical@mhc.demo',      'agent.medical',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Médical MHC',            'agent_medical_mhc',              true, false, true, NOW(), NOW()),
    ('conformite.medical@mhc.demo', 'conformite.medical', '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Médical',     'agent_conformite_medical',       true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- ----------------------------------------------------------------
-- INTERNES MHC — PÔLE COMPTABILITÉ & FINANCES
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('sup.comptable@mhc.demo',      'sup.comptable',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Superviseur Comptable',        'superviseur_comptable',          true, false, true, NOW(), NOW()),
    ('agent.comptable@mhc.demo',    'agent.comptable',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Comptable MH',           'agent_comptable_mh',             true, false, true, NOW(), NOW()),
    ('conformite.compta@mhc.demo',  'conformite.compta',  '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Conformité Comptable',   'agent_conformite_comptable',     true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- ----------------------------------------------------------------
-- MÉDECIN-CONSEIL MHC
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('medecin.conseil@mhc.demo',    'medecin.conseil',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Dr. Kouadio Médecin-Conseil',  'medecin_referent_mh',            true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- ----------------------------------------------------------------
-- EXTERNES — ASSUREUR (lié à NSIA Assurance, id=1)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('prod.assureur@mhc.demo',      'prod.assureur',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Production NSIA',        'agent_production_assureur',      true, false, true, NOW(), NOW()),
    ('sinistre.assureur@mhc.demo',  'sinistre.assureur',  '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Sinistre NSIA',          'agent_sinistre_assureur',        true, false, true, NOW(), NOW()),
    ('compta.assureur@mhc.demo',    'compta.assureur',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Comptable NSIA',         'agent_comptable_assureur',       true, false, true, NOW(), NOW()),
    ('medical.assureur@mhc.demo',   'medical.assureur',   '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Médical NSIA',           'agent_medical_assureur',         true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Liaisons assureur_agents (NSIA = id 1)
INSERT INTO assureur_agents (assureur_id, user_id, type_agent, created_at, updated_at)
SELECT 1, u.id, v.t, NOW(), NOW()
FROM users u
JOIN (VALUES
    ('prod.assureur@mhc.demo',     'production'),
    ('sinistre.assureur@mhc.demo', 'sinistre'),
    ('compta.assureur@mhc.demo',   'comptable'),
    ('medical.assureur@mhc.demo',  'medical')
) AS v(email, t) ON u.email = v.email
ON CONFLICT ON CONSTRAINT uq_assureur_agent_user DO NOTHING;

-- ----------------------------------------------------------------
-- EXTERNES — COURTIER (lié à Cabinet Koffi & Associés, id=1)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, created_at, updated_at) VALUES
    ('prod.courtier@mhc.demo',      'prod.courtier',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Production Courtier',    'agent_production_courtier',      true, false, true, NOW(), NOW()),
    ('assistant.souscr@mhc.demo',   'assistant.souscr',   '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Assistant Souscription',       'assistant_souscription',         true, false, true, NOW(), NOW()),
    ('sinistre.courtier@mhc.demo',  'sinistre.courtier',  '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Sinistre Courtier',      'agent_sinistre_courtier',        true, false, true, NOW(), NOW()),
    ('compta.courtier@mhc.demo',    'compta.courtier',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Comptable Courtier',     'agent_comptable_courtier',       true, false, true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Liaisons courtier_agents (Cabinet Koffi = id 1)
INSERT INTO courtier_agents (courtier_id, user_id, type_agent, created_at, updated_at)
SELECT 1, u.id, v.t, NOW(), NOW()
FROM users u
JOIN (VALUES
    ('prod.courtier@mhc.demo',     'production'),
    ('assistant.souscr@mhc.demo',  'souscription'),
    ('sinistre.courtier@mhc.demo', 'sinistre')
) AS v(email, t) ON u.email = v.email
ON CONFLICT ON CONSTRAINT uq_courtier_agent_user DO NOTHING;

-- Agent comptable du courtier (champ dédié sur la table courtiers)
UPDATE courtiers SET agent_comptable_id = (SELECT id FROM users WHERE email = 'compta.courtier@mhc.demo')
WHERE id = 1;

-- ----------------------------------------------------------------
-- EXTERNE — RÉASSUREUR (lié à Africa Re, id=1)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, reassureur_id, created_at, updated_at) VALUES
    ('verif.reassureur@mhc.demo',   'verif.reassureur',   '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Vérificateur Africa Re',       'agent_verificateur_reassureur',  true, false, true, 1, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- ----------------------------------------------------------------
-- PARTENAIRES SANTÉ (liés au CHU de Treichville, id=1)
-- ----------------------------------------------------------------
INSERT INTO users (email, username, hashed_password, full_name, role, is_active, is_superuser, email_verified, hospital_id, created_at, updated_at) VALUES
    ('admin.hopital@mhc.demo',      'admin.hopital',      '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Admin CHU Treichville',        'hospital_admin',               true, false, true, 1, NOW(), NOW()),
    ('medecin.hopital@mhc.demo',    'medecin.hopital',    '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Dr. Traoré CHU',               'medecin_hopital',              true, false, true, 1, NOW(), NOW()),
    ('reception.hopital@mhc.demo',  'reception.hopital',  '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Réception CHU',          'agent_reception_hopital',      true, false, true, 1, NOW(), NOW()),
    ('compta.hopital@mhc.demo',     'compta.hopital',     '$2b$12$Jvi7/pJsrGdNqYQERf6Wpuw9J65woDs/39hhPEpA/BNK0ZotUfngO', 'Agent Comptable CHU',          'agent_comptable_hopital',      true, false, true, 1, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

COMMIT;

-- Récapitulatif
SELECT role, COUNT(*) AS nb, string_agg(email, ', ' ORDER BY email) AS comptes
FROM users
GROUP BY role
ORDER BY role;
