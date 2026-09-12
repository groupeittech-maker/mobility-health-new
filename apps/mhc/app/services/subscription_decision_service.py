"""Moteur de décision automatique pour la souscription MHC.

Le moteur évalue un dossier juste après la soumission du formulaire / questionnaire.
Trois sorties possibles :
- APPROVE  -> statut EN_ATTENTE_PAIEMENT
- REJECT   -> statut REFUSEE
- REVIEW   -> statut EN_ATTENTE_VALIDATION, avec routage vers la bonne étape
              du pipeline existant (medical, technical, production).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import StatutSouscription
from app.models.paiement import Paiement
from app.models.produit_assurance import ProduitAssurance
from app.models.projet_voyage import ProjetVoyage
from app.models.questionnaire import Questionnaire
from app.models.souscription import Souscription
from app.models.user import User
from app.services.medical_eligibility import MedicalEligibilityError, validate_medical_eligibility

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Règles métier paramétrables
# ---------------------------------------------------------------------------
MEDICAL_REVIEW_KEYS = [
    "enceinte",
    "grossesse",
    "pregnancy",
    "mois_grossesse",
    "moisGrossesse",
]

MEDICAL_REVIEW_HINTS = [
    "maladie chronique",
    "chronique",
    "diabete",
    "hypertension",
    "asthme severe",
    "opere",
    "operation",
    "chirurgie",
    "greffe",
    "insuffisance",
    "cardiaque",
    "epilepsie",
    "thrombose",
    "embolie",
    "cancer",
    "tumeur",
]

MEDICAL_REJECTION_HINTS = [
    "dialyse",
    "insuffisance renale",
    "cancer en cours",
    "cancer actif",
    "sida",
    "transplantation",
    "greffe recente",
    "maladie terminale",
    "hospitalisation prolongee",
]

TECHNICAL_REVIEW_HINTS = [
    "long sejour",
    "plus de 30 jours",
    "groupe",
    "famille nombreuse",
    "entreprise",
    "business",
    "affaires",
    "sport extreme",
    "sport a risque",
    "derogation",
    "demande speciale",
]

PRODUCTION_REVIEW_HINTS = [
    "entreprise",
    "societe",
    "groupe",
    "business",
    "affaires",
    "sport extreme",
    "aventure",
    "montagne",
    "plongee",
    "parachutisme",
]

REVIEW_STEP_ORDER = ["medical", "production"]

# Clés (normalisées : minuscules, sans séparateurs) des questions médicales
# oui/non dont une réponse affirmative impose une revue médicale.
MEDICAL_DECLARATION_KEYS = {
    "maladesouscription",      # malade au moment de la souscription
    "malade12mois",            # malade au cours des 12 derniers mois
    "maladiechronique",        # maladie chronique
    "maladieschroniques",
    "traitementsencours",
    "traitementmedical",
    "hospitalisation12mois",
    "maladiescontagieuses",
    "contactpersonnemalade",
    "antecedentsrecents",
    "voyagemedical",           # voyage à but médical
}


def _normalized_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _is_affirmative(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return value.strip().lower() in {"oui", "yes", "true", "vrai", "1"}
    return False


# ---------------------------------------------------------------------------
# Structures de retour
# ---------------------------------------------------------------------------
@dataclass
class DecisionResult:
    decision: str  # approve | reject | review
    primary_step: Optional[str] = None  # medical | production
    review_steps: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    risk_score: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _age_from_birthdate(birthdate: Optional[date]) -> Optional[int]:
    if not birthdate:
        return None
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def _trip_duration_days(project: Optional[ProjetVoyage]) -> Optional[int]:
    if not project or not project.date_depart or not project.date_retour:
        return None
    return (project.date_retour - project.date_depart).days


def _latest_medical_questionnaire(db: Session, souscription_id: int) -> Optional[Questionnaire]:
    if db is None:
        return None
    return (
        db.query(Questionnaire)
        .filter(
            Questionnaire.souscription_id == souscription_id,
            Questionnaire.type_questionnaire == "medical",
            Questionnaire.statut == "complete",
        )
        .order_by(Questionnaire.version.desc())
        .first()
    )


def _latest_administrative_questionnaire(db: Session, souscription_id: int) -> Optional[Questionnaire]:
    if db is None:
        return None
    return (
        db.query(Questionnaire)
        .filter(
            Questionnaire.souscription_id == souscription_id,
            Questionnaire.type_questionnaire == "administratif",
            Questionnaire.statut == "complete",
        )
        .order_by(Questionnaire.version.desc())
        .first()
    )


def _parse_birthdate(value: Any) -> Optional[date]:
    """Parse une date de naissance depuis string/ISO."""
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _voyageur_age(
    user: Optional[User],
    admin_questionnaire: Optional[Questionnaire],
    medical_questionnaire: Optional[Questionnaire],
    projet: Optional[ProjetVoyage] = None,
    voyageur_age: Optional[int] = None,
    voyageur_date_naissance: Optional[date] = None,
) -> Optional[int]:
    """
    Détermine l'âge du voyageur assuré (pas forcément l'abonné).
    Priorité : paramètre > date de naissance paramètre > questionnaire administratif
    > notes du projet > questionnaire médical > abonné.
    """
    if voyageur_age is not None:
        return voyageur_age
    if voyageur_date_naissance:
        return _age_from_birthdate(voyageur_date_naissance)

    # Si le questionnaire administratif désigne un voyageur tiers (enfant, etc.)
    admin = admin_questionnaire
    if admin and admin.reponses and isinstance(admin.reponses, dict):
        personal = admin.reponses.get("personal") or {}
        if isinstance(personal, dict):
            is_tier = admin.reponses.get("travelerType") == "child" or admin.reponses.get("isChildOnly") is True
            name = personal.get("fullName")
            if is_tier or (name and user and name != user.full_name):
                birth = _parse_birthdate(personal.get("birthDate"))
                if birth:
                    return _age_from_birthdate(birth)

    # Repli sur les notes du projet (format tier pour mobile/web)
    if projet and getattr(projet, "notes", None):
        notes = str(projet.notes)
        if "=== INFORMATIONS DU TIERS (BÉNÉFICIAIRE) ===" in notes or "Pour un tiers" in notes:
            match = re.search(r'Date de naissance du tiers[:\s]+([^\n]+)', notes, re.IGNORECASE)
            if not match:
                match = re.search(r'birthdate[:\s]+([^\n]+)', notes, re.IGNORECASE)
            if match:
                birth = _parse_birthdate(match.group(1).strip())
                if birth:
                    return _age_from_birthdate(birth)

    # Repli sur le questionnaire médical
    med = medical_questionnaire
    if med and med.reponses and isinstance(med.reponses, dict):
        personal = med.reponses.get("personal") or {}
        if isinstance(personal, dict):
            birth = _parse_birthdate(personal.get("birthDate"))
            if birth:
                return _age_from_birthdate(birth)

    return _age_from_birthdate(user.date_naissance if user else None)


def _is_subscriber_minor(user: Optional[User]) -> bool:
    age = _age_from_birthdate(user.date_naissance if user else None)
    return age is not None and age < 18


# Clés dont la valeur ne doit jamais alimenter la détection d'indices médicaux :
# photos base64, documents, identité — sinon un blob base64 (ou un nom comme
# « Sida ») déclenche aléatoirement les hints (« sida », « cancer »…).
_FLAT_SKIP_KEY_TOKENS = (
    "photo", "image", "base64", "file", "fichier", "document",
    "fullname", "full_name", "birthdate", "date_naissance", "datenaissance",
    "email", "telephone", "phone", "passport", "signature",
)


def _flatten_reponses(reponses: Any) -> list[str]:
    """Aplatit un dict de réponses en liste de chaînes normalisées."""
    result: list[str] = []
    if not reponses:
        return result

    def _walk(value: Any, key: str = ""):
        k = _normalized_key(key)
        if any(tok in k for tok in _FLAT_SKIP_KEY_TOKENS):
            return
        if isinstance(value, dict):
            for k2, v in value.items():
                _walk(v, k2)
        elif isinstance(value, list):
            for item in value:
                _walk(item)
        elif value is not None:
            s = str(value).lower().strip()
            if s.startswith("data:"):
                return
            # Blob encodé (base64/hex long sans espace) : jamais une réponse médicale
            if len(s) > 300 and " " not in s:
                return
            result.append(s)

    _walk(reponses)
    return result


def _contains_any(texts: list[str], hints: list[str]) -> bool:
    joined = " ".join(texts)
    return any(hint in joined for hint in hints)


_NEGATION_PREFIXES = ("non", "pas", "no ", "not ", "aucun", "aucune")


def _is_pregnancy_positive(value: Any, *, free_text: bool = False) -> bool:
    """
    Détection affirmative de grossesse. Les formulaires envoient toujours la clé
    « enceinte »/« pregnancy » — il faut regarder la valeur, pas la présence.

    - free_text=False (clé grossesse dédiée) : « oui », true, 1, mois > 0, ou
      texte mentionnant la grossesse → positif.
    - free_text=True (valeur quelconque du questionnaire) : uniquement un texte
      mentionnant la grossesse (un simple « oui » sur une autre question ne
      doit pas déclencher la revue).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        t = value.strip().lower()
        if not t or t.startswith(_NEGATION_PREFIXES) or "pas de grossesse" in t or "non enceinte" in t:
            return False
        if "enceinte" in t or "grossesse" in t or "pregnant" in t:
            return True
        return not free_text and t in {"oui", "yes", "true", "vrai", "1"}
    return False


