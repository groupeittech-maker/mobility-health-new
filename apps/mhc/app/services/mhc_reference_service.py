"""Allocation des numéros MHC (police, sinistre, bons)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.mhc_nomenclature import (
    MhcCareDocumentType,
    MhcOperationCode,
    code_from_id,
    country_code_from_name,
    format_bpcu_like_number,
    format_bph_number,
    format_police_number,
    format_simple_document_number,
    format_sinistre_number,
    parse_sinistre_order,
)
from app.models.assureur import Assureur
from app.models.hospital import Hospital
from app.models.mhc_reference_counter import MhcReferenceCounter
from app.models.produit_assurance import ProduitAssurance
from app.models.sinistre import Sinistre
from app.models.souscription import Souscription


def next_order(db: Session, counter_key: str, year: Optional[int] = None) -> int:
    year = year or datetime.utcnow().year
    query = db.query(MhcReferenceCounter).filter(
        MhcReferenceCounter.counter_key == counter_key,
        MhcReferenceCounter.year == year,
    )
    try:
        row = query.with_for_update().first()
    except Exception:
        row = query.first()
    if row is None:
        row = MhcReferenceCounter(counter_key=counter_key, year=year, last_value=0)
        db.add(row)
        db.flush()
    row.last_value = int(row.last_value or 0) + 1
    db.add(row)
    db.flush()
    return row.last_value


def _country_from_souscription(souscription: Optional[Souscription], fallback_country: Optional[str] = None) -> int:
    if souscription and getattr(souscription, "projet_voyage", None):
        projet = souscription.projet_voyage
        dest = getattr(projet, "destination", None)
        pays = dest
        dest_country = getattr(projet, "destination_country", None)
        if dest_country is not None:
            pays = getattr(dest_country, "nom", dest)
        return country_code_from_name(pays or fallback_country)
    if souscription and getattr(souscription, "user", None):
        return country_code_from_name(
            getattr(souscription.user, "pays_residence", None) or fallback_country
        )
    return country_code_from_name(fallback_country)


def _assureur_code(souscription: Optional[Souscription]) -> int:
    if not souscription:
        return 1
    produit = getattr(souscription, "produit_assurance", None)
    if produit and getattr(produit, "assureur_id", None):
        return code_from_id(produit.assureur_id)
    if produit and getattr(produit, "assureur_obj", None) and produit.assureur_obj.id:
        return code_from_id(produit.assureur_obj.id)
    return 1


def allocate_police_number(
    db: Session,
    souscription: Optional[Souscription] = None,
    country_name: Optional[str] = None,
    year: Optional[int] = None,
) -> str:
    year = year or datetime.utcnow().year
    order = next_order(db, "police", year)
    country = _country_from_souscription(souscription, country_name)
    assureur = _assureur_code(souscription)
    return format_police_number(order, country, assureur, year)


def allocate_sinistre_number(
    db: Session,
    sinistre: Sinistre,
    year: Optional[int] = None,
) -> str:
    year = year or datetime.utcnow().year
    order = next_order(db, "sinistre", year)
    souscription = getattr(sinistre, "souscription", None)
    hospital = getattr(sinistre, "hospital", None)
    country_name = None
    if hospital is not None:
        country_name = hospital.pays
    country = _country_from_souscription(souscription, country_name)
    assureur = _assureur_code(souscription)
    return format_sinistre_number(order, country, assureur, year)


def allocate_document_number(
    db: Session,
    document_type: MhcCareDocumentType,
    sinistre: Sinistre,
    *,
    bh_order: Optional[int] = None,
    bph_sequence: Optional[int] = None,
    year: Optional[int] = None,
) -> str:
    year = year or datetime.utcnow().year
    sinistre_order = parse_sinistre_order(sinistre.numero_sinistre)
    hospital = getattr(sinistre, "hospital", None)
    partner_code = code_from_id(hospital.id if hospital else None)
    doctor_code = code_from_id(sinistre.medecin_referent_id)

    if document_type == MhcCareDocumentType.BPH:
        if not bh_order or not bph_sequence:
            raise ValueError("La prolongation d'hospitalisation requiert le n° d'ordre du bon d'hospitalisation.")
        return format_bph_number(bh_order, bph_sequence, sinistre_order)

    if document_type in {MhcCareDocumentType.BPCU, MhcCareDocumentType.BRPCU}:
        operation = (
            MhcOperationCode.BPCU
            if document_type == MhcCareDocumentType.BPCU
            else MhcOperationCode.BRPCU
        )
        order = next_order(db, document_type.value, year)
        return format_bpcu_like_number(order, sinistre_order, operation, partner_code, doctor_code, year)

    operation_map = {
        MhcCareDocumentType.BH: MhcOperationCode.BH,
        MhcCareDocumentType.BS: MhcOperationCode.BS,
        MhcCareDocumentType.BRS: MhcOperationCode.BRS,
        MhcCareDocumentType.BRF: MhcOperationCode.BRF,
        MhcCareDocumentType.ARS: MhcOperationCode.ARS,
        MhcCareDocumentType.ARF: MhcOperationCode.ARF,
        MhcCareDocumentType.CERTIFICAT_DECES: MhcOperationCode.CERTIFICAT_DECES,
    }
    operation = operation_map[document_type]
    order = next_order(db, document_type.value, year)
    return format_simple_document_number(order, sinistre_order, operation)
