-- Fix production: accepter les valeurs enum en MAJUSCULES (EN_PLANIFICATION, LONG, etc.)
-- À exécuter sur la base PostgreSQL (psql ou depuis le conteneur db).
-- Si une valeur existe déjà, PostgreSQL renverra une erreur "already exists" : ignorer pour cette ligne.

-- statutprojetvoyage
ALTER TYPE statutprojetvoyage ADD VALUE IF NOT EXISTS 'EN_PLANIFICATION';
ALTER TYPE statutprojetvoyage ADD VALUE IF NOT EXISTS 'CONFIRME';
ALTER TYPE statutprojetvoyage ADD VALUE IF NOT EXISTS 'EN_COURS';
ALTER TYPE statutprojetvoyage ADD VALUE IF NOT EXISTS 'TERMINE';
ALTER TYPE statutprojetvoyage ADD VALUE IF NOT EXISTS 'ANNULE';

-- questionnairetype
ALTER TYPE questionnairetype ADD VALUE IF NOT EXISTS 'LONG';
ALTER TYPE questionnairetype ADD VALUE IF NOT EXISTS 'SHORT';

-- typepaiement (fix: invalid input value for enum typepaiement: "CARTE_BANCAIRE")
ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'CARTE_BANCAIRE';
ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'MOBILE_MONEY_AIRTEL';
ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'MOBILE_MONEY_MTN';
ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'MOBILE_MONEY_ORANGE';
ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'MOBILE_MONEY_MOOV';
ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'PAIEMENT_DIFFERE';
ALTER TYPE typepaiement ADD VALUE IF NOT EXISTS 'PRELEVEMENT';