def _destination_excluded(destination: str, product: ProduitAssurance) -> bool:
    zones = product.zones_geographiques or {}
    excluded = zones.get("pays_exclus") or zones.get("excluded") or []
    return destination.lower() in [str(z).lower() for z in excluded]


# ---------------------------------------------------------------------------
# Moteur
# ---------------------------------------------------------------------------
class SubscriptionDecisionEngine:
    """Décision automatique d'acceptation / refus / revue d'une souscription."""

    @staticmethod
    def evaluate(
        db: Session,
        souscription: Souscription,
        *,
        user: Optional[User] = None,
        product: Optional[ProduitAssurance] = None,
        project: Optional[ProjetVoyage] = None,
        questionnaire: Optional[Questionnaire] = None,
        admin_questionnaire: Optional[Questionnaire] = None,
        voyageur_age: Optional[int] = None,
        voyageur_date_naissance: Optional[date] = None,
    ) -> DecisionResult:
        """
        Évalue le dossier et met à jour la souscription (statut + validations pending).
        Ne fait pas de commit : l'appelant reste maître de la transaction.
        """
        if souscription.statut in {
            StatutSouscription.ACTIVE,
            StatutSouscription.RESILIEE,
            StatutSouscription.REFUSEE,
            StatutSouscription.EXPIREE,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La souscription est déjà dans un état terminal",
            )

        # Idempotence : un dossier déjà approuvé ou déjà en revue renvoie son
        # état actuel sans ré-évaluer (ni réinitialiser les validations faites).
        if souscription.statut == StatutSouscription.EN_ATTENTE_PAIEMENT:
            return DecisionResult(decision="approve", reasons=["Dossier déjà approuvé"])
        if souscription.statut == StatutSouscription.EN_ATTENTE_VALIDATION:
            pending = [
                step
                for step in REVIEW_STEP_ORDER
                if getattr(souscription, {
                    "medical": "validation_medicale",
                    "production": "validation_finale",
                }[step]) == "pending"
            ]
            # Dossier legacy « technique » (validation_technique pending) →
            # désormais traité par l'agent de production.
            if (
                "production" not in pending
                and souscription.validation_technique == "pending"
            ):
                pending.append("production")
            return DecisionResult(
                decision="review",
                primary_step=pending[0] if pending else None,
                review_steps=pending,
                reasons=["Dossier déjà en cours de validation humaine"],
            )

        user = user or souscription.user
        product = product or souscription.produit_assurance
        project = project or souscription.projet_voyage
        questionnaire = questionnaire or _latest_medical_questionnaire(db, souscription.id)
        admin_questionnaire = admin_questionnaire or _latest_administrative_questionnaire(db, souscription.id)

        reponses = questionnaire.reponses if questionnaire else {}
        flat = _flatten_reponses(reponses)

        reasons: list[str] = []
        review_steps: set[str] = set()

        # Le souscripteur (détenteur du compte) doit être majeur ; le voyageur peut être un enfant.
        if _is_subscriber_minor(user):
            reasons.append("Le souscripteur doit être majeur. Un enfant mineur ne peut pas souscrire seul.")
            return SubscriptionDecisionEngine._apply_reject(souscription, reasons)

        age = _voyageur_age(user, admin_questionnaire, questionnaire, project, voyageur_age, voyageur_date_naissance)

        # 1. Règles de refus dur
        if age is not None and product.age_minimum is not None and age < product.age_minimum:
            reasons.append(f"Âge du voyageur inférieur au minimum ({age} < {product.age_minimum})")
            return SubscriptionDecisionEngine._apply_reject(souscription, reasons)

        if age is not None and product.age_maximum is not None and age > product.age_maximum:
            reasons.append(f"Âge du voyageur supérieur au maximum ({age} > {product.age_maximum})")
            return SubscriptionDecisionEngine._apply_reject(souscription, reasons)

        try:
            validate_medical_eligibility(reponses)
        except MedicalEligibilityError as exc:
            reasons.append(str(exc))
            return SubscriptionDecisionEngine._apply_reject(souscription, reasons)

        duration = _trip_duration_days(project)
        if duration is not None and product.duree_max_jours is not None and duration > product.duree_max_jours:
            reasons.append(f"Durée supérieure au maximum ({duration} > {product.duree_max_jours} jours)")
            return SubscriptionDecisionEngine._apply_reject(souscription, reasons)

        if project and _destination_excluded(project.destination, product):
            reasons.append(f"Destination exclue du produit ({project.destination})")
            return SubscriptionDecisionEngine._apply_reject(souscription, reasons)

        if _contains_any(flat, MEDICAL_REJECTION_HINTS):
            for hint in MEDICAL_REJECTION_HINTS:
                if hint in " ".join(flat):
                    reasons.append(f"Condition médicale à exclusion automatique détectée ({hint})")
                    break
            return SubscriptionDecisionEngine._apply_reject(souscription, reasons)

        # 2. Règles de revue
        # Médical — grossesse : uniquement si la réponse est affirmative
        # (la clé « enceinte » est toujours envoyée par les formulaires, y compris avec « non »).
        pregnant = any(_is_pregnancy_positive(reponses.get(k)) for k in MEDICAL_REVIEW_KEYS) or any(
            _is_pregnancy_positive(t, free_text=True) for t in flat
        )
        if pregnant:
            review_steps.add("medical")
            reasons.append("Grossesse déclarée : revue médicale requise")

        if age is not None and age >= 70:
            review_steps.add("medical")
            reasons.append(f"Assuré âgé de {age} ans : revue médicale requise")

        # Réponses « oui » aux questions médicales structurées → revue médicale
        if isinstance(reponses, dict) and any(
            _is_affirmative(v)
            for k, v in reponses.items()
            if _normalized_key(k) in MEDICAL_DECLARATION_KEYS
        ):
            review_steps.add("medical")
            reasons.append("Condition médicale déclarée (réponse « oui ») : revue médicale requise")

        if _contains_any(flat, MEDICAL_REVIEW_HINTS):
            review_steps.add("medical")
            reasons.append("Antécédent / condition médicale déclarée : revue médicale requise")

        # Revue production (agent de production) — ex-« technique » fusionnée
        if duration is not None and duration > 30:
            review_steps.add("production")
            reasons.append(f"Séjour long ({duration} jours) : revue production requise")

        if project and project.nombre_participants and project.nombre_participants > 1:
            review_steps.add("production")
            reasons.append("Plusieurs participants : revue production requise")

        if souscription.prix_applique is not None and souscription.prix_applique > 200000:
            review_steps.add("production")
            reasons.append("Montant élevé : revue production requise")

        if _contains_any(flat, TECHNICAL_REVIEW_HINTS):
            review_steps.add("production")
            reasons.append("Indicateur technique détecté : revue production requise")

        # Production
        if _contains_any(flat, PRODUCTION_REVIEW_HINTS):
            review_steps.add("production")
            reasons.append("Indicateur production / dérogation détecté : revue production requise")

        if review_steps:
            ordered = [s for s in REVIEW_STEP_ORDER if s in review_steps]
            return SubscriptionDecisionEngine._apply_review(souscription, ordered, reasons, db)

        # 3. Acceptation automatique
        return SubscriptionDecisionEngine._apply_approve(souscription, reasons)

    # -----------------------------------------------------------------------
    # Application des décisions
    # -----------------------------------------------------------------------
    @staticmethod
    def _apply_reject(souscription: Souscription, reasons: list[str]) -> DecisionResult:
        souscription.statut = StatutSouscription.REFUSEE
        souscription.validation_medicale = "rejected"
        souscription.validation_technique = "rejected"
        souscription.validation_finale = "rejected"
        logger.info(
            "Souscription %s refusée automatiquement : %s",
            souscription.id,
            "; ".join(reasons),
        )
        return DecisionResult(decision="reject", reasons=reasons, risk_score=100)

    # Étape de revue → rôles habilités (même matrice que l'UI de revue existante)
    _REVIEW_STEP_ROLES = {
        "medical": ("MEDICAL_REVIEWER", "DOCTOR", "MEDECIN_REFERENT_MH"),
        "production": ("PRODUCTION_AGENT",),
    }
    _REVIEW_STEP_LABELS = {
        "medical": "médicale",
        "production": "de production",
    }

    @staticmethod
    def _dispatch_to_review_pipeline(
        db: Optional[Session],
        souscription: Souscription,
        primary_step: str,
    ) -> None:
        """
        Rend le dossier visible dans le pipeline de revue (souscription-based) :
        notifie les relecteurs habilités pour l'étape en cours. La file de revue
        lit les souscriptions EN_ATTENTE_VALIDATION — pas d'attestation ici.
        Ne lève jamais d'exception.
        """
        if db is None:
            return
        try:
            from app.core.enums import Role
            from app.services.notification_service import NotificationService

            role_names = SubscriptionDecisionEngine._REVIEW_STEP_ROLES.get(primary_step, ())
            roles = [r for r in Role if r.value in role_names or r.name in role_names]
            if not roles:
                return
            reviewers = (
                db.query(User)
                .filter(User.role.in_(roles), User.is_active == True)  # noqa: E712
                .all()
            )
            label = SubscriptionDecisionEngine._REVIEW_STEP_LABELS.get(primary_step, primary_step)
            for reviewer in reviewers:
                NotificationService.create_notification(
                    user_id=reviewer.id,
                    type_notification="souscription_review",
                    titre=f"Dossier à valider — revue {label}",
                    message=(
                        f"La souscription #{souscription.numero_souscription} a été "
                        f"routée en revue {label} par le moteur de décision. "
                        "Merci de procéder à l'évaluation."
                    ),
                    lien_relation_id=souscription.id,
                    lien_relation_type="souscription",
                    channels=["push"],
                )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Notification relecteurs impossible pour souscription %s: %s",
                getattr(souscription, "id", "?"),
                exc,
            )

    @staticmethod
    def _apply_review(
        souscription: Souscription,
        review_steps: list[str],
        reasons: list[str],
        db: Optional[Session] = None,
    ) -> DecisionResult:
        souscription.statut = StatutSouscription.EN_ATTENTE_VALIDATION
        souscription.validation_medicale = None
        souscription.validation_technique = None
        souscription.validation_finale = None
        for step in review_steps:
            if step == "medical":
                souscription.validation_medicale = "pending"
            elif step == "production":
                souscription.validation_finale = "pending"

        SubscriptionDecisionEngine._dispatch_to_review_pipeline(db, souscription, review_steps[0])

        risk_score = 30 + min(len(review_steps) * 20, 50)
        logger.info(
            "Souscription %s envoyée en revue %s : %s",
            souscription.id,
            review_steps,
            "; ".join(reasons),
        )
        return DecisionResult(
            decision="review",
            primary_step=review_steps[0],
            review_steps=review_steps,
            reasons=reasons,
            risk_score=risk_score,
        )

    @staticmethod
    def _apply_approve(souscription: Souscription, reasons: list[str]) -> DecisionResult:
        souscription.statut = StatutSouscription.EN_ATTENTE_PAIEMENT
        souscription.validation_medicale = "approved"
        souscription.validation_technique = "approved"
        souscription.validation_finale = "approved"
        logger.info(
            "Souscription %s approuvée automatiquement, en attente de paiement",
            souscription.id,
        )
        return DecisionResult(decision="approve", reasons=reasons, risk_score=0)

    # -----------------------------------------------------------------------
    # Gestion du pipeline de revue
    # -----------------------------------------------------------------------
    @staticmethod
    def record_review(
        db: Session,
        souscription: Souscription,
        step: str,
        approved: bool,
        validator_user_id: int,
        notes: Optional[str] = None,
    ) -> DecisionResult:
        """
        Enregistre le résultat d'une étape de revue et avance le workflow.
        step ∈ {"medical", "production"}
        """
        now = datetime.utcnow()
        if step == "medical":
            if souscription.validation_medicale != "pending":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Revue médicale non en attente",
                )
            souscription.validation_medicale = "approved" if approved else "rejected"
            souscription.validation_medicale_par = validator_user_id
            souscription.validation_medicale_date = now
            souscription.validation_medicale_notes = notes
        elif step == "production":
            # Compat : dossiers routés « technique » avant fusion des étapes —
            # l'agent de production statue aussi sur validation_technique.
            if (
                souscription.validation_finale != "pending"
                and souscription.validation_technique != "pending"
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Approbation finale non en attente",
                )
            if souscription.validation_technique == "pending":
                souscription.validation_technique = "approved" if approved else "rejected"
                souscription.validation_technique_par = validator_user_id
                souscription.validation_technique_date = now
                souscription.validation_technique_notes = notes
            souscription.validation_finale = "approved" if approved else "rejected"
            souscription.validation_finale_par = validator_user_id
            souscription.validation_finale_date = now
            souscription.validation_finale_notes = notes
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Étape de revue inconnue : {step}",
            )

        if not approved:
            souscription.statut = StatutSouscription.REFUSEE
            SubscriptionDecisionEngine._notify_client_outcome(
                db, souscription, approved=False, notes=notes
            )
            return DecisionResult(
                decision="reject",
                reasons=[f"Revue {step} rejetée" + (f" ({notes})" if notes else "")],
                risk_score=100,
            )

        # Détermine la prochaine étape encore pending
        attr_map = {
            "medical": "validation_medicale",
            "production": "validation_finale",
        }
        for next_step in REVIEW_STEP_ORDER:
            val = getattr(souscription, attr_map[next_step])
            if val == "pending":
                souscription.statut = StatutSouscription.EN_ATTENTE_VALIDATION
                return DecisionResult(
                    decision="review",
                    primary_step=next_step,
                    reasons=[f"Revue {step} approuvée, en attente de {next_step}"],
                )

        # Toutes les revues sont approuvées : le dossier peut payer
        souscription.statut = StatutSouscription.EN_ATTENTE_PAIEMENT
        SubscriptionDecisionEngine._notify_client_outcome(db, souscription, approved=True)
        return DecisionResult(
            decision="approve",
            reasons=[f"Revue {step} approuvée, dossier prêt pour paiement"],
            risk_score=0,
        )

    @staticmethod
    def _notify_client_outcome(
        db: Optional[Session],
        souscription: Souscription,
        approved: bool,
        notes: Optional[str] = None,
    ) -> None:
        """Informe le client de l'issue de la revue humaine de son dossier."""
        if db is None:
            return
        try:
            from app.services.notification_service import NotificationService

            if approved:
                titre = "Dossier approuvé — paiement disponible"
                message = (
                    f"Votre souscription #{souscription.numero_souscription} a été approuvée "
                    "par la revue. Vous pouvez procéder au paiement."
                )
            else:
                titre = "Dossier refusé"
                message = (
                    f"Votre souscription #{souscription.numero_souscription} a été refusée "
                    "après revue. Contactez le service client pour plus d'informations."
                )
                if notes:
                    message += f" Motif : {notes}"
            NotificationService.create_notification(
                user_id=souscription.user_id,
                type_notification="souscription_decision_result",
                titre=titre,
                message=message,
                lien_relation_id=souscription.id,
                lien_relation_type="souscription",
                channels=["push"],
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "Notification client décision impossible pour souscription %s: %s",
                getattr(souscription, "id", "?"),
                exc,
            )
