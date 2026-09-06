"""Documents officiels MHC : attestation, avenant d'annulation, quittance."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.models.paiement import Paiement
from app.models.souscription import Souscription
from app.models.user import User

TEAL = colors.HexColor("#14AE98")
PURPLE = colors.HexColor("#4F1F78")
NAVY = colors.HexColor("#1B2A4A")
LIGHT_ROW = colors.HexColor("#F4F6F8")
PAID_BG = colors.HexColor("#D8F3DC")

DEFAULT_GARANTIES = [
    ("FRAIS MÉDICAUX", None),
    (
        "Frais médicaux et d'hospitalisation hors du pays de domicile (y compris épidémie ou pandémie) (A)",
        "(A) 10 000 000 F CFA (15 000 €)",
    ),
    ("Frais médicaux dentaires d'urgence (B)", "(B) 100 000 F CFA (150 €)"),
    ("ASSISTANCES AUX PERSONNES EN CAS DE MALADIE OU BLESSURE", None),
    (
        "Rapatriement médical (y compris épidémie ou pandémie) (C)",
        "(C) Frais réels",
    ),
    ("ASSISTANCE EN CAS DE DÉCÈS", None),
    ("Transport de corps (D)", "(D) Frais réels"),
    ("Frais de cercueil ou d'urne (E)", "(E) 1 000 000 F CFA (1 500 €)"),
    ("Présence hospitalière d'un proche (F)", "(F) Billet d'avion AR (Eco) ou billet de train"),
    (
        "Frais de séjour du membre de la famille accompagnateur (G)",
        "(G) 100 000 F CFA (150 €) par jour (max. 3 nuits)",
    ),
    ("ASSISTANCE VOYAGE", None),
    ("Avant le voyage", None),
    ("Téléconsultation (H)", "(H) 1 appel"),
    ("Informations pratiques avant le voyage (I)", "(I) Informations"),
]


def _fmt_date(value: Any, with_time: bool = False) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M") if with_time else value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _money(value: Any, currency: str = "F CFA") -> str:
    try:
        amount = Decimal(str(value))
    except Exception:
        return f"[MONTANT] {currency}"
    formatted = f"{amount:,.0f}".replace(",", " ")
    return f"{formatted} {currency}"


def _amount_in_words(value: Any, currency: str = "francs CFA") -> str:
    try:
        n = int(Decimal(str(value)))
    except Exception:
        return f"[MONTANT EN LETTRES] {currency}"
    units = [
        "", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
        "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
    ]

    def under_100(x: int) -> str:
        if x < 17:
            return units[x]
        if x < 20:
            return "dix-" + units[x - 10]
        tens = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante", "quatre-vingt", "quatre-vingt"]
        if x < 70:
            t, u = divmod(x, 10)
            if u == 1 and t != 8:
                return tens[t] + "-et-un"
            return tens[t] + (f"-{units[u]}" if u else "")
        if x < 80:
            return "soixante-" + under_100(x - 60)
        if x == 80:
            return "quatre-vingts"
        return "quatre-vingt-" + under_100(x - 80)

    def under_1000(x: int) -> str:
        if x < 100:
            return under_100(x)
        h, r = divmod(x, 100)
        head = "cent" if h == 1 else units[h] + " cent"
        if r == 0:
            return head + ("s" if h > 1 else "")
        return head + " " + under_100(r)

    if n == 0:
        words = "zéro"
    elif n < 1000:
        words = under_1000(n)
    elif n < 1_000_000:
        m, r = divmod(n, 1000)
        head = "mille" if m == 1 else under_1000(m) + " mille"
        words = head if r == 0 else f"{head} {under_1000(r)}"
    else:
        mil, r = divmod(n, 1_000_000)
        head = "un million" if mil == 1 else under_1000(mil) + " millions"
        words = head if r == 0 else f"{head} {_amount_in_words(r, '').strip()}"
    return f"{words} {currency}".strip() + f" ({n} {currency})"


def _garanties_rows(produit) -> list[tuple[str, Optional[str]]]:
    raw = getattr(produit, "garanties", None) if produit else None
    if not raw:
        return DEFAULT_GARANTIES
    items = raw if isinstance(raw, list) else []
    rows: list[tuple[str, Optional[str]]] = []
    for item in items:
        if isinstance(item, str):
            rows.append((item, "—"))
            continue
        if not isinstance(item, dict):
            continue
        title = str(item.get("titre") or item.get("libelle") or item.get("nom") or "").strip()
        cap = item.get("plafond") or item.get("capitaux") or item.get("limite") or item.get("montant")
        if not title:
            continue
        rows.append((title, str(cap).strip() if cap not in (None, "") else "—"))
    return rows or DEFAULT_GARANTIES


def _traveler(user: Optional[User], traveler_info: Optional[dict[str, Any]]) -> dict[str, str]:
    info = traveler_info or {}
    name = (info.get("fullName") or "").strip()
    if not name and user:
        name = user.full_name or user.username or "—"
    birth = info.get("birthDate") or getattr(user, "date_naissance", None)
    passport = info.get("passportNumber") or getattr(user, "numero_passeport", None) or "—"
    nationality = info.get("nationality") or info.get("nationalite") or getattr(user, "nationalite", None) or "—"
    residence = info.get("paysResidence") or info.get("pays_residence") or getattr(user, "pays_residence", None) or "—"
    return {
        "name": name or "—",
        "birth": _fmt_date(birth),
        "passport": str(passport or "—"),
        "nationality": str(nationality or "—"),
        "residence": str(residence or "—"),
    }


def _split_person_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in (full_name or "").strip().split() if part]
    if not parts:
        return "—", "—"
    if len(parts) == 1:
        return parts[0], "—"
    return parts[0], " ".join(parts[1:])


def _age_from_birth(value: Any) -> Optional[int]:
    if not value:
        return None
    if isinstance(value, date):
        born = value
    elif isinstance(value, datetime):
        born = value.date()
    elif isinstance(value, str):
        text = value.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                born = datetime.strptime(text[:10], fmt).date()
                break
            except ValueError:
                continue
        else:
            return None
    else:
        return None
    today = date.today()
    years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return max(0, years)


def _format_ayants_droit(minors_info: Optional[list[dict[str, Any]]]) -> str:
    if not minors_info:
        return "—"
    entries: list[str] = []
    for minor in minors_info:
        if not isinstance(minor, dict):
            continue
        name = (minor.get("nom_complet") or minor.get("fullName") or minor.get("nom") or "").strip()
        birth = minor.get("date_naissance") or minor.get("birthDate")
        age = _age_from_birth(birth)
        if name and age is not None:
            entries.append(f"{name} ({age} ans)")
        elif name:
            entries.append(name)
    return ", ".join(entries) if entries else "—"


def _medecin_conseil_lines(medecin_conseil: Optional[dict[str, Any]]) -> dict[str, str]:
    info = medecin_conseil or {}
    full_name = (info.get("nom") or info.get("full_name") or info.get("fullName") or "").strip()
    prenom, nom = _split_person_name(full_name)
    if info.get("prenom"):
        prenom = str(info["prenom"]).strip() or prenom
    if info.get("nom_famille"):
        nom = str(info["nom_famille"]).strip() or nom
    return {
        "nom": nom or "—",
        "prenom": prenom or "—",
        "tel": (info.get("telephone") or info.get("tel") or "—").strip() or "—",
        "email": (info.get("email") or "—").strip() or "—",
        "alerte": getattr(settings, "ASSURANCE_ALERT_CENTER", None) or "+242 05 098 35 35",
    }


def _dispositions_speciales(styles, section_num: int = 3) -> list:
    return [
        Paragraph(f"{section_num} INFORMATIONS SUR LES DISPOSITIONS SPÉCIALES", styles["section"]),
        Paragraph(
            "L'Assuré reconnaît avoir reçu ou, avoir pu consulter les Conditions Générales applicables au "
            "contrat et déclare avoir pris connaissance des garanties et exclusions.",
            styles["body"],
        ),
        Paragraph(
            "Ce certificat ne peut servir en aucun cas de lettre de garantie ou de prise en charge auprès des "
            "structures médicales publiques ou privées comme de tout autre organisme.",
            styles["body"],
        ),
        Paragraph(
            "L'Assuré reconnait ne pas être malade au moment de la souscription et déclare ne pas effectuer "
            "ce voyage à des fins thérapeutiques.",
            styles["body"],
        ),
    ]


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("OffTitle", parent=base["Heading1"], fontSize=16, textColor=PURPLE, alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold"),
        "section": ParagraphStyle("OffSection", parent=base["Heading2"], fontSize=11, textColor=PURPLE, spaceBefore=10, spaceAfter=6, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("OffBody", parent=base["Normal"], fontSize=9, textColor=NAVY, leading=12, alignment=TA_JUSTIFY),
        "small": ParagraphStyle("OffSmall", parent=base["Normal"], fontSize=8, textColor=NAVY, leading=11),
        "center": ParagraphStyle("OffCenter", parent=base["Normal"], fontSize=9, textColor=NAVY, alignment=TA_CENTER),
        "cell": ParagraphStyle("OffCell", parent=base["Normal"], fontSize=8, textColor=NAVY, leading=11),
        "head": ParagraphStyle("OffHead", parent=base["Normal"], fontSize=8, textColor=colors.white, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "footer": ParagraphStyle("OffFooter", parent=base["Normal"], fontSize=8, textColor=TEAL, alignment=TA_CENTER),
    }


def _header_table(souscription: Souscription, left_label: str):
    from app.services.pdf_service import _build_logo_header_flowable

    styles = _styles()
    logos = _build_logo_header_flowable(souscription)
    banner = Table(
        [[Paragraph(left_label, styles["center"])]],
        colWidths=[18 * cm],
    )
    banner.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#9AA4B2")),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_ROW),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [logos, Spacer(1, 0.25 * cm), banner, Spacer(1, 0.3 * cm)]


def _info_grid(headers: list[str], values: list[str], styles) -> Table:
    head = [Paragraph(h, styles["head"]) for h in headers]
    vals = [Paragraph(v or "—", styles["cell"]) for v in values]
    table = Table([head, vals], colWidths=[6 * cm] * len(headers))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_ROW),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD2D9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def generate_attestation_assistance_voyage(
    souscription: Souscription,
    user: Optional[User],
    numero_attestation: str,
    *,
    traveler_info: Optional[dict[str, Any]] = None,
    exemplaire: str = "assuré",
    card_image: Optional[BytesIO] = None,
    qr_image_data: Optional[BytesIO] = None,
    verification_url: Optional[str] = None,
    minors_info: Optional[list[dict[str, Any]]] = None,
    medecin_conseil: Optional[dict[str, Any]] = None,
) -> BytesIO:
    styles = _styles()
    produit = getattr(souscription, "produit_assurance", None)
    projet = getattr(souscription, "projet_voyage", None)
    dest = "—"
    if projet:
        dest_country = getattr(projet, "destination_country", None)
        dest = getattr(dest_country, "nom", None) or getattr(projet, "destination", None) or "—"
    zone = getattr(produit, "zone_geographique", None) or getattr(projet, "zone_code", None) or "—"
    traveler = _traveler(user, traveler_info)
    ayants_droit = _format_ayants_droit(minors_info)
    medecin = _medecin_conseil_lines(medecin_conseil)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.4 * cm,
    )
    story = []
    card_bytes = None
    if card_image:
        try:
            card_image.seek(0)
            card_bytes = card_image.read()
        except Exception:
            card_bytes = None
    qr_bytes = None
    if qr_image_data:
        try:
            qr_image_data.seek(0)
            qr_bytes = qr_image_data.read()
        except Exception:
            qr_bytes = None

    def build_exemplaire(kind: str) -> list:
        pages = []
        banners = {
            "assuré": "Exemplaire destiné à l'assuré",
            "assureur": "Exemplaire destiné à l'assureur",
            "consulat": "Exemplaire destiné aux Consulats",
        }
        banner = banners.get(kind, banners["assuré"])
        section1_title = (
            "1 INFORMATIONS SUR L'ASSURÉ ET SES AYANTS DROIT"
            if kind == "assuré"
            else "1 INFORMATIONS DE L'ASSURÉ"
        )
        pages.extend(_header_table(souscription, banner))
        pages.append(Paragraph("ATTESTATION D'ASSISTANCE VOYAGE", styles["title"]))
        pages.append(Paragraph(f"<b>{numero_attestation}</b>", styles["center"]))
        pages.append(Spacer(1, 0.25 * cm))
        pages.append(Paragraph(section1_title, styles["section"]))
        pages.append(_info_grid(
            ["NOM ET PRÉNOM", "DATE DE NAISSANCE", "N° PASSEPORT / PIÈCE D'IDENTITÉ"],
            [traveler["name"], traveler["birth"], traveler["passport"]],
            styles,
        ))
        pages.append(Spacer(1, 0.12 * cm))
        pages.append(_info_grid(
            ["NATIONALITÉ", "PAYS DE RÉSIDENCE", "PAYS DE DESTINATION"],
            [traveler["nationality"], traveler["residence"], str(dest)],
            styles,
        ))
        pages.append(Spacer(1, 0.12 * cm))
        pages.append(_info_grid(
            ["ZONE DE COUVERTURE", "DÉBUT DE VALIDITÉ", "FIN DE VALIDITÉ"],
            [str(zone), _fmt_date(souscription.date_debut), _fmt_date(souscription.date_fin)],
            styles,
        ))
        pages.append(Spacer(1, 0.12 * cm))
        pages.append(_info_grid(
            ["NOM, PRÉNOM ET AGE DES AYANTS DROIT"],
            [ayants_droit],
            styles,
        ))
        pages.append(Paragraph("2 INFORMATIONS SUR LES GARANTIES DE LA POLICE", styles["section"]))
        pages.append(Paragraph(
            "L'assuré bénéficie des garanties suivantes d'assistance voyage :",
            styles["body"],
        ))
        pages.append(Spacer(1, 0.12 * cm))
        garanties = _garanties_rows(produit)
        table_data = [[
            Paragraph("GARANTIES", styles["head"]),
            Paragraph("PLAFONDS", styles["head"]),
        ]]
        for title, cap in garanties:
            if cap is None:
                table_data.append([
                    Paragraph(f"<b>{title}</b>", ParagraphStyle("cat", parent=styles["cell"], textColor=PURPLE)),
                    Paragraph("", styles["cell"]),
                ])
            else:
                table_data.append([
                    Paragraph(title, styles["cell"]),
                    Paragraph(cap, styles["cell"]),
                ])
        gtable = Table(table_data, colWidths=[12.2 * cm, 5.8 * cm])
        gtable.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD2D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ]))
        pages.append(gtable)

        if kind == "assuré":
            pages.append(Spacer(1, 0.25 * cm))
            pages.append(Paragraph(
                "3 VOTRE CARTE D'ASSURANCE VOYAGE & LES INFORMATIONS DU MÉDECIN CONSEIL",
                styles["section"],
            ))
            if card_bytes:
                try:
                    pages.append(Image(BytesIO(card_bytes), width=12 * cm, height=7.2 * cm, kind="proportional"))
                except Exception:
                    pass
            pages.append(Spacer(1, 0.15 * cm))
            pages.append(Paragraph("INFORMATIONS SUR LE MÉDECIN CONSEIL", styles["section"]))
            pages.append(_info_grid(
                ["NOM", "PRÉNOM", "TÉLÉPHONE"],
                [medecin["nom"], medecin["prenom"], medecin["tel"]],
                styles,
            ))
            pages.append(Spacer(1, 0.12 * cm))
            pages.append(_info_grid(
                ["E-MAIL", "N° CENTRE D'ALERTE"],
                [medecin["email"], medecin["alerte"]],
                styles,
            ))
            pages.extend(_dispositions_speciales(styles, section_num=4))
        else:
            pages.extend(_dispositions_speciales(styles, section_num=3))

        city = settings.ASSURANCE_CITY or "Abidjan"
        pages.append(Spacer(1, 0.3 * cm))
        pages.append(Paragraph(f"Fait à <b>{city}</b>, le <b>{_fmt_date(datetime.utcnow())}</b>.", styles["body"]))
        pages.append(Spacer(1, 0.6 * cm))
        pages.append(Table(
            [[
                Paragraph("POUR L'ASSUREUR", ParagraphStyle("s", parent=styles["cell"], textColor=TEAL, fontName="Helvetica-Bold")),
                Paragraph("SIGNATURE DE L'ASSURÉ", ParagraphStyle("s2", parent=styles["cell"], textColor=TEAL, fontName="Helvetica-Bold", alignment=1)),
            ]],
            colWidths=[9 * cm, 9 * cm],
        ))
        if qr_bytes and kind == "assuré":
            try:
                pages.append(Spacer(1, 0.4 * cm))
                pages.append(Image(BytesIO(qr_bytes), width=3 * cm, height=3 * cm))
                if verification_url:
                    pages.append(Paragraph(f"Vérification : {verification_url}", styles["small"]))
            except Exception:
                pass
        pages.append(Spacer(1, 0.4 * cm))
        pages.append(Paragraph(
            "Document électronique généré par MyMHC • Police " + (souscription.numero_souscription or ""),
            styles["footer"],
        ))
        return pages

    requested = (exemplaire or "assuré").strip().lower()
    if requested in {"consulat"}:
        kinds = ["consulat"]
    elif requested in {"assureur"}:
        kinds = ["assureur"]
    elif requested in {"assuré", "assure"}:
        kinds = ["assuré"]
    else:
        kinds = ["assuré", "assureur", "consulat"]

    for index, kind in enumerate(kinds):
        if index:
            story.append(PageBreak())
        story.extend(build_exemplaire(kind))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_avenant_annulation(
    souscription: Souscription,
    user: Optional[User],
    numero_avenant: str,
    *,
    traveler_info: Optional[dict[str, Any]] = None,
) -> BytesIO:
    styles = _styles()
    produit = getattr(souscription, "produit_assurance", None)
    projet = getattr(souscription, "projet_voyage", None)
    dest = "—"
    if projet:
        dest_country = getattr(projet, "destination_country", None)
        dest = getattr(dest_country, "nom", None) or getattr(projet, "destination", None) or "—"
    traveler = _traveler(user, traveler_info)
    assureur = getattr(produit, "assureur", None) or settings.ASSURANCE_NAME
    zone = getattr(produit, "zone_geographique", None) or "—"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.4 * cm, rightMargin=1.4 * cm, topMargin=1.2 * cm, bottomMargin=1.4 * cm)
    story = []
    story.extend(_header_table(souscription, "Avenant distinct de l'attestation initiale"))
    story.append(Paragraph("AVENANT D'ANNULATION DE POLICE", styles["title"]))
    story.append(Paragraph("1 INFORMATIONS", styles["section"]))
    story.append(_info_grid(
        ["N° DE POLICE", "N° D'ANNULATION", "DATE D'ANNULATION"],
        [souscription.numero_souscription or "—", numero_avenant, _fmt_date(datetime.utcnow())],
        styles,
    ))
    story.append(Spacer(1, 0.12 * cm))
    story.append(_info_grid(
        ["NOM ET PRÉNOM", "DATE DE NAISSANCE", "N° PASSEPORT / PIÈCE D'IDENTITÉ"],
        [traveler["name"], traveler["birth"], traveler["passport"]],
        styles,
    ))
    story.append(Spacer(1, 0.12 * cm))
    story.append(_info_grid(
        ["NATIONALITÉ", "PAYS DE RÉSIDENCE", "PAYS DE DESTINATION"],
        [traveler["nationality"], traveler["residence"], str(dest)],
        styles,
    ))
    story.append(Spacer(1, 0.12 * cm))
    story.append(_info_grid(
        ["ZONE DE COUVERTURE", "DÉBUT DE VALIDITÉ", "FIN DE VALIDITÉ"],
        [str(zone), _fmt_date(souscription.date_debut), _fmt_date(souscription.date_fin)],
        styles,
    ))
    story.append(Paragraph("2 PORTÉE ET EFFETS DE L'ANNULATION", styles["section"]))
    story.append(Paragraph(
        f"Mobility Health Care informe le souscripteur que la police d'assurance voyage référencée "
        f"<b>{souscription.numero_souscription or 'XXXXXXX'}</b> souscrite auprès de "
        f"<b>{assureur or 'XXX'}</b> est <b>ANNULÉE</b> à sa demande.",
        styles["body"],
    ))
    story.append(Paragraph(
        "En conséquence, aucune garantie n'a été ni ne peut être activée, et aucune déclaration de sinistre ne peut être déposée au titre de cette police.",
        styles["body"],
    ))
    city = settings.ASSURANCE_CITY or "Abidjan"
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"Fait à <b>{city}</b>, le <b>{_fmt_date(datetime.utcnow())}</b>.", styles["body"]))
    story.append(Spacer(1, 0.7 * cm))
    story.append(Table(
        [[
            Paragraph("POUR L'ASSUREUR", ParagraphStyle("s", parent=styles["cell"], textColor=TEAL, fontName="Helvetica-Bold")),
            Paragraph("POUR L'ASSURÉ", ParagraphStyle("s2", parent=styles["cell"], textColor=TEAL, fontName="Helvetica-Bold", alignment=1)),
        ]],
        colWidths=[9 * cm, 9 * cm],
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Document électronique généré par MyMHC • À conserver avec la police annulée", styles["footer"]))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_quittance_paiement(
    souscription: Souscription,
    paiement: Paiement,
    user: Optional[User],
    numero_quittance: str,
    *,
    traveler_info: Optional[dict[str, Any]] = None,
) -> BytesIO:
    styles = _styles()
    traveler = _traveler(user, traveler_info)
    total = getattr(paiement, "montant", None) or getattr(souscription, "prix_applique", 0)
    prime = getattr(souscription, "prime_assurance", None) or total
    try:
        total_dec = Decimal(str(total))
        prime_dec = Decimal(str(prime))
        taxes = (total_dec - prime_dec) if total_dec > prime_dec else Decimal("0")
        police_cost = Decimal("0")
    except Exception:
        total_dec = prime_dec = taxes = police_cost = Decimal("0")
    method = getattr(paiement, "type_paiement", None)
    method_label = method.value.replace("_", " ").upper() if hasattr(method, "value") else str(method or "AUTRE")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
    story = []
    story.append(Paragraph("QUITTANCE DE PAIEMENT", styles["title"]))
    story.append(Spacer(1, 0.2 * cm))
    meta = Table(
        [[
            Paragraph(f"<b>N° DE QUITTANCE</b><br/>{numero_quittance}", styles["cell"]),
            Paragraph(f"<b>DATE ET HEURE D'ÉMISSION</b><br/>{_fmt_date(datetime.utcnow(), with_time=True)}", styles["cell"]),
            Paragraph("<b>STATUT DU PAIEMENT</b><br/>PAYÉ", ParagraphStyle("paid", parent=styles["cell"], alignment=1, fontName="Helvetica-Bold")),
        ]],
        colWidths=[6 * cm, 6.5 * cm, 5.5 * cm],
    )
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD2D9")),
        ("BACKGROUND", (2, 0), (2, 0), PAID_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph("IDENTIFICATION DU VOYAGEUR", styles["section"]))
    story.append(_info_grid(
        ["NOM ET PRÉNOMS", "NUMÉRO DE POLICE"],
        [traveler["name"], souscription.numero_souscription or "—"],
        styles,
    ))
    story.append(Paragraph("DÉTAILS DU PAIEMENT", styles["section"]))
    rows = [
        [Paragraph("MONTANT DE LA PRIME", styles["cell"]), Paragraph(_money(prime_dec), styles["cell"])],
        [Paragraph("COÛT DE POLICE", styles["cell"]), Paragraph(_money(police_cost), styles["cell"])],
        [Paragraph("TAXES", styles["cell"]), Paragraph(_money(taxes), styles["cell"])],
        [Paragraph("<b>MONTANT TOTAL PAYÉ</b>", ParagraphStyle("tot", parent=styles["head"])), Paragraph(f"<b>{_money(total_dec)}</b>", ParagraphStyle("tot2", parent=styles["head"]))],
        [Paragraph("MOYEN DE PAIEMENT", styles["cell"]), Paragraph(method_label, styles["cell"])],
    ]
    pay = Table(rows, colWidths=[10 * cm, 8 * cm])
    pay.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD2D9")),
        ("BACKGROUND", (0, 3), (-1, 3), TEAL),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(pay)
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        f"<b>Montant total payé en lettres :</b> {_amount_in_words(total_dec)}",
        styles["body"],
    ))
    story.append(Spacer(1, 0.3 * cm))
    notice = Table(
        [[Paragraph(
            "La présente quittance certifie l'enregistrement du paiement indiqué ci-dessus au titre de la souscription "
            "de l'assistance voyage référencée. Elle est générée automatiquement par la plateforme MyMHC après validation "
            "de la transaction. Elle ne peut être modifiée et ne vaut pas, à elle seule, attestation d'assurance. "
            "La couverture est acquise conformément aux dates, garanties, exclusions et conditions prévues au contrat émis par l'assureur.",
            styles["small"],
        )]],
        colWidths=[18 * cm],
    )
    notice.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_ROW),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(notice)
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Document électronique généré par MyMHC • À conserver comme justificatif de paiement", styles["footer"]))
    doc.build(story)
    buffer.seek(0)
    return buffer
