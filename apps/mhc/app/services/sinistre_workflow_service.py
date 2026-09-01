from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.enums import StatutWorkflowSinistre
from app.models.alerte import Alerte
from app.models.sinistre import Sinistre
from app.models.sinistre_process_step import SinistreProcessStep
from app.models.invoice import InvoiceStatus

SINISTRE_WORKFLOW_TEMPLATE: List[Dict] = [
    {
        "key": "alerte_declenchee",
        "ordre": 1,
        "titre": "Déclenchement de l'alerte",
        "description": "L'assuré déclenche une alerte via la plateforme ou le numéro d'urgence.",
        "auto_sync": True,
    },
    {
        "key": "centre_ops_notifie",
        "ordre": 2,
        "titre": "Centre des opérations alerté",
        "description": "Le centre des opérations MHC reçoit et accuse réception de l'alarme.",
        "auto_sync": True,
    },
    {
        "key": "medecin_notifie",
        "ordre": 3,
        "titre": "Médecin référent notifié",
        "description": "Le médecin référent local reçoit l'alarme sur son téléphone.",
        "auto_sync": True,
    },
    {
        "key": "localisation_assure",
        "ordre": 4,
        "titre": "Localisation de l'assuré",
        "description": "Centre des opérations et médecin localisent l'assuré par géolocalisation ou tout autre moyen.",
        "auto_sync": True,
    },
    {
        "key": "activation_hopital",
        "ordre": 5,
        "titre": "Activation de l'hôpital le plus proche",
        "description": "L'hôpital le plus proche de l'assuré est activé pour prendre en charge le patient.",
        "auto_sync": True,
    },
    {
        "key": "ambulance_en_route",
        "ordre": 6,
        "titre": "Ambulance en route",
        "description": "L'ambulance de l'hôpital prend la route pour récupérer l'assuré.",
        "auto_sync": False,
    },
    {
        "key": "medecin_en_route",
        "ordre": 7,
        "titre": "Médecin référent en route",
        "description": "Le médecin référent se rend sur le lieu de l'urgence ou à l'hôpital activé.",
        "auto_sync": False,
    },
    {
        "key": "partage_donnees_medicales",
        "ordre": 8,
        "titre": "Partage des données médicales",
        "description": "L'alerte ouvre l'accès sécurisé aux informations médicales et civiles de l'assuré.",
        "auto_sync": True,
    },
    {
        "key": "verification_urgence",
        "ordre": 9,
        "titre": "Vérification de la véracité de l'urgence",
        "description": "Le médecin sur site qualifie l'urgence avant d'engager les soins.",
        "auto_sync": True,
    },
    {
        "key": "suspension_si_fausse",
        "ordre": 10,
        "titre": "Suspension si urgence non avérée",
        "description": "En cas de fausse alerte, la prise en charge est suspendue.",
        "auto_sync": True,
    },
    {
        "key": "validation_et_numero_sinistre",
        "ordre": 11,
        "titre": "Validation hospitalière & numéro de sinistre",
        "description": "La validation médicale déclenche définitivement la prise en charge et confirme le numéro de sinistre.",
        "auto_sync": True,
    },
    {
        "key": "facture_emise",
        "ordre": 12,
        "titre": "Facture hospitalière émise",
        "description": "L'hôpital rédige la facture du séjour pour transmission à Mobility Health.",
        "auto_sync": True,
    },
    {
        "key": "validation_facture_medicale",
        "ordre": 13,
        "titre": "Validation médicale de la facture",
        "description": "Le médecin référent MH confirme le contenu médical avant envoi au pôle sinistre.",
        "auto_sync": True,
    },
    {
        "key": "validation_facture_sinistre",
        "ordre": 14,
        "titre": "Validation par le pôle sinistre",
        "description": "Les agents sinistre MH vérifient la facture et déclenchent la phase comptable.",
        "auto_sync": True,
    },
    {
        "key": "validation_facture_comptable",
        "ordre": 15,
        "titre": "Validation comptable",
        "description": "La facturation est transmise à la comptabilité MH pour paiement ou rejet.",
        "auto_sync": True,
    },
]


