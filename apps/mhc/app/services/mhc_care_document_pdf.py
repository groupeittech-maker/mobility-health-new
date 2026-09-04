"""Génération PDF des bons et attestations MHC — modèle référentiel officiel."""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.core.mhc_nomenclature import DOCUMENT_TITLES, EXIT_MODE_LABELS, MhcCareDocumentType
from app.models.mhc_care_document import MhcCareDocument
from app.services.pdf_service import _load_logo_bytes_mobility


# Couleurs modèle référentiel MHC
MHC_NAVY = colors.HexColor("#002060")
MHC_TEAL = colors.HexColor("#14AE98")
MHC_RED = colors.HexColor("#c00000")
MHC_PURPLE = colors.HexColor("#4e267c")
MHC_LAVENDER = colors.HexColor("#a689c1")
MHC_GREY_FOOT = colors.HexColor("#a6a6a6")
MHC_GREY_LINE = colors.HexColor("#cccccc")
MHC_TEXT = colors.HexColor("#1a1528")
MHC_CHECK = colors.HexColor("#334155")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_L = 1.5 * cm
MARGIN_R = 1.5 * cm
MARGIN_T = 1.2 * cm
MARGIN_B = 1.6 * cm
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_L - MARGIN_R

REFUSAL_MOTIFS = [
    "Prestation ou pathologie exclue des garanties la police d'assurance voyage.",
    "Absence du caractère d'urgence médicale obligatoire.",
    "Sinistre survenu en dehors des dates de validité ou d'effet du contrat.",
    "Situation médicale présente avant la souscription de la police d'assurance",
]

DOC_NUMBER_LABELS: Dict[str, str] = {
    MhcCareDocumentType.BPCU.value: "N° DU BON DE PRISE EN CHARGE",
    MhcCareDocumentType.BRPCU.value: "N° DU BON DE REFUS",
    MhcCareDocumentType.BH.value: "N° DU BON D'HOSPITALISATION",
    MhcCareDocumentType.BPH.value: "N° DU BON DE PROLONGATION",
    MhcCareDocumentType.BS.value: "N° DU BULLETIN DE SORTIE",
    MhcCareDocumentType.BRS.value: "N° DU BON DE RAPATRIEMENT SANITAIRE",
    MhcCareDocumentType.ARS.value: "N° DE L'ATTESTATION",
    MhcCareDocumentType.BRF.value: "N° DU BON DE RAPATRIEMENT FUNÉRAIRE",
    MhcCareDocumentType.ARF.value: "N° DE L'ATTESTATION",
}


def _display(value: Any) -> str:
    if value in (None, "", []):
        return ""
    if isinstance(value, list):
        return " ; ".join(str(v) for v in value)
    return str(value)


def _format_date(value: Any) -> str:
    if value in (None, "", []):
        return ""
    raw = str(value)
    if "T" in raw:
        return raw.replace("T", " ").split(".")[0][:16]
    return raw


def _styles():
    base = getSampleStyleSheet()
    return {
        "slogan": ParagraphStyle(
            "MhcSlogan",
            parent=base["Normal"],
            fontSize=8,
            textColor=MHC_GREY_FOOT,
            alignment=TA_RIGHT,
            fontName="Helvetica-Oblique",
        ),
        "doc_title": ParagraphStyle(
            "MhcDocTitle",
            parent=base["Heading1"],
            fontSize=12,
            textColor=MHC_NAVY,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            spaceAfter=8,
            leading=14,
        ),
        "table_label": ParagraphStyle(
            "MhcTableLabel",
            parent=base["Normal"],
            fontSize=7.5,
            textColor=MHC_NAVY,
            fontName="Helvetica-Bold",
            leading=9,
        ),
        "table_value": ParagraphStyle(
            "MhcTableValue",
            parent=base["Normal"],
            fontSize=9,
            textColor=MHC_TEXT,
            leading=11,
            spaceBefore=2,
        ),
        "table_value_red": ParagraphStyle(
            "MhcTableValueRed",
            parent=base["Normal"],
            fontSize=9,
            textColor=MHC_RED,
            fontName="Helvetica-Bold",
            leading=11,
            spaceBefore=2,
        ),
        "section_title": ParagraphStyle(
            "MhcSectionTitle",
            parent=base["Normal"],
            fontSize=8.5,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            leading=10,
        ),
        "section_num": ParagraphStyle(
            "MhcSectionNum",
            parent=base["Normal"],
            fontSize=9,
            textColor=MHC_TEAL,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            leading=10,
        ),
        "legal": ParagraphStyle(
            "MhcLegal",
            parent=base["Normal"],
            fontSize=8.5,
            textColor=MHC_TEXT,
            leading=12,
            alignment=TA_LEFT,
        ),
        "checkbox": ParagraphStyle(
            "MhcCheckbox",
            parent=base["Normal"],
            fontSize=8,
            textColor=MHC_CHECK,
            leading=13,
            leftIndent=4,
        ),
        "sign_label": ParagraphStyle(
            "MhcSignLabel",
            parent=base["Normal"],
            fontSize=8,
            textColor=MHC_NAVY,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            leading=10,
        ),
        "sign_hint": ParagraphStyle(
            "MhcSignHint",
            parent=base["Normal"],
            fontSize=8,
            textColor=MHC_GREY_FOOT,
            fontName="Helvetica-Oblique",
            alignment=TA_CENTER,
            leading=10,
        ),
    }


def _label(text: str) -> str:
    return f"<u>{text.upper()}</u>"


def _draw_watermark_and_footer(canvas, _doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#e8eef2"))
    canvas.setLineWidth(1.5)
    for i in range(-6, 18):
        x = i * 2.2 * cm
        canvas.line(x, 0, x + PAGE_HEIGHT * 0.6, PAGE_HEIGHT)
    canvas.restoreState()

    canvas.saveState()
    y_line = MARGIN_B * 0.55
    canvas.setStrokeColor(MHC_GREY_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_L, y_line, PAGE_WIDTH - MARGIN_R, y_line)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MHC_GREY_FOOT)
    canvas.drawCentredString(PAGE_WIDTH / 2, y_line - 0.45 * cm, "Mobility Health Care S.A.S")
    canvas.setFillColor(MHC_LAVENDER)
    canvas.drawRightString(PAGE_WIDTH - MARGIN_R, y_line + 0.15 * cm, "mobilityhealth-care.com")
    canvas.restoreState()


class _MhcCareDocTemplate(BaseDocTemplate):
    def __init__(self, buffer: BytesIO, title: str):
        super().__init__(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN_L,
            rightMargin=MARGIN_R,
            topMargin=MARGIN_T,
            bottomMargin=MARGIN_B,
            title=title,
        )
        frame = Frame(MARGIN_L, MARGIN_B, CONTENT_WIDTH, PAGE_HEIGHT - MARGIN_T - MARGIN_B, id="main")
        self.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_draw_watermark_and_footer)])


def _section_bar(number: int, title: str, styles) -> Table:
    num = Table([[Paragraph(str(number), styles["section_num"])]], colWidths=[0.65 * cm], rowHeights=[0.65 * cm])
    num.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    bar = Table([[num, Paragraph(title.upper(), styles["section_title"])]], colWidths=[0.75 * cm, CONTENT_WIDTH - 0.75 * cm])
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), MHC_TEAL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 4),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return bar


def _labeled_grid(
    fields: Sequence[Tuple[str, Any]],
    styles,
    columns: int = 3,
    value_style_key: str = "table_value",
) -> Table:
    col_w = CONTENT_WIDTH / columns
    rows: List[List[Any]] = []
    value_style = styles[value_style_key]
    for i in range(0, len(fields), columns):
        chunk = list(fields[i : i + columns])
        label_row: List[Any] = []
        value_row: List[Any] = []
        for label, value in chunk:
            label_row.append(Paragraph(_label(label), styles["table_label"]))
            value_row.append(Paragraph(_display(value), value_style))
        while len(label_row) < columns:
            label_row.append("")
            value_row.append("")
        rows.append(label_row)
        rows.append(value_row)

    table = Table(rows, colWidths=[col_w] * columns)
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_header(styles) -> List[Any]:
    logo_bytes = _load_logo_bytes_mobility()
    logo_cell: Any = Spacer(1, 1.1 * cm)
    if logo_bytes:
        try:
            logo_bytes.seek(0)
            logo_cell = Image(logo_bytes, width=4.5 * cm, height=1.35 * cm, kind="proportional")
        except Exception:
            pass
    slogan = Paragraph("Travel safe, Live free.", styles["slogan"])
    header = Table([[logo_cell, slogan]], colWidths=[10 * cm, CONTENT_WIDTH - 10 * cm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    line = Table([[""]], colWidths=[CONTENT_WIDTH], rowHeights=[0.03 * cm])
    line.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), MHC_GREY_LINE)]))
    return [header, Spacer(1, 0.15 * cm), line, Spacer(1, 0.25 * cm)]


def _build_ref_row(document: MhcCareDocument, payload: Dict[str, Any], styles) -> Table:
    doc_type = document.document_type
    bon_label = DOC_NUMBER_LABELS.get(doc_type, "N° DU DOCUMENT")
    use_red = doc_type == MhcCareDocumentType.BRPCU.value
    fields = [
        ("N° de sinistre", payload.get("numero_sinistre")),
        (bon_label, document.numero),
        ("Date d'émission", _format_date(payload.get("date_emission"))),
        ("Heure d'émission", payload.get("heure_emission")),
    ]
    col_w = CONTENT_WIDTH / 4
    label_row = [Paragraph(_label(lbl), styles["table_label"]) for lbl, _ in fields]
    value_row = []
    for idx, (_, val) in enumerate(fields):
        if idx == 1 and use_red:
            value_row.append(Paragraph(_display(val), styles["table_value_red"]))
        else:
            value_row.append(Paragraph(_display(val), styles["table_value"]))
    table = Table([label_row, value_row], colWidths=[col_w] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _build_partner_section(partenaire: Dict[str, Any], payload: Dict[str, Any], styles) -> List[Any]:
    ville_pays = " / ".join(x for x in [partenaire.get("ville"), partenaire.get("pays")] if x)
    fields = [
        ("Nom de l'hôpital / clinique", partenaire.get("nom")),
        ("Ville / pays", ville_pays),
        ("Numéro de téléphone", partenaire.get("telephone")),
        ("Service concerné", partenaire.get("service") or payload.get("service")),
        ("Médecin référent", partenaire.get("medecin_referent") or payload.get("medecin_referent")),
        ("Email", partenaire.get("email")),
    ]
    return [
        _section_bar(1, "Établissement partenaire-santé destinataire", styles),
        _labeled_grid(fields, styles, columns=3),
        Spacer(1, 0.12 * cm),
    ]


def _build_voyageur_section(voyageur: Dict[str, Any], styles) -> List[Any]:
    fields = [
        ("Nom et prénom(s)", voyageur.get("nom")),
        ("Date de naissance", voyageur.get("date_naissance")),
        ("Genre", voyageur.get("genre")),
        ("Nationalité", voyageur.get("nationalite")),
        ("N° passeport / pièce d'identité", voyageur.get("passeport")),
        ("Pays de résidence habituelle", voyageur.get("pays_residence")),
    ]
    return [
        _section_bar(2, "Identification du voyageur assuré", styles),
        _labeled_grid(fields, styles, columns=3),
        Spacer(1, 0.12 * cm),
    ]


def _build_assureur_section(assureur: Dict[str, Any], payload: Dict[str, Any], styles) -> List[Any]:
    fields = [
        ("Compagnie d'assurance", assureur.get("compagnie")),
        ("N° de police", payload.get("numero_police")),
        ("Plafond de garantie médicale", assureur.get("plafond")),
        ("Date de début de couverture", assureur.get("date_debut")),
        ("Date de fin de couverture", assureur.get("date_fin")),
        ("", ""),
    ]
    return [
        _section_bar(3, "Assureur et police", styles),
        _labeled_grid(fields, styles, columns=3),
        Spacer(1, 0.12 * cm),
    ]


def _motif_selected(payload: Dict[str, Any], motif_text: str) -> bool:
    selected = payload.get("motifs_refus") or []
    if isinstance(selected, str):
        selected = [selected]
    blob = " ".join(str(x) for x in selected).lower()
    blob += " " + str(payload.get("motif_refus") or "").lower()
    blob += " " + str(payload.get("motif_medical") or "").lower()
    key = motif_text[:30].lower()
    return key in blob or any(m.lower() in blob for m in motif_text.split()[:3])


def _build_refusal_motifs_section(payload: Dict[str, Any], styles) -> List[Any]:
    checks = []
    for motif in REFUSAL_MOTIFS:
        mark = "☑" if _motif_selected(payload, motif) else "☐"
        checks.append(Paragraph(f"{mark}&nbsp;&nbsp;{motif}", styles["checkbox"]))

    left = Table(
        [
            [Paragraph(_label("Motifs de refus contractuels :"), styles["table_label"])],
            [checks[0]],
            [checks[1]],
            [checks[2]],
            [checks[3]],
        ],
        colWidths=[CONTENT_WIDTH / 2 - 0.05 * cm],
    )
    right = Table(
        [
            [Paragraph(_label("Autres motifs :"), styles["table_label"])],
            [Paragraph(_display(payload.get("autres_motifs") or payload.get("motif_refus")), styles["table_value"])],
        ],
        colWidths=[CONTENT_WIDTH / 2 - 0.05 * cm],
    )
    for tbl in (left, right):
        tbl.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
    panel = Table([[left, right]], colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2])
    panel.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [
        _section_bar(4, "Motif du refus de la prise en charge d'urgence", styles),
        panel,
        Spacer(1, 0.12 * cm),
    ]


