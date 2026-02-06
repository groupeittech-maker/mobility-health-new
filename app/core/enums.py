from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    DOCTOR = "doctor"
    HOSPITAL_ADMIN = "hospital_admin"
    FINANCE_MANAGER = "finance_manager"
    SOS_OPERATOR = "sos_operator"
    MEDICAL_REVIEWER = "medical_reviewer"
    TECHNICAL_REVIEWER = "technical_reviewer"
    PRODUCTION_AGENT = "production_agent"
    AGENT_COMPTABLE_MH = "agent_comptable_mh"
    AGENT_COMPTABLE_ASSUREUR = "agent_comptable_assureur"
    AGENT_COMPTABLE_HOPITAL = "agent_comptable_hopital"
    AGENT_SINISTRE_MH = "agent_sinistre_mh"
    AGENT_SINISTRE_ASSUREUR = "agent_sinistre_assureur"
    AGENT_RECEPTION_HOPITAL = "agent_reception_hopital"
    MEDECIN_REFERENT_MH = "medecin_referent_mh"
    MEDECIN_HOPITAL = "medecin_hopital"


class StatutSouscription(str, Enum):
    """Statut d'une souscription"""
    EN_ATTENTE = "en_attente"
    PENDING = "pending"  # Alias pour en_attente, utilisé pour les nouvelles souscriptions
    ACTIVE = "active"
    SUSPENDUE = "suspendue"
    RESILIEE = "resiliee"
    EXPIREE = "expiree"


class StatutPaiement(str, Enum):
    """Statut d'un paiement"""
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    VALIDE = "valide"
    ECHOUE = "echoue"
    REMBOURSE = "rembourse"


class TypePaiement(str, Enum):
    """Type de paiement"""
    CARTE_BANCAIRE = "carte_bancaire"
    VIREMENT = "virement"
    MOBILE_MONEY_AIRTEL = "mobile_money_airtel"
    MOBILE_MONEY_MTN = "mobile_money_mtn"
    MOBILE_MONEY_ORANGE = "mobile_money_orange"
    MOBILE_MONEY_MOOV = "mobile_money_moov"
    PAIEMENT_DIFFERE = "paiement_differe"
    PRELEVEMENT = "prelevement"
    ESPECES = "especes"
    CHEQUE = "cheque"


class StatutProjetVoyage(str, Enum):
    """Statut d'un projet de voyage"""
    EN_PLANIFICATION = "en_planification"
    CONFIRME = "confirme"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    ANNULE = "annule"


class QuestionnaireType(str, Enum):
    """Préférence de questionnaire médical"""
    SHORT = "short"
    LONG = "long"


class CleRepartition(str, Enum):
    """Clé de répartition pour les produits d'assurance"""
    PAR_PERSONNE = "par_personne"
    PAR_GROUPE = "par_groupe"
    PAR_DUREE = "par_duree"
    PAR_DESTINATION = "par_destination"
    FIXE = "fixe"


class CategorieAssure(str, Enum):
    """Catégories d'assurés"""
    INDIVIDUEL = "individuel"
    FAMILLE = "famille"
    GROUPE = "groupe"
    ENTREPRISE = "entreprise"


class StatutWorkflowSinistre(str, Enum):
    """Statut des étapes du flux sinistre"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"