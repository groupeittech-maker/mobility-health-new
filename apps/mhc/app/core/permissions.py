"""Matrice de permissions MHC — Edition / Contrôle / Consultation.

Source : FONCTIONNALITES INTERNES MHC.xlsx et FONCTIONNALITES EXTERNE MHC.xlsx.
Chaque profil (valeur de `users.role`) possède un niveau par fonctionnalité :

    edition      → lecture + création/modification/suppression
    controle     → lecture + validation / verdict de conformité
    consultation → lecture seule
    none         → pas d'accès

L'administrateur MHC (`admin`) a tous les droits en édition : il crée tous les
comptes et profils, y compris ceux des structures partenaires.
"""

from typing import Dict, Optional

# Ordre des niveaux : un niveau inclut les niveaux inférieurs.
LEVEL_NONE = "none"
LEVEL_CONSULTATION = "consultation"
LEVEL_CONTROLE = "controle"
LEVEL_EDITION = "edition"

_LEVEL_ORDER = {
    LEVEL_NONE: 0,
    LEVEL_CONSULTATION: 1,
    LEVEL_CONTROLE: 2,
    LEVEL_EDITION: 3,
}

# --- Fonctionnalités (clés stables, exposées au frontend) -------------------

F_COMPTES_PRODUITS = "comptes_produits"
F_COMPTES_ASSUREURS = "comptes_assureurs"
F_COMPTES_REASSUREURS = "comptes_reassureurs"
F_COMPTES_INTERMEDIAIRES = "comptes_intermediaires"
F_COMPTES_MEDECINS_CONSEIL = "comptes_medecins_conseil"
F_COMPTES_PARTENAIRES_SANTE = "comptes_partenaires_sante"
F_COMPTES_TPA = "comptes_tpa"
F_COMPTES_UTILISATEURS = "comptes_utilisateurs"
F_PRODUCTION = "production"
F_SINISTRES = "sinistres"
F_ENCAISSEMENT_PRIME = "encaissement_prime"
F_REMBOURSEMENT = "remboursement"
F_PAIEMENT_CESSION_REASSURANCE = "paiement_cession_reassurance"
F_PAIEMENT_RETENTION_ASSUREUR = "paiement_retention_assureur"
F_PAIEMENT_COMMISSION_CESSION = "paiement_commission_cession"
F_PAIEMENT_COMMISSION_COURTAGE = "paiement_commission_courtage"
F_PAIEMENT_COUT_POLICE = "paiement_cout_police"
F_PAIEMENT_TAXE = "paiement_taxe"
F_PAIEMENT_TAXE_ADDITIONNELLE = "paiement_taxe_additionnelle"
F_RETROCESSION_MHC = "retrocession_mhc"
F_ENCAISSEMENT_QUOTE_PART_SINISTRE = "encaissement_quote_part_sinistre"
F_PAIEMENT_SINISTRE = "paiement_sinistre"
F_ALERTE_SOS = "alerte_sos"
F_PRISE_EN_CHARGE = "prise_en_charge"
F_BULLETIN_SORTIE = "bulletin_sortie"
F_HOSPITALISATION = "hospitalisation"
F_RAPATRIEMENT = "rapatriement"
F_RAPPORT_MEDICAL = "rapport_medical"
F_FACTURATION_MEDICALE = "facturation_medicale"

FEATURES = [
    F_COMPTES_PRODUITS,
    F_COMPTES_ASSUREURS,
    F_COMPTES_REASSUREURS,
    F_COMPTES_INTERMEDIAIRES,
    F_COMPTES_MEDECINS_CONSEIL,
    F_COMPTES_PARTENAIRES_SANTE,
    F_COMPTES_TPA,
    F_COMPTES_UTILISATEURS,
    F_PRODUCTION,
    F_SINISTRES,
    F_ENCAISSEMENT_PRIME,
    F_REMBOURSEMENT,
    F_PAIEMENT_CESSION_REASSURANCE,
    F_PAIEMENT_RETENTION_ASSUREUR,
    F_PAIEMENT_COMMISSION_CESSION,
    F_PAIEMENT_COMMISSION_COURTAGE,
    F_PAIEMENT_COUT_POLICE,
    F_PAIEMENT_TAXE,
    F_PAIEMENT_TAXE_ADDITIONNELLE,
    F_RETROCESSION_MHC,
    F_ENCAISSEMENT_QUOTE_PART_SINISTRE,
    F_PAIEMENT_SINISTRE,
    F_ALERTE_SOS,
    F_PRISE_EN_CHARGE,
    F_BULLETIN_SORTIE,
    F_HOSPITALISATION,
    F_RAPATRIEMENT,
    F_RAPPORT_MEDICAL,
    F_FACTURATION_MEDICALE,
]