def _build_bpcu_section(payload: Dict[str, Any], styles) -> List[Any]:
    fields = [
        ("Motif médical / diagnostic", payload.get("motif_medical") or payload.get("diagnostic")),
        ("Montant maximum autorisé", payload.get("montant_max")),
        ("Devise", payload.get("devise") or "XAF"),
        ("Service concerné", payload.get("service")),
        ("Médecin référent MHC", payload.get("medecin_referent")),
        ("Valable jusqu'au", _format_date(payload.get("valable_jusqu_au"))),
    ]
    return [
        _section_bar(4, "Prise en charge d'urgence autorisée", styles),
        _labeled_grid(fields, styles, columns=3),
        Spacer(1, 0.12 * cm),
    ]


def _build_specific_section(
    section_num: int,
    title: str,
    fields: Sequence[Tuple[str, Any]],
    styles,
) -> List[Any]:
    if not fields:
        return []
    return [
        _section_bar(section_num, title, styles),
        _labeled_grid(fields, styles, columns=3),
        Spacer(1, 0.12 * cm),
    ]


def _specific_fields(doc_type: str, payload: Dict[str, Any]) -> Tuple[str, List[Tuple[str, Any]]]:
    if doc_type == MhcCareDocumentType.BH.value:
        return (
            "Hospitalisation autorisée",
            [
                ("Date / heure d'admission prévue", payload.get("admission_prevue")),
                ("Service d'admission", payload.get("service")),
                ("Médecin traitant", payload.get("medecin_traitant")),
                ("Chambre", payload.get("chambre")),
                ("Diagnostic / motif", payload.get("motif_medical") or payload.get("diagnostic")),
                ("Valable jusqu'au", _format_date(payload.get("valable_jusqu_au"))),
            ],
        )
    if doc_type == MhcCareDocumentType.BPH.value:
        return (
            "Prolongation d'hospitalisation",
            [
                ("N° bon de prolongation", payload.get("numero")),
                ("Motif de la prolongation", payload.get("motif_prolongation")),
                ("Examens / traitements prévus", payload.get("examens_prevus")),
                ("Coût additionnel autorisé", payload.get("cout_additionnel")),
                ("Coût total à ce jour", payload.get("cout_total")),
                ("Devise", payload.get("devise") or "XAF"),
            ],
        )
    if doc_type == MhcCareDocumentType.BS.value:
        mode = payload.get("mode_sortie")
        docs_remis = payload.get("documents_remis") or []
        if isinstance(docs_remis, list):
            docs_remis = ", ".join(str(x) for x in docs_remis)
        return (
            "Bulletin de sortie",
            [
                ("Date d'entrée", payload.get("date_entree")),
                ("Date de sortie", payload.get("date_sortie")),
                ("Durée totale (jours)", payload.get("duree_jours")),
                ("Mode de sortie", EXIT_MODE_LABELS.get(mode, mode)),
                ("Résumé du rapport final", payload.get("resume_rapport")),
                ("Documentation remise", docs_remis),
            ],
        )
    if doc_type == MhcCareDocumentType.BRS.value:
        return (
            "Rapatriement sanitaire",
            [
                ("Date / heure de départ prévues", payload.get("depart_prevu")),
                ("Moyen de transport", payload.get("moyen_transport")),
                ("Société de transport", payload.get("transporteur")),
                ("Escorte médicale", payload.get("escorte_medicale")),
                ("Destination", payload.get("destination")),
                ("Coût total autorisé", payload.get("cout_rapatriement")),
            ],
        )
    if doc_type == MhcCareDocumentType.ARS.value:
        return (
            "Attestation de retour de rapatriement sanitaire",
            [
                ("Lieu de départ", payload.get("lieu_depart")),
                ("Structure de départ", payload.get("structure_depart")),
                ("Destination finale", payload.get("destination")),
                ("Structure d'arrivée", payload.get("structure_arrivee")),
                ("Départ", payload.get("date_depart")),
                ("Arrivée", payload.get("date_arrivee")),
                ("État à l'arrivée", payload.get("etat_arrivee")),
                ("Bonne réception", payload.get("bonne_reception")),
                ("Observations", payload.get("observations")),
            ],
        )
    if doc_type == MhcCareDocumentType.BRF.value:
        return (
            "Rapatriement funéraire",
            [
                ("Date et heure du décès", payload.get("date_deces")),
                ("Cause du décès", payload.get("cause_deces")),
                ("Pays de départ", payload.get("pays_depart")),
                ("Pays de destination", payload.get("pays_destination")),
                ("Moyen de transport du corps", payload.get("moyen_transport")),
                ("Coût total autorisé", payload.get("cout_rapatriement")),
            ],
        )
    if doc_type == MhcCareDocumentType.ARF.value:
        return (
            "Attestation de rapatriement funéraire",
            [
                ("Date et lieu du décès", payload.get("date_deces") or payload.get("lieu_deces")),
                ("N° acte / certificat de décès", payload.get("numero_acte_deces")),
                ("Lieu de départ", payload.get("lieu_depart")),
                ("Destination finale", payload.get("destination")),
                ("Réceptionnaire de la dépouille", payload.get("receptionnaire")),
                ("Date / heure de remise", payload.get("date_remise")),
                ("Bonne réception", payload.get("bonne_reception")),
            ],
        )
    return ("", [])


def _legal_text_html(doc_type: str) -> str:
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
            "prise en charge médicale <b>EST REFUSÉE</b>. Toute prestation dispensée à compter de ce refus "
            "demeure <b>À LA CHARGE EXCLUSIVE DU PATIENT VOYAGEUR</b>."
        ),
        MhcCareDocumentType.BH.value: (
            "Le présent bon d'hospitalisation est valable <b>72 HEURES</b> à compter de son émission. "
            "Toute poursuite au-delà de cette échéance nécessite un bon de prolongation. "
            "Toute prestation au-delà de 72h sans prolongation demeure à la charge du partenaire-santé."
        ),
        MhcCareDocumentType.BPH.value: (
            "Cette extension accorde une prise en charge additionnelle stricte de <b>24 HEURES</b>, "
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


def _signatory_labels(doc_type: str) -> List[str]:
    mapping = {
        MhcCareDocumentType.BPCU.value: ["DU PARTENAIRE-SANTÉ", "DU MEDECIN-CONSEIL"],
        MhcCareDocumentType.BRPCU.value: ["DU PARTENAIRE-SANTÉ", "DU MEDECIN-CONSEIL"],
        MhcCareDocumentType.BH.value: ["DU DEMANDEUR", "DU MEDECIN-CONSEIL", "DU PÔLE MÉDICAL MHC"],
        MhcCareDocumentType.BPH.value: ["DU DEMANDEUR", "DU MEDECIN-CONSEIL", "DU PÔLE MÉDICAL MHC"],
        MhcCareDocumentType.BS.value: ["DE MOBILITY HEALTH CARE", "DU PARTENAIRE-SANTÉ"],
        MhcCareDocumentType.BRS.value: ["DU PARTENAIRE-SANTÉ", "DU MEDECIN-CONSEIL", "DU PÔLE MÉDICAL MHC"],
        MhcCareDocumentType.ARS.value: ["DU PÔLE MÉDICAL MHC", "DU VOYAGEUR ASSURÉ"],
        MhcCareDocumentType.BRF.value: ["DE L'OPÉRATEUR FUNÉRAIRE", "DU MEDECIN-CONSEIL", "DU PÔLE MÉDICAL MHC"],
        MhcCareDocumentType.ARF.value: ["DU PÔLE MÉDICAL MHC", "DU RÉCEPTIONNAIRE DE LA DÉPOUILLE"],
    }
    return mapping.get(doc_type, ["MOBILITY HEALTH CARE"])


def _build_signatures(doc_type: str, styles) -> Table:
    labels = _signatory_labels(doc_type)
    col_w = CONTENT_WIDTH / len(labels)
    header_row = [Paragraph(_label(lbl), styles["sign_label"]) for lbl in labels]
    hint_row = [Paragraph("<i>Nom, fonction et cachet</i>", styles["sign_hint"]) for _ in labels]
    space_row = ["" for _ in labels]
    table = Table([header_row, hint_row, space_row], colWidths=[col_w] * len(labels), rowHeights=[None, None, 2.2 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _build_official_story(document: MhcCareDocument, styles) -> List[Any]:
    payload = dict(document.payload or {})
    doc_type = document.document_type
    title = DOCUMENT_TITLES.get(MhcCareDocumentType(doc_type), doc_type)
    voyageur = payload.get("voyageur") or {}
    partenaire = payload.get("partenaire_sante") or {}
    assureur = payload.get("assureur") or {}

    story: List[Any] = []
    story.extend(_build_header(styles))
    story.append(Paragraph(title.upper(), styles["doc_title"]))
    story.append(_build_ref_row(document, payload, styles))
    story.append(Spacer(1, 0.15 * cm))
    story.extend(_build_partner_section(partenaire, payload, styles))
    story.extend(_build_voyageur_section(voyageur, styles))
    story.extend(_build_assureur_section(assureur, payload, styles))

    if doc_type == MhcCareDocumentType.BRPCU.value:
        story.extend(_build_refusal_motifs_section(payload, styles))
    elif doc_type == MhcCareDocumentType.BPCU.value:
        story.extend(_build_bpcu_section(payload, styles))
    else:
        section_title, fields = _specific_fields(doc_type, payload)
        story.extend(_build_specific_section(4, section_title, fields, styles))

    legal = _legal_text_html(doc_type)
    if legal:
        story.append(_section_bar(5, "Engagement et conditions financières", styles))
        story.append(Paragraph(legal, styles["legal"]))
        story.append(Spacer(1, 0.12 * cm))

    story.append(_section_bar(6, "Décisions", styles))
    story.append(_build_signatures(doc_type, styles))
    return story


def build_care_document_pdf(document: MhcCareDocument) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = _MhcCareDocTemplate(buffer, document.numero)
    story = _build_official_story(document, styles)
    doc.build(story)
    return buffer.getvalue()
