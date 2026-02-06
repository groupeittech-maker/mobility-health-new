-- À exécuter sur le VPS UNIQUEMENT, après le premier "alembic upgrade head"
-- (qui crée users, audit_logs, paiements, transaction_logs puis échoue sur ad587bb061e5).
-- Prérequis : la table "users" doit exister.
-- Usage : cat scripts/vps_fix_tables_before_alembic.sql | sudo docker compose exec -T db psql -U postgres -d mobility_health

-- Enums (ignorer si déjà existants)
DO $$ BEGIN
    CREATE TYPE cle_repartition AS ENUM ('par_personne', 'par_groupe', 'par_duree', 'par_destination', 'fixe');
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
    CREATE TYPE statutprojetvoyage AS ENUM ('en_planification', 'confirme', 'en_cours', 'termine', 'annule');
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
    CREATE TYPE questionnairetype AS ENUM ('short', 'long');
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
    CREATE TYPE statutsouscription AS ENUM ('en_attente', 'pending', 'active', 'suspendue', 'resiliee', 'expiree');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 1. destination_countries
CREATE TABLE IF NOT EXISTS destination_countries (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    nom VARCHAR(200) NOT NULL,
    est_actif BOOLEAN NOT NULL DEFAULT true,
    ordre_affichage INTEGER NOT NULL DEFAULT 0,
    notes VARCHAR(500),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_destination_countries_code ON destination_countries (code);
CREATE INDEX IF NOT EXISTS ix_destination_countries_id ON destination_countries (id);
CREATE INDEX IF NOT EXISTS ix_destination_countries_nom ON destination_countries (nom);

-- 2. destination_cities
CREATE TABLE IF NOT EXISTS destination_cities (
    id SERIAL PRIMARY KEY,
    pays_id INTEGER NOT NULL REFERENCES destination_countries(id) ON DELETE CASCADE,
    nom VARCHAR(200) NOT NULL,
    est_actif BOOLEAN NOT NULL DEFAULT true,
    ordre_affichage INTEGER NOT NULL DEFAULT 0,
    notes VARCHAR(500),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_destination_cities_id ON destination_cities (id);
CREATE INDEX IF NOT EXISTS ix_destination_cities_nom ON destination_cities (nom);
CREATE INDEX IF NOT EXISTS ix_destination_cities_pays_id ON destination_cities (pays_id);

-- 3. assureurs
CREATE TABLE IF NOT EXISTS assureurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(200) NOT NULL UNIQUE,
    pays VARCHAR(100) NOT NULL,
    logo_url VARCHAR(500),
    adresse VARCHAR(255),
    telephone VARCHAR(50),
    agent_comptable_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_assureurs_id ON assureurs (id);
CREATE INDEX IF NOT EXISTS ix_assureurs_agent_comptable_id ON assureurs (agent_comptable_id);

-- 4. produits_assurance
CREATE TABLE IF NOT EXISTS produits_assurance (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    nom VARCHAR(200) NOT NULL,
    description TEXT,
    version VARCHAR(20),
    est_actif BOOLEAN NOT NULL DEFAULT true,
    assureur VARCHAR(200),
    assureur_id INTEGER REFERENCES assureurs(id) ON DELETE SET NULL,
    image_url VARCHAR(500),
    cout NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'XAF',
    cle_repartition cle_repartition NOT NULL DEFAULT 'fixe',
    commission_assureur_pct NUMERIC(5, 2),
    zones_geographiques JSONB,
    duree_min_jours INTEGER,
    duree_max_jours INTEGER,
    duree_validite_jours INTEGER,
    reconduction_possible BOOLEAN NOT NULL DEFAULT false,
    couverture_multi_entrees BOOLEAN NOT NULL DEFAULT false,
    age_minimum INTEGER,
    age_maximum INTEGER,
    conditions_sante TEXT,
    categories_assures JSONB,
    garanties JSONB,
    primes_generees JSONB,
    exclusions_generales JSONB,
    conditions TEXT,
    conditions_generales_pdf_url VARCHAR(500),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_produits_assurance_id ON produits_assurance (id);
CREATE INDEX IF NOT EXISTS ix_produits_assurance_code ON produits_assurance (code);
CREATE INDEX IF NOT EXISTS ix_produits_assurance_assureur_id ON produits_assurance (assureur_id);

-- 5. projets_voyage
CREATE TABLE IF NOT EXISTS projets_voyage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    titre VARCHAR(200) NOT NULL,
    description TEXT,
    destination VARCHAR(200) NOT NULL,
    destination_country_id INTEGER REFERENCES destination_countries(id) ON DELETE SET NULL,
    date_depart TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    date_retour TIMESTAMP WITHOUT TIME ZONE,
    nombre_participants INTEGER NOT NULL DEFAULT 1,
    statut statutprojetvoyage NOT NULL DEFAULT 'en_planification',
    notes TEXT,
    budget_estime NUMERIC(10, 2),
    questionnaire_type questionnairetype NOT NULL DEFAULT 'long',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_projets_voyage_id ON projets_voyage (id);
CREATE INDEX IF NOT EXISTS ix_projets_voyage_user_id ON projets_voyage (user_id);
CREATE INDEX IF NOT EXISTS ix_projets_voyage_destination_country_id ON projets_voyage (destination_country_id);

-- 6. souscriptions
CREATE TABLE IF NOT EXISTS souscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    produit_assurance_id INTEGER NOT NULL REFERENCES produits_assurance(id) ON DELETE RESTRICT,
    projet_voyage_id INTEGER REFERENCES projets_voyage(id) ON DELETE SET NULL,
    numero_souscription VARCHAR(100) NOT NULL UNIQUE,
    prix_applique NUMERIC(10, 2) NOT NULL,
    date_debut TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    date_fin TIMESTAMP WITHOUT TIME ZONE,
    statut statutsouscription NOT NULL DEFAULT 'en_attente',
    notes TEXT,
    validation_medicale VARCHAR(20),
    validation_medicale_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
    validation_medicale_date TIMESTAMP WITHOUT TIME ZONE,
    validation_medicale_notes TEXT,
    validation_technique VARCHAR(20),
    validation_technique_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
    validation_technique_date TIMESTAMP WITHOUT TIME ZONE,
    validation_technique_notes TEXT,
    validation_finale VARCHAR(20),
    validation_finale_par INTEGER REFERENCES users(id) ON DELETE SET NULL,
    validation_finale_date TIMESTAMP WITHOUT TIME ZONE,
    validation_finale_notes TEXT,
    demande_resiliation VARCHAR(20),
    demande_resiliation_date TIMESTAMP WITHOUT TIME ZONE,
    demande_resiliation_notes TEXT,
    demande_resiliation_par_agent INTEGER REFERENCES users(id) ON DELETE SET NULL,
    demande_resiliation_date_traitement TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_souscriptions_id ON souscriptions (id);
CREATE INDEX IF NOT EXISTS ix_souscriptions_user_id ON souscriptions (user_id);
CREATE INDEX IF NOT EXISTS ix_souscriptions_produit_assurance_id ON souscriptions (produit_assurance_id);
CREATE INDEX IF NOT EXISTS ix_souscriptions_projet_voyage_id ON souscriptions (projet_voyage_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_souscriptions_numero_souscription ON souscriptions (numero_souscription);
CREATE INDEX IF NOT EXISTS ix_souscriptions_statut ON souscriptions (statut);
CREATE INDEX IF NOT EXISTS ix_souscriptions_validation_medicale ON souscriptions (validation_medicale);
CREATE INDEX IF NOT EXISTS ix_souscriptions_validation_technique ON souscriptions (validation_technique);
CREATE INDEX IF NOT EXISTS ix_souscriptions_validation_finale ON souscriptions (validation_finale);
CREATE INDEX IF NOT EXISTS ix_souscriptions_demande_resiliation ON souscriptions (demande_resiliation);

-- 7. hospitals (requise par hospital_exam_tarifs, hospital_act_tarifs, hospital_stays, etc.)
CREATE TABLE IF NOT EXISTS hospitals (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(200) NOT NULL,
    adresse VARCHAR(500),
    ville VARCHAR(100),
    pays VARCHAR(100),
    code_postal VARCHAR(20),
    telephone VARCHAR(50),
    email VARCHAR(255),
    latitude NUMERIC(10, 8) NOT NULL DEFAULT 0,
    longitude NUMERIC(11, 8) NOT NULL DEFAULT 0,
    est_actif BOOLEAN NOT NULL DEFAULT true,
    specialites TEXT,
    capacite_lits INTEGER,
    notes TEXT,
    medecin_referent_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_hospitals_id ON hospitals (id);
CREATE INDEX IF NOT EXISTS ix_hospitals_nom ON hospitals (nom);
CREATE INDEX IF NOT EXISTS ix_hospitals_medecin_referent_id ON hospitals (medecin_referent_id);

-- 8. alertes (requise par sinistres)
CREATE TABLE IF NOT EXISTS alertes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    souscription_id INTEGER REFERENCES souscriptions(id) ON DELETE SET NULL,
    numero_alerte VARCHAR(100) NOT NULL UNIQUE,
    latitude NUMERIC(10, 8) NOT NULL,
    longitude NUMERIC(11, 8) NOT NULL,
    adresse VARCHAR(500),
    description TEXT,
    statut VARCHAR(20) NOT NULL DEFAULT 'en_attente',
    priorite VARCHAR(20) NOT NULL DEFAULT 'normale',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_alertes_id ON alertes (id);
CREATE INDEX IF NOT EXISTS ix_alertes_user_id ON alertes (user_id);
CREATE INDEX IF NOT EXISTS ix_alertes_souscription_id ON alertes (souscription_id);
CREATE INDEX IF NOT EXISTS ix_alertes_numero_alerte ON alertes (numero_alerte);
CREATE INDEX IF NOT EXISTS ix_alertes_statut ON alertes (statut);

-- 9. sinistres (requise par sinistre_process_steps)
CREATE TABLE IF NOT EXISTS sinistres (
    id SERIAL PRIMARY KEY,
    alerte_id INTEGER NOT NULL REFERENCES alertes(id) ON DELETE CASCADE,
    souscription_id INTEGER REFERENCES souscriptions(id) ON DELETE SET NULL,
    hospital_id INTEGER REFERENCES hospitals(id) ON DELETE SET NULL,
    numero_sinistre VARCHAR(100) UNIQUE,
    description TEXT,
    statut VARCHAR(20) NOT NULL DEFAULT 'en_cours',
    agent_sinistre_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    medecin_referent_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sinistres_id ON sinistres (id);
CREATE INDEX IF NOT EXISTS ix_sinistres_alerte_id ON sinistres (alerte_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_souscription_id ON sinistres (souscription_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_hospital_id ON sinistres (hospital_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_numero_sinistre ON sinistres (numero_sinistre);
CREATE INDEX IF NOT EXISTS ix_sinistres_statut ON sinistres (statut);
CREATE INDEX IF NOT EXISTS ix_sinistres_agent_sinistre_id ON sinistres (agent_sinistre_id);
CREATE INDEX IF NOT EXISTS ix_sinistres_medecin_referent_id ON sinistres (medecin_referent_id);