E = LEVEL_EDITION
K = LEVEL_CONTROLE
C = LEVEL_CONSULTATION

# Flux financiers sortants (pôles technique / comptabilité).
_FINANCE_FLOWS = [
    F_ENCAISSEMENT_PRIME,
    F_REMBOURSEMENT,
    F_PAIEMENT_CESSION_REASSURANCE,
    F_PAIEMENT_RETENTION_ASSUREUR,
    F_PAIEMENT_COMMISSION_CESSION,
    F_PAIEMENT_COMMISSION_COURTAGE,
    F_PAIEMENT_COUT_POLICE,
    F_PAIEMENT_TAXE,
    F_PAIEMENT_TAXE_ADDITIONNELLE,
    F_RETROCESSION_MHC,
    F_ENCAISSEMENT_QUOTE_PART_SINISTRE,
    F_PAIEMENT_SINISTRE,
]

# Comptes partenaires gérés par le pôle affaires médicales.
_MEDICAL_ACCOUNTS = [
    F_COMPTES_MEDECINS_CONSEIL,
    F_COMPTES_PARTENAIRES_SANTE,
    F_COMPTES_TPA,
]

# Comptes techniques gérés par le pôle production.
_TECH_ACCOUNTS = [
    F_COMPTES_PRODUITS,
    F_COMPTES_ASSUREURS,
    F_COMPTES_REASSUREURS,
    F_COMPTES_INTERMEDIAIRES,
]


def _perms(**kwargs) -> Dict[str, str]:
    return kwargs


def _with(features_levels: Dict[str, str], **overrides) -> Dict[str, str]:
    merged = dict(features_levels)
    merged.update(overrides)
    return merged


# --- Matrice par profil -----------------------------------------------------
# E = édition, K = contrôle (validation/conformité), C = consultation.

# Pôle technique — production / sinistres / supervision financière.
_SUPERVISEUR_TECHNIQUE = _perms(
    **{f: E for f in _TECH_ACCOUNTS},
    **{f: E for f in _FINANCE_FLOWS if f != F_PAIEMENT_SINISTRE},
    **{f: E for f in (F_PRODUCTION, F_SINISTRES)},
    **{f: C for f in (F_PAIEMENT_SINISTRE, F_ALERTE_SOS, F_FACTURATION_MEDICALE)},
)

_AGENT_PRODUCTION = _perms(
    **{f: C for f in _TECH_ACCOUNTS},
    **{f: E for f in _FINANCE_FLOWS if f not in (F_ENCAISSEMENT_QUOTE_PART_SINISTRE, F_PAIEMENT_SINISTRE)},
    **{f: C for f in (F_SINISTRES, F_ENCAISSEMENT_QUOTE_PART_SINISTRE, F_PAIEMENT_SINISTRE, F_FACTURATION_MEDICALE)},
    **{F_PRODUCTION: E},
)

_AGENT_CONFORMITE_PRODUCTION = _perms(
    **{f: K for f in _TECH_ACCOUNTS},
    **{f: K for f in _FINANCE_FLOWS if f not in (F_ENCAISSEMENT_QUOTE_PART_SINISTRE, F_PAIEMENT_SINISTRE)},
    **{f: C for f in (F_SINISTRES, F_ENCAISSEMENT_QUOTE_PART_SINISTRE, F_PAIEMENT_SINISTRE, F_FACTURATION_MEDICALE)},
    **{F_PRODUCTION: K},
)

_AGENT_SINISTRE = _perms(
    **{f: C for f in _TECH_ACCOUNTS},
    **{f: C for f in (F_PRODUCTION, F_ENCAISSEMENT_PRIME, F_REMBOURSEMENT, F_PAIEMENT_SINISTRE, F_ALERTE_SOS, F_FACTURATION_MEDICALE)},
    **{F_SINISTRES: E},
)