def ensure_workflow_steps(
    db: Session,
    sinistre: Sinistre,
    alerte: Optional[Alerte],
) -> Tuple[List[SinistreProcessStep], bool]:
    """
    S'assure que toutes les étapes du workflow sinistre existent et reflètent l'état actuel.
    Retourne la liste ordonnée des étapes ainsi qu'un booléen indiquant si des modifications ont été effectuées.
    """
    existing_steps: Dict[str, SinistreProcessStep] = {step.step_key: step for step in sinistre.workflow_steps}
    ordered_steps: List[SinistreProcessStep] = []
    modified = False

    for template in SINISTRE_WORKFLOW_TEMPLATE:
        step = existing_steps.get(template["key"])
        status, completed_at = _compute_status(template["key"], sinistre, alerte)

        if step is None:
            step = SinistreProcessStep(
                sinistre_id=sinistre.id,
                step_key=template["key"],
                titre=template["titre"],
                description=template["description"],
                ordre=template["ordre"],
                statut=status.value,
                completed_at=completed_at if status == StatutWorkflowSinistre.COMPLETED else None,
            )
            db.add(step)
            modified = True
        else:
            if template["auto_sync"]:
                desired_status = status.value
                if step.statut != desired_status:
                    step.statut = desired_status
                    if status == StatutWorkflowSinistre.COMPLETED and step.completed_at is None:
                        step.completed_at = completed_at or datetime.utcnow()
                    if status != StatutWorkflowSinistre.COMPLETED:
                        step.completed_at = None
                    modified = True
            # Toujours synchroniser les métadonnées statiques
            if step.titre != template["titre"] or step.description != template["description"] or step.ordre != template["ordre"]:
                step.titre = template["titre"]
                step.description = template["description"]
                step.ordre = template["ordre"]
                modified = True

        ordered_steps.append(step)

    ordered_steps.sort(key=lambda s: s.ordre)
    return ordered_steps, modified


def update_workflow_step(
    db: Session,
    sinistre: Sinistre,
    alerte: Optional[Alerte],
    step_key: str,
    statut: StatutWorkflowSinistre,
    actor_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> SinistreProcessStep:
    """Met à jour manuellement une étape de workflow."""
    steps, _ = ensure_workflow_steps(db, sinistre, alerte)
    steps_map = {step.step_key: step for step in steps}
    step = steps_map.get(step_key)

    if step is None:
        raise ValueError(f"Étape {step_key} introuvable pour ce sinistre")

    if step.statut != statut.value:
        step.statut = statut.value
        if statut == StatutWorkflowSinistre.COMPLETED:
            step.completed_at = datetime.utcnow()
        else:
            step.completed_at = None

    if actor_id is not None and step.actor_id != actor_id:
        step.actor_id = actor_id

    if notes:
        existing_details = step.details or {}
        step.details = {
            **existing_details,
            "notes": notes,
            "last_update": datetime.utcnow().isoformat(),
        }

    if _apply_business_rules(sinistre, alerte, step_key, statut):
        db.add(sinistre)
        if alerte:
            db.add(alerte)

    db.add(step)
    return step


def _compute_status(
    step_key: str,
    sinistre: Sinistre,
    alerte: Optional[Alerte],
) -> Tuple[StatutWorkflowSinistre, Optional[datetime]]:
    stay = getattr(sinistre, "hospital_stay", None)
    invoice = getattr(stay, "invoice", None) if stay else None

    if step_key == "alerte_declenchee":
        return StatutWorkflowSinistre.COMPLETED, alerte.created_at if alerte else sinistre.created_at

    if step_key == "centre_ops_notifie":
        return StatutWorkflowSinistre.COMPLETED, alerte.created_at if alerte else sinistre.created_at

    if step_key == "medecin_notifie":
        if sinistre.medecin_referent_id:
            return StatutWorkflowSinistre.COMPLETED, sinistre.created_at
        return StatutWorkflowSinistre.PENDING, None

    if step_key == "localisation_assure":
        if alerte and alerte.latitude is not None and alerte.longitude is not None:
            return StatutWorkflowSinistre.COMPLETED, alerte.created_at
        return StatutWorkflowSinistre.PENDING, None

    if step_key == "activation_hopital":
        if sinistre.hospital_id:
            return StatutWorkflowSinistre.COMPLETED, sinistre.updated_at
        return StatutWorkflowSinistre.IN_PROGRESS, None

    if step_key in {"ambulance_en_route", "medecin_en_route"}:
        return StatutWorkflowSinistre.PENDING, None

    if step_key == "partage_donnees_medicales":
        if sinistre.medecin_referent_id:
            return StatutWorkflowSinistre.COMPLETED, sinistre.created_at
        return StatutWorkflowSinistre.PENDING, None

    if step_key == "verification_urgence":
        if sinistre.statut == "annule":
            return StatutWorkflowSinistre.CANCELLED, sinistre.updated_at
        # Validé par le médecin référent : soit statut "resolu", soit numero_sinistre attribué
        if sinistre.statut == "resolu" or sinistre.numero_sinistre:
            return StatutWorkflowSinistre.COMPLETED, sinistre.updated_at or sinistre.created_at
        return StatutWorkflowSinistre.IN_PROGRESS, None

    if step_key == "suspension_si_fausse":
        if sinistre.statut == "annule":
            return StatutWorkflowSinistre.COMPLETED, sinistre.updated_at
        return StatutWorkflowSinistre.PENDING, None

    if step_key == "validation_et_numero_sinistre":
        if sinistre.numero_sinistre:
            return StatutWorkflowSinistre.COMPLETED, sinistre.updated_at or sinistre.created_at
        if sinistre.statut == "annule":
            return StatutWorkflowSinistre.CANCELLED, sinistre.updated_at
        return StatutWorkflowSinistre.IN_PROGRESS, None

    if step_key == "facture_emise":
        if not stay:
            return StatutWorkflowSinistre.PENDING, None
        if invoice:
            return StatutWorkflowSinistre.COMPLETED, invoice.created_at
        if stay.status in {"validated", "invoiced"}:
            return StatutWorkflowSinistre.IN_PROGRESS, None
        return StatutWorkflowSinistre.PENDING, None

    if step_key == "validation_facture_medicale":
        if not invoice:
            return StatutWorkflowSinistre.PENDING, None
        if invoice.validation_medicale == "rejected" or invoice.statut == InvoiceStatus.REJECTED:
            return (
                StatutWorkflowSinistre.CANCELLED,
                invoice.validation_medicale_date or invoice.updated_at,
            )
        if invoice.validation_medicale == "approved" or invoice.statut in {
            InvoiceStatus.PENDING_SINISTRE,
            InvoiceStatus.PENDING_COMPTA,
            InvoiceStatus.VALIDATED,
            InvoiceStatus.PAID,
        }:
            return (
                StatutWorkflowSinistre.COMPLETED,
                invoice.validation_medicale_date or invoice.updated_at,
            )
        return StatutWorkflowSinistre.IN_PROGRESS, invoice.date_facture

    if step_key == "validation_facture_sinistre":
        if not invoice or invoice.validation_medicale != "approved":
            return StatutWorkflowSinistre.PENDING, None
        if invoice.validation_sinistre == "rejected" or invoice.statut == InvoiceStatus.REJECTED:
            return (
                StatutWorkflowSinistre.CANCELLED,
                invoice.validation_sinistre_date or invoice.updated_at,
            )
        if invoice.validation_sinistre == "approved" or invoice.statut in {
            InvoiceStatus.PENDING_COMPTA,
            InvoiceStatus.VALIDATED,
            InvoiceStatus.PAID,
        }:
            return (
                StatutWorkflowSinistre.COMPLETED,
                invoice.validation_sinistre_date or invoice.updated_at,
            )
        return StatutWorkflowSinistre.IN_PROGRESS, None

    if step_key == "validation_facture_comptable":
        if not invoice or invoice.validation_sinistre != "approved":
            return StatutWorkflowSinistre.PENDING, None
        if invoice.validation_compta == "rejected" or invoice.statut == InvoiceStatus.REJECTED:
            return (
                StatutWorkflowSinistre.CANCELLED,
                invoice.validation_compta_date or invoice.updated_at,
            )
        if invoice.validation_compta == "approved" or invoice.statut in {
            InvoiceStatus.VALIDATED,
            InvoiceStatus.PAID,
        }:
            return (
                StatutWorkflowSinistre.COMPLETED,
                invoice.validation_compta_date or invoice.updated_at,
            )
        if invoice.statut == InvoiceStatus.PENDING_COMPTA:
            return StatutWorkflowSinistre.IN_PROGRESS, None
        return StatutWorkflowSinistre.PENDING, None

    return StatutWorkflowSinistre.PENDING, None


def _apply_business_rules(
    sinistre: Sinistre,
    alerte: Optional[Alerte],
    step_key: str,
    statut: StatutWorkflowSinistre,
) -> bool:
    """
    Applique les effets métiers lorsque certaines étapes changent de statut.
    Retourne True si le sinistre ou l'alerte ont été modifiés.
    """
    changed = False

    if step_key == "suspension_si_fausse":
        if statut == StatutWorkflowSinistre.COMPLETED and sinistre.statut != "annule":
            sinistre.statut = "annule"
            if alerte and alerte.statut != "annulee":
                alerte.statut = "annulee"
            changed = True
        elif statut != StatutWorkflowSinistre.COMPLETED and sinistre.statut == "annule":
            sinistre.statut = "en_cours"
            if alerte and alerte.statut == "annulee":
                alerte.statut = "en_cours"
            changed = True

    return changed


