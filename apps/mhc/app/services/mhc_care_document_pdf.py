"""Génération PDF des bons et attestations MHC."""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.mhc_nomenclature import DOCUMENT_TITLES, EXIT_MODE_LABELS, MhcCareDocumentType
from app.models.mhc_care_document import MhcCareDocument


MHC_RED = colors.HexColor("#b91c1c")
MHC_NAVY = colors.HexColor("#0f2f5b")
MHC_GOLD = colors.HexColor("#c9a227")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "MhcDocTitle",
            parent=base["Heading1"],
            fontSize=14,
            textColor=MHC_NAVY,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=18,
        ),
        "numero": ParagraphStyle(
            "MhcDocNumero",
            parent=base["Heading2"],
            fontSize=12,
            textColor=MHC_RED,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "MhcDocSection",
            parent=base["Heading3"],
            fontSize=10,
            textColor=MHC_NAVY,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "label": ParagraphStyle("MhcLabel", parent=base["Normal"], fontSize=8, textColor=colors.HexColor("#475569")),
        "value": ParagraphStyle("MhcValue", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#0f172a")),
        "legal": ParagraphStyle("MhcLegal", parent=base["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#334155")),
        "sign": ParagraphStyle("MhcSign", parent=base["Normal"], fontSize=8, alignment=TA_CENTER, textColor=MHC_NAVY),
    }


def _kv_table(rows: Sequence[Tuple[str, Any]], styles) -> Table:
    data = []
    for label, value in rows:
        display = "—" if value in (None, "", []) else str(value)
        data.append([Paragraph(str(label), styles["label"]), Paragraph(display, styles["value"])])
    table = Table(data, colWidths=[7.2 * cm, 10.3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    return table


def _party_rows(payload: Dict[str, Any]) -> List[Tuple[str, Any]]:
    v = payload.get("voyageur") or {}
    h = payload.get("partenaire_sante") or {}
    a = payload.get("assureur") or {}
    return [
        ("N° de sinistre", payload.get("numero_sinistre")),
        ("N° de police", payload.get("numero_police")),
        ("N° BPCU", payload.get("numero_bpcu")),
        ("N° bon d'hospitalisation", payload.get("numero_bh")),
        ("Voyageur", v.get("nom")),
        ("Date de naissance", v.get("date_naissance")),
        ("Genre", v.get("genre")),
        ("Nationalité", v.get("nationalite")),
        ("Passeport / pièce", v.get("passeport")),
        ("Pays de résidence", v.get("pays_residence")),
        ("Partenaire-santé", h.get("nom")),
        ("Ville / pays", " / ".join(x for x in [h.get("ville"), h.get("pays")] if x)),
        ("Téléphone partenaire", h.get("telephone")),
        ("Email partenaire", h.get("email")),
        ("Compagnie d'assurance", a.get("compagnie")),
        ("Plafond / coût produit", a.get("plafond")),
        ("Couverture du", a.get("date_debut")),
        ("Couverture au", a.get("date_fin")),
        ("Date d'émission", payload.get("date_emission")),
        ("Heure d'émission", payload.get("heure_emission")),
        ("Valable jusqu'au", payload.get("valable_jusqu_au")),
    ]


def _specific_rows(doc_type: str, payload: Dict[str, Any]) -> List[Tuple[str, Any]]:
    if doc_type == MhcCareDocumentType.BPCU.value:
        return [
            ("Motif médical / diagnostic", payload.get("motif_medical") or payload.get("diagnostic")),
            ("Montant maximum pris en charge", payload.get("montant_max")),
            ("Devise", payload.get("devise") or "XAF"),
            ("Service concerné", payload.get("service")),
            ("Médecin référent", payload.get("medecin_referent")),
        ]
    if doc_type == MhcCareDocumentType.BRPCU.value:
        motifs = payload.get("motifs_refus") or []
        if isinstance(motifs, list):
            motifs = " ; ".join(str(m) for m in motifs)
        return [
            ("Motifs de refus", motifs or payload.get("motif_refus")),
            ("Autres motifs", payload.get("autres_motifs")),
        ]
    if doc_type == MhcCareDocumentType.BH.value:
        return [
            ("Date / heure d'admission prévue", payload.get("admission_prevue")),
            ("Service d'admission", payload.get("service")),
            ("Médecin traitant", payload.get("medecin_traitant")),
            ("Chambre", payload.get("chambre")),
            ("Diagnostic / motif", payload.get("motif_medical") or payload.get("diagnostic")),
        ]
    if doc_type == MhcCareDocumentType.BPH.value:
        return [
            ("N° bon de prolongation", payload.get("numero")),
            ("Motif de la prolongation", payload.get("motif_prolongation")),
            ("Examens / traitements prévus", payload.get("examens_prevus")),
            ("Coût additionnel autorisé", payload.get("cout_additionnel")),
            ("Coût total à ce jour", payload.get("cout_total")),
            ("Devise", payload.get("devise") or "XAF"),
        ]
    if doc_type == MhcCareDocumentType.BS.value:
        mode = payload.get("mode_sortie")
        docs_remis = payload.get("documents_remis") or []
        if isinstance(docs_remis, list):
            docs_remis = ", ".join(str(x) for x in docs_remis)
        return [
            ("Date d'entrée", payload.get("date_entree")),
            ("Date de sortie", payload.get("date_sortie")),
            ("Durée totale (jours)", payload.get("duree_jours")),
            ("Résumé du rapport final", payload.get("resume_rapport")),
            ("Mode de sortie", EXIT_MODE_LABELS.get(mode, mode)),
            ("Documentation remise", docs_remis),
            ("N° bon de rapatriement sanitaire", payload.get("numero_brs")),
        ]
    if doc_type == MhcCareDocumentType.BRS.value:
        return [
            ("Date / heure de départ prévues", payload.get("depart_prevu")),
            ("Moyen de transport", payload.get("moyen_transport")),
            ("Société de transport", payload.get("transporteur")),
            ("Escorte médicale", payload.get("escorte_medicale")),
            ("Destination", payload.get("destination")),
            ("Diagnostic / motif", payload.get("motif_medical") or payload.get("diagnostic")),
            ("Coût total autorisé", payload.get("cout_rapatriement")),
            ("Devise", payload.get("devise") or "XAF"),
        ]
    if doc_type == MhcCareDocumentType.ARS.value:
        return [
            ("Lieu de départ", payload.get("lieu_depart")),
            ("Structure de départ", payload.get("structure_depart")),
            ("Destination finale", payload.get("destination")),
            ("Structure d'arrivée", payload.get("structure_arrivee")),
            ("Départ", payload.get("date_depart")),
            ("Arrivée", payload.get("date_arrivee")),
            ("Mode de transport", payload.get("moyen_transport")),
            ("Prestataire", payload.get("transporteur")),
            ("État à l'arrivée", payload.get("etat_arrivee")),
            ("Personne / structure réceptionnaire", payload.get("receptionnaire")),
            ("Bonne réception", payload.get("bonne_reception")),
            ("Observations", payload.get("observations")),
        ]
    if doc_type == MhcCareDocumentType.BRF.value:
        return [
            ("Date et heure du décès", payload.get("date_deces")),
            ("Cause du décès", payload.get("cause_deces")),
            ("Pays de départ", payload.get("pays_depart")),
            ("Pays de destination", payload.get("pays_destination")),
            ("Moyen de transport du corps", payload.get("moyen_transport")),
            ("Société de transport", payload.get("transporteur")),
            ("Contact famille", payload.get("contact_famille")),
            ("Coût total autorisé", payload.get("cout_rapatriement")),
            ("Devise", payload.get("devise") or "XAF"),
        ]
    if doc_type == MhcCareDocumentType.ARF.value:
        return [
            ("Date et lieu du décès", payload.get("date_deces") or payload.get("lieu_deces")),
            ("N° acte / certificat de décès", payload.get("numero_acte_deces")),
            ("Lieu de départ", payload.get("lieu_depart")),
            ("Destination finale", payload.get("destination")),
            ("Départ", payload.get("date_depart")),
            ("Arrivée", payload.get("date_arrivee")),
            ("Mode de transport", payload.get("moyen_transport")),
            ("Prestataire", payload.get("transporteur")),
            ("Réceptionnaire de la dépouille", payload.get("receptionnaire")),
            ("Date / heure de remise", payload.get("date_remise")),
            ("Bonne réception", payload.get("bonne_reception")),
            ("Réserves / observations", payload.get("observations")),
        ]
    return []


def _legal_text(doc_type: str) -> str:
    texts = {
        MhcCareDocumentType.BPCU.value: (
            "Ce bon de prise en charge est émis par Mobility Health Care pour le compte de l'assureur "
            "du voyageur, dans la limite des garanties de son contrat. Il vaut engagement de paiement "
            "direct auprès du partenaire-santé, sous réserve de la transmission des pièces justificatives "
            "au pôle médical de MHC. Toute prestation dépassant le montant autorisé doit faire l'objet "
            "d'une autorisation préalable, sauf urgence vitale."
        ),
        MhcCareDocumentType.BRPCU.value: (
            "Par la présente, Mobility Health Care informe le partenaire-santé et le voyageur que la "
            "prise en charge médicale EST REFUSÉE. Toute prestation dispensée à compter de ce refus "
            "demeure à la charge exclusive du voyageur."
        ),
        MhcCareDocumentType.BH.value: (
            "Le présent bon d'hospitalisation est valable 72 heures à compter de son émission. "
            "Toute poursuite au-delà de cette échéance nécessite un bon de prolongation. "
            "Toute prestation au-delà de 72h sans prolongation demeure à la charge du partenaire-santé."
        ),
        MhcCareDocumentType.BPH.value: (
            "Cette extension accorde une prise en charge additionnelle stricte de 24 heures, "
            "soumise à la validation conjointe du médecin-conseil et du pôle médical MHC."
        ),
        MhcCareDocumentType.BRS.value: (
            "Le présent bon autorise l'organisation et la prise en charge du transport médicalisé "
            "vers la destination indiquée. Toute modification du moyen, de la destination ou de la "
            "date de départ prévue doit être validée par le pôle médical."
        ),
        MhcCareDocumentType.ARS.value: (
            "Nous attestons que le rapatriement sanitaire a été effectivement réalisé. "
            "Cette attestation ne vaut pas quittance financière ni renonciation à un droit ou recours."
        ),
        MhcCareDocumentType.BRF.value: (
            "Le présent bon autorise l'organisation et la prise en charge du transport du corps vers "
            "la destination indiquée, sous réserve de la transmission du certificat et de l'acte de décès."
        ),
        MhcCareDocumentType.ARF.value: (
            "Nous attestons que le rapatriement funéraire a été effectivement réalisé et que la dépouille "
            "a été remise à la destination prévue. Cette attestation ne vaut pas quittance financière."
        ),
        MhcCareDocumentType.BS.value: (
            "Le bulletin de sortie formalise la fin de l'épisode de prise en charge. "
            "Lorsque le mode de sortie est un rapatriement sanitaire organisé par MHC, "
            "il est émis simultanément avec le bon de rapatriement sanitaire."
        ),
    }
    return texts.get(doc_type, "")


def _signatories(doc_type: str) -> List[str]:
    mapping = {
        MhcCareDocumentType.BPCU.value: ["Médecin-conseil MHC", "Partenaire-santé"],
        MhcCareDocumentType.BRPCU.value: ["Médecin-conseil MHC", "Partenaire-santé"],
        MhcCareDocumentType.BH.value: ["Demandeur", "Médecin-conseil MHC", "Pôle médical MHC"],
        MhcCareDocumentType.BPH.value: ["Demandeur", "Médecin-conseil MHC", "Pôle médical MHC"],
        MhcCareDocumentType.BS.value: ["Mobility Health Care", "Partenaire-santé"],
        MhcCareDocumentType.BRS.value: ["Partenaire-santé", "Médecin-conseil MHC", "Pôle médical MHC"],
        MhcCareDocumentType.ARS.value: ["Pôle médical MHC", "Voyageur assuré"],
        MhcCareDocumentType.BRF.value: ["Opérateur funéraire", "Médecin-conseil MHC", "Pôle médical MHC"],
        MhcCareDocumentType.ARF.value: ["Pôle médical MHC", "Réceptionnaire de la dépouille"],
    }
    return mapping.get(doc_type, ["Mobility Health Care"])


def build_care_document_pdf(document: MhcCareDocument) -> bytes:
    payload = dict(document.payload or {})
    payload.setdefault("numero", document.numero)
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=document.numero,
    )
    story = []
    title = DOCUMENT_TITLES.get(MhcCareDocumentType(document.document_type), document.document_type)
    story.append(Paragraph("MOBILITY HEALTH CARE", styles["title"]))
    story.append(Paragraph(title.upper(), styles["title"]))
    story.append(Paragraph(f"N° {document.numero}", styles["numero"]))

    story.append(Paragraph("Identification et rattachement du dossier", styles["section"]))
    story.append(_kv_table(_party_rows(payload), styles))

    specific = _specific_rows(document.document_type, payload)
    if specific:
        story.append(Paragraph("Éléments spécifiques du document", styles["section"]))
        story.append(_kv_table(specific, styles))

    legal = _legal_text(document.document_type)
    if legal:
        story.append(Paragraph("Engagement et conditions", styles["section"]))
        story.append(Paragraph(legal, styles["legal"]))

    signs = _signatories(document.document_type)
    story.append(Paragraph("Décisions / signatures", styles["section"]))
    sign_data = [[Paragraph(f"<b>{name}</b><br/><br/>Nom, fonction et cachet<br/><br/>______________", styles["sign"]) for name in signs]]
    width = 17.5 * cm / max(len(signs), 1)
    sign_table = Table(sign_data, colWidths=[width] * len(signs))
    sign_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.4, MHC_GOLD),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(sign_table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            "Document généré par la plateforme Mobility Health Care — usage interne et partenaires-santé.",
            styles["legal"],
        )
    )
    doc.build(story)
    return buffer.getvalue()