_AGENT_CONFORMITE_SINISTRE = _perms(
    **{f: C for f in _TECH_ACCOUNTS},
    **{f: C for f in _FINANCE_FLOWS if f != F_ENCAISSEMENT_QUOTE_PART_SINISTRE},
    **{f: C for f in (F_PRODUCTION,)},
    **{f: K for f in (F_SINISTRES, F_ENCAISSEMENT_QUOTE_PART_SINISTRE, F_ALERTE_SOS, F_FACTURATION_MEDICALE)},
)

# Pôle affaires médicales.
_SUPERVISEUR_AFFAIRES_MEDICALES = _perms(
    **{f: C for f in (F_PRODUCTION, F_SINISTRES, F_PAIEMENT_SINISTRE, F_BULLETIN_SORTIE)},
    **{f: E for f in _MEDICAL_ACCOUNTS},
    **{f: E for f in (F_ALERTE_SOS, F_PRISE_EN_CHARGE, F_HOSPITALISATION, F_RAPATRIEMENT)},
    **{f: K for f in (F_RAPPORT_MEDICAL, F_FACTURATION_MEDICALE)},
)

_AGENT_MEDICAL_MHC = _with(
    _SUPERVISEUR_AFFAIRES_MEDICALES,
    **{f: C for f in _MEDICAL_ACCOUNTS},
)

_AGENT_CONFORMITE_MEDICAL = _perms(
    **{f: C for f in (F_PRODUCTION, F_SINISTRES, F_PAIEMENT_SINISTRE)},
    **{f: K for f in _MEDICAL_ACCOUNTS},
    **{f: C for f in (F_ALERTE_SOS, F_PRISE_EN_CHARGE, F_BULLETIN_SORTIE, F_HOSPITALISATION, F_RAPATRIEMENT, F_RAPPORT_MEDICAL)},
    **{F_FACTURATION_MEDICALE: K},
)

# Pôle comptabilité et finances.
_SUPERVISEUR_COMPTABLE = _perms(
    **{f: C for f in _TECH_ACCOUNTS + _MEDICAL_ACCOUNTS},
    **{f: C for f in (F_PRODUCTION, F_SINISTRES, F_FACTURATION_MEDICALE)},
    **{f: E for f in _FINANCE_FLOWS},
)

_AGENT_COMPTABLE_MH = dict(_SUPERVISEUR_COMPTABLE)

_AGENT_CONFORMITE_COMPTABLE = _perms(
    **{f: C for f in _TECH_ACCOUNTS + _MEDICAL_ACCOUNTS},
    **{f: C for f in (F_PRODUCTION, F_SINISTRES, F_FACTURATION_MEDICALE)},
    **{f: K for f in _FINANCE_FLOWS},
)

# Profils externes — assureur / intermédiaire / réassureur.
_AGENT_PRODUCTION_PARTENAIRE = _perms(
    **{f: C for f in (F_SINISTRES, F_ENCAISSEMENT_PRIME, F_REMBOURSEMENT, F_PAIEMENT_SINISTRE)},
    **{F_PRODUCTION: E},
)

_ASSISTANT_SOUSCRIPTION = _perms(**{F_PRODUCTION: E})

_AGENT_SINISTRE_PARTENAIRE = _perms(
    **{f: C for f in (F_PRODUCTION, F_ENCAISSEMENT_PRIME, F_REMBOURSEMENT, F_PAIEMENT_SINISTRE)},
    **{F_SINISTRES: E},
)

_AGENT_COMPTABLE_PARTENAIRE = _perms(
    **{f: C for f in (F_PRODUCTION, F_SINISTRES, F_FACTURATION_MEDICALE)},
    **{f: E for f in (F_ENCAISSEMENT_PRIME, F_REMBOURSEMENT, F_PAIEMENT_SINISTRE)},
)

_AGENT_MEDICAL_ASSUREUR = _perms(
    **{f: C for f in (F_PRISE_EN_CHARGE, F_BULLETIN_SORTIE, F_HOSPITALISATION, F_RAPATRIEMENT, F_RAPPORT_MEDICAL, F_FACTURATION_MEDICALE)},
)

_AGENT_VERIFICATEUR_REASSUREUR = _perms(
    **{f: C for f in (F_SINISTRES, F_ENCAISSEMENT_PRIME, F_REMBOURSEMENT, F_ENCAISSEMENT_QUOTE_PART_SINISTRE)},
    **{F_PRODUCTION: E},
)

# Partenaires de santé / TPA (mêmes profils, structure différente).
_AGENT_MEDICAL_PARTENAIRE = _perms(
    **{f: E for f in (F_PRISE_EN_CHARGE, F_BULLETIN_SORTIE, F_HOSPITALISATION, F_RAPATRIEMENT, F_RAPPORT_MEDICAL)},
    **{F_FACTURATION_MEDICALE: C},
)

_AGENT_ACCUEIL_PARTENAIRE = _perms(
    **{f: C for f in (F_PRISE_EN_CHARGE, F_BULLETIN_SORTIE, F_HOSPITALISATION, F_RAPATRIEMENT, F_FACTURATION_MEDICALE)},
    **{F_ALERTE_SOS: E},
)

_AGENT_COMPTABLE_PARTENAIRE_SANTE = _perms(**{F_FACTURATION_MEDICALE: E})

# Médecin-conseil : première validation de la chaîne médicale.
_MEDECIN_CONSEIL = _perms(
    **{f: E for f in (F_ALERTE_SOS, F_PRISE_EN_CHARGE, F_RAPATRIEMENT)},
    **{f: K for f in (F_HOSPITALISATION, F_RAPPORT_MEDICAL, F_FACTURATION_MEDICALE)},
    **{F_BULLETIN_SORTIE: C},
)

# Vue d'ensemble pour l'administrateur d'un établissement de santé.
_HOSPITAL_ADMIN = _perms(
    **{f: C for f in (F_ALERTE_SOS, F_PRISE_EN_CHARGE, F_BULLETIN_SORTIE, F_HOSPITALISATION, F_RAPATRIEMENT, F_RAPPORT_MEDICAL, F_FACTURATION_MEDICALE)},
)

ROLE_PERMISSIONS: Dict[str, Dict[str, str]] = {
    # Internes MHC
    "superviseur_technique": _SUPERVISEUR_TECHNIQUE,
    "production_agent": _AGENT_PRODUCTION,
    "agent_conformite_production": _AGENT_CONFORMITE_PRODUCTION,
    "agent_sinistre_mh": _AGENT_SINISTRE,
    "agent_conformite_sinistre": _AGENT_CONFORMITE_SINISTRE,
    "superviseur_affaires_medicales": _SUPERVISEUR_AFFAIRES_MEDICALES,
    "agent_medical_mhc": _AGENT_MEDICAL_MHC,
    "agent_conformite_medical": _AGENT_CONFORMITE_MEDICAL,
    "superviseur_comptable": _SUPERVISEUR_COMPTABLE,
    "agent_comptable_mh": _AGENT_COMPTABLE_MH,
    "agent_conformite_comptable": _AGENT_CONFORMITE_COMPTABLE,
    # Externes — assureur / intermédiaire / réassureur
    "agent_production_assureur": _AGENT_PRODUCTION_PARTENAIRE,
    "agent_production_courtier": _AGENT_PRODUCTION_PARTENAIRE,
    "assistant_souscription": _ASSISTANT_SOUSCRIPTION,
    "agent_sinistre_assureur": _AGENT_SINISTRE_PARTENAIRE,
    "agent_sinistre_courtier": _AGENT_SINISTRE_PARTENAIRE,
    "agent_comptable_assureur": _AGENT_COMPTABLE_PARTENAIRE,
    "agent_comptable_courtier": _AGENT_COMPTABLE_PARTENAIRE,
    "agent_medical_assureur": _AGENT_MEDICAL_ASSUREUR,
    "agent_verificateur_reassureur": _AGENT_VERIFICATEUR_REASSUREUR,
    # Partenaires de santé / TPA
    "medecin_hopital": _AGENT_MEDICAL_PARTENAIRE,
    "agent_reception_hopital": _AGENT_ACCUEIL_PARTENAIRE,
    "agent_comptable_hopital": _AGENT_COMPTABLE_PARTENAIRE_SANTE,
    "hospital_admin": _HOSPITAL_ADMIN,
    # Médecin-conseil
    "medecin_referent_mh": _MEDECIN_CONSEIL,
    # Rôles historiques rapprochés des profils cibles
    "sos_operator": _AGENT_MEDICAL_MHC,
    "medical_reviewer": _AGENT_CONFORMITE_MEDICAL,
    "technical_reviewer": _AGENT_CONFORMITE_PRODUCTION,
    "finance_manager": _SUPERVISEUR_COMPTABLE,
    # Assuré / médecin legacy : aucun accès back-office
    "user": {},
    "doctor": {},
}

ROLE_LABELS: Dict[str, str] = {
    "admin": "Administrateur MHC",
    "superviseur_technique": "Superviseur technique",
    "production_agent": "Agent de production",
    "agent_conformite_production": "Agent conformité production",
    "agent_sinistre_mh": "Agent sinistre",
    "agent_conformite_sinistre": "Agent conformité sinistre",
    "superviseur_affaires_medicales": "Superviseur affaires médicales",
    "agent_medical_mhc": "Agent médical MHC",
    "agent_conformite_medical": "Agent conformité médical",
    "superviseur_comptable": "Superviseur comptabilité et finances",
    "agent_comptable_mh": "Agent comptable",
    "agent_conformite_comptable": "Agent conformité comptable",
    "agent_production_assureur": "Agent de production (assureur)",
    "agent_production_courtier": "Agent de production (intermédiaire)",
    "assistant_souscription": "Assistant de souscription",
    "agent_sinistre_assureur": "Agent sinistre (assureur)",
    "agent_sinistre_courtier": "Agent sinistre (intermédiaire)",
    "agent_comptable_assureur": "Agent comptable (assureur)",
    "agent_comptable_courtier": "Agent comptable (intermédiaire)",
    "agent_comptable_hopital": "Agent comptable (partenaire santé)",
    "agent_medical_assureur": "Agent médical (assureur)",
    "agent_verificateur_reassureur": "Agent vérificateur (réassureur)",
    "hospital_admin": "Administrateur partenaire santé",
    "medecin_hopital": "Agent médical (partenaire santé / TPA)",
    "agent_reception_hopital": "Agent d'accueil (partenaire santé / TPA)",
    "medecin_referent_mh": "Médecin-conseil",
    "sos_operator": "Opérateur SOS",
    "medical_reviewer": "Validateur médical",
    "technical_reviewer": "Validateur technique",
    "finance_manager": "Responsable finance",
    "doctor": "Médecin",
    "user": "Assuré",
}


def _normalize_level(level: Optional[str]) -> str:
    if not level:
        return LEVEL_NONE
    return level if level in _LEVEL_ORDER else LEVEL_NONE


def permissions_for_role(role: Optional[str]) -> Dict[str, str]:
    """Matrice effective d'un profil. `admin` reçoit toutes les fonctionnalités."""
    role_key = (role or "user").strip().lower()
    if role_key == "admin":
        return {f: LEVEL_EDITION for f in FEATURES}
    return dict(ROLE_PERMISSIONS.get(role_key, {}))


def permission_level(role: Optional[str], feature: str) -> str:
    return _normalize_level(permissions_for_role(role).get(feature))


def has_permission(role: Optional[str], feature: str, min_level: str = LEVEL_CONSULTATION) -> bool:
    return _LEVEL_ORDER[permission_level(role, feature)] >= _LEVEL_ORDER[_normalize_level(min_level)]


def require_permission(feature: str, min_level: str = LEVEL_CONSULTATION):
    """Dependency FastAPI : exige `feature` au niveau `min_level` (ou plus)."""
    # Import paresseux pour éviter la circularité avec app.api.v1.auth.
    from fastapi import Depends, HTTPException, status
    from app.api.v1.auth import get_current_user

    def _check(current_user=Depends(get_current_user)):
        role = getattr(current_user, "role", "user")
        if hasattr(role, "value"):
            role = role.value
        if not has_permission(str(role), feature, min_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission insuffisante : {feature} ({min_level}) requis.",
            )
        return current_user

    return _check
