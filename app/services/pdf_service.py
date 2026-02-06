import os
from io import BytesIO
from datetime import datetime as dt, date
from typing import Dict, Any, Optional, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
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


# Chemins logos (alignés sur card_service)
_LOGO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend-simple",
    "assets",
)
MOBILITY_LOGO_PATH = os.path.join(_LOGO_DIR, "mobility-logo.png")


def _load_logo_bytes_mobility() -> Optional[BytesIO]:
    """Charge le logo Mobility Health en bytes pour le PDF."""
    path = getattr(settings, "MOBILITY_HEALTH_LOGO_PATH", None) or MOBILITY_LOGO_PATH
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return BytesIO(f.read())
        except Exception:
            pass
    url = getattr(settings, "MOBILITY_HEALTH_LOGO_URL", None)
    if url:
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                r = client.get(url)
                if r.status_code == 200:
                    return BytesIO(r.content)
        except Exception:
            pass
    return None


def _load_logo_bytes_assureur(souscription: Souscription) -> Optional[BytesIO]:
    """Charge le logo de l'assureur (produit lié à la souscription) en bytes pour le PDF."""
    try:
        produit = getattr(souscription, "produit_assurance", None)
        if not produit:
            return None
        assureur = getattr(produit, "assureur_obj", None)
        if not assureur:
            return None
        logo_url = getattr(assureur, "logo_url", None)
        if not logo_url:
            return None
        if logo_url.startswith("http"):
            import httpx
            with httpx.Client(timeout=5.0) as client:
                r = client.get(logo_url)
                if r.status_code == 200:
                    return BytesIO(r.content)
            return None
        if os.path.exists(logo_url):
            with open(logo_url, "rb") as f:
                return BytesIO(f.read())
        from app.services.minio_service import MinioService
        for bucket in ["logos", "assureurs", "assets", MinioService.BUCKET_ATTESTATIONS]:
            try:
                data = MinioService.get_file(bucket, logo_url)
                if data:
                    return BytesIO(data)
            except Exception:
                continue
    except Exception:
        pass
    return None


def _build_garanties_table_flowable(garanties_list: List[Dict[str, Any]], normal_style) -> Optional[Table]:
    """
    Construit un tableau ReportLab pour la section Garanties accordées.
    Colonnes : Garantie, Franchise, Capitaux, Obligatoire.
    Le frontend (admin-products) envoie titre, franchise, capitaux, obligatoire.
    """
    if not garanties_list:
        return None
    rows = [["Garantie", "Franchise", "Capitaux", "Obligatoire"]]
    for g in garanties_list:
        # Libellé : titre (frontend), nom/libelle (seed/API), name, description en secours
        nom = (
            g.get("titre")
            or g.get("nom")
            or g.get("libelle")
            or g.get("garantie")
            or g.get("name")
            or g.get("description")
            or "—"
        )
        franchise = g.get("franchise")
        if franchise is not None and not isinstance(franchise, str):
            franchise = str(franchise)
        else:
            franchise = franchise or "0"
        # Capitaux : capitaux (frontend), montant_max, plafond, montant
        capitaux = g.get("capitaux") or g.get("montant_max") or g.get("plafond") or g.get("montant")
        if capitaux is not None and not isinstance(capitaux, str):
            capitaux = str(capitaux)
        else:
            capitaux = capitaux or "—"
        obl = g.get("obligatoire")
        if obl is True or (isinstance(obl, str) and str(obl).lower() in ("oui", "yes", "true", "1")):
            obl_str = "Oui"
        elif obl is False or (isinstance(obl, str) and str(obl).lower() in ("non", "no", "false", "0")):
            obl_str = "Non"
        else:
            obl_str = "Oui"
        rows.append([str(nom), str(franchise), str(capitaux), obl_str])
    col_widths = [7 * cm, 3 * cm, 3 * cm, 2.5 * cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 0), (2, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    return t


def _build_logo_header_flowable(souscription: Souscription):
    """
    Construit l'en-tête avec logo Mobility Health (gauche) et logo assureur (droite).
    Retourne un flowable (Table) à insérer en haut des attestations.
    """
    logo_w, logo_h = 3.5 * cm, 1.2 * cm
    mobility_io = _load_logo_bytes_mobility()
    assureur_io = _load_logo_bytes_assureur(souscription)
    left_flowable = None
    right_flowable = None
    if mobility_io:
        try:
            mobility_io.seek(0)
            left_flowable = Image(mobility_io, width=logo_w, height=logo_h, kind="proportional")
        except Exception:
            _styles = getSampleStyleSheet()
            left_flowable = Paragraph("<i>Mobility Health</i>", _styles["Normal"])
    if assureur_io:
        try:
            assureur_io.seek(0)
            right_flowable = Image(assureur_io, width=logo_w, height=logo_h, kind="proportional")
        except Exception:
            right_flowable = None
    if not left_flowable:
        _styles = getSampleStyleSheet()
        left_flowable = Paragraph("<i>Mobility Health</i>", _styles["Normal"])
    if not right_flowable:
        right_flowable = Spacer(1, logo_w)
    col_widths = [9 * cm, 9 * cm]
    t = Table([[left_flowable, right_flowable]], colWidths=col_widths)
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _format_date_cp(value, include_time=False):
    """Format date for Conditions Particulières."""
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, dt):
        return value.strftime("%d/%m/%Y à %H:%M") if include_time else value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return "N/A"


def _garanties_from_product(produit) -> Dict[str, Dict[str, str]]:
    """
    Extrait un dictionnaire de garanties par type depuis produit.garanties (JSON).
    Chaque entrée a les clés montant_max et franchise.
    Mapping par mots-clés dans le nom de la garantie.
    """
    result = {
        "frais_medicaux": {"montant": "N/A", "franchise": "N/A"},
        "rapatriement": {"montant": "N/A", "franchise": "0 €"},
        "assistance_deces": {"montant": "N/A", "franchise": "0 €"},
        "responsabilité_civile": {"montant": "N/A", "franchise": "N/A"},
        "accident_corporel": {"montant": "N/A", "franchise": "0 €"},
        "bagages": {"montant": "N/A", "franchise": "N/A"},
        "annulation": {"montant": "N/A", "franchise": "N/A"},
    }
    if not produit or not getattr(produit, "garanties", None):
        return result
    garanties = produit.garanties or []
    for g in garanties:
        nom = (g.get("nom") or g.get("libelle") or "").lower()
        montant = g.get("montant_max") or g.get("montant") or g.get("plafond") or "N/A"
        franchise = g.get("franchise") or "0 €"
        if "frais médicaux" in nom or "hospitalisation" in nom or "médicaux d'urgence" in nom:
            result["frais_medicaux"] = {"montant": str(montant), "franchise": str(franchise)}
        elif "rapatriement" in nom:
            result["rapatriement"] = {"montant": str(montant), "franchise": str(franchise)}
        elif "décès" in nom or "deces" in nom:
            result["assistance_deces"] = {"montant": str(montant), "franchise": str(franchise)}
        elif "responsabilité" in nom or "responsabilite" in nom or "civile" in nom:
            result["responsabilité_civile"] = {"montant": str(montant), "franchise": str(franchise)}
        elif "accident corporel" in nom or "invalidité" in nom or "invalidite" in nom:
            result["accident_corporel"] = {"montant": str(montant), "franchise": str(franchise)}
        elif "bagages" in nom or "bagage" in nom:
            result["bagages"] = {"montant": str(montant), "franchise": str(franchise)}
        elif "annulation" in nom or "interruption" in nom:
            result["annulation"] = {"montant": str(montant), "franchise": str(franchise)}
    return result


def _build_conditions_context(
    souscription: Souscription,
    paiement: Paiement,
    user: User,
    traveler_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construit le dictionnaire de contexte pour remplir les Conditions Particulières
    et la Police d'assurance à partir de la souscription, du paiement, de l'utilisateur
    et des informations voyageur (questionnaire).
    """
    produit = getattr(souscription, "produit_assurance", None)
    projet = getattr(souscription, "projet_voyage", None)
    assureur_obj = getattr(produit, "assureur_obj", None) if produit else None

    # Compagnie d'assurance
    nom_compagnie = (
        (assureur_obj.nom if assureur_obj else None)
        or (getattr(produit, "assureur", None) if produit else None)
        or settings.ASSURANCE_NAME
    )
    siege_social = (
        (getattr(assureur_obj, "adresse", None) if assureur_obj else None)
        or settings.ASSURANCE_ADDRESS
    )
    assurance_telephone = (
        (getattr(assureur_obj, "telephone", None) if assureur_obj else None)
        or settings.ASSURANCE_PHONE
    )
    assurance_email = (
        getattr(settings, "ASSURANCE_EMAIL", None) or getattr(settings, "SMTP_FROM_EMAIL", None) or "contact@mobilityhealth.com"
    )
    assurance_site = getattr(settings, "ASSURANCE_SITE_WEB", None) or "https://srv1324425.hstgr.cloud"
    assurance_ville = getattr(settings, "ASSURANCE_CITY", None) or "Abidjan"

    # Assuré (voyageur)
    if traveler_info and traveler_info.get("fullName"):
        nom_assure = traveler_info.get("fullName", "")
        email_assure = traveler_info.get("email") or user.email
        adresse_assure = traveler_info.get("address") or "Non renseignée"
        phone_assure = traveler_info.get("phone") or getattr(user, "telephone", None) or ""
        nationalite_assure = traveler_info.get("nationality") or getattr(user, "nationalite", None) or "Non renseignée"
        numero_passeport = traveler_info.get("passportNumber") or getattr(user, "numero_passeport", None) or "Non renseigné"
        passport_expiry = traveler_info.get("passportExpiryDate")
        birth_date = traveler_info.get("birthDate")
        birth_place = traveler_info.get("birthPlace") or traveler_info.get("lieu_naissance") or "Non renseigné"
        profession_assure = traveler_info.get("profession") or traveler_info.get("occupation") or "Non renseignée"
    else:
        nom_assure = user.full_name or user.username or "N/A"
        email_assure = user.email or ""
        adresse_assure = (
            getattr(user, "adresse", None) or getattr(user, "address", None) or getattr(user, "city", None) or "Non renseignée"
        )
        phone_assure = getattr(user, "telephone", None) or ""
        nationalite_assure = getattr(user, "nationalite", None) or "Non renseignée"
        numero_passeport = getattr(user, "numero_passeport", None) or "Non renseigné"
        passport_expiry = getattr(user, "validite_passeport", None)
        birth_date = getattr(user, "date_naissance", None)
        birth_place = "Non renseigné"
        profession_assure = "Non renseignée"

    if passport_expiry and not isinstance(passport_expiry, str):
        try:
            passport_expiry = _format_date_cp(passport_expiry)
        except Exception:
            passport_expiry = str(passport_expiry)
    elif not passport_expiry:
        passport_expiry = "Non renseigné"

    date_naissance_str = _format_date_cp(birth_date) if birth_date else "Non renseignée"
    date_et_lieu_naissance = f"{date_naissance_str}, {birth_place}" if date_naissance_str != "Non renseignée" else birth_place
    coordonnees = " / ".join(filter(None, [phone_assure, email_assure])) or "Non renseignées"

    # Contrat et voyage
    date_effet = souscription.date_debut
    date_expiration = souscription.date_fin
    duree_jours = 0
    if date_effet and date_expiration:
        try:
            delta = date_expiration - date_effet
            duree_jours = max(0, delta.days)
        except Exception:
            pass
    duree_voyage = f"{duree_jours} jour(s)" if duree_jours else "Non définie"
    date_souscription = getattr(souscription, "created_at", None) or date_effet
    num_contrat = souscription.numero_souscription
    zone_couverture = "Non définie"
    if produit and getattr(produit, "zones_geographiques", None):
        zg = produit.zones_geographiques
        if isinstance(zg, dict) and zg.get("zones"):
            zone_couverture = ", ".join(zg["zones"]) if isinstance(zg["zones"], list) else str(zg["zones"])
    elif projet:
        zone_couverture = getattr(projet, "destination", None) or zone_couverture
    pays_destination = (getattr(projet, "destination", None) if projet else None) or zone_couverture
    motif_voyage = getattr(projet, "description", None) or getattr(projet, "titre", None) or "Voyage"
    if motif_voyage and len(motif_voyage) > 50:
        motif_voyage = motif_voyage[:47] + "..."

    # Âge maximum produit
    age_max = getattr(produit, "age_maximum", None)
    age_max_str = str(age_max) if age_max is not None else "Non spécifié"

    # Prime et paiement
    total_payer = float(souscription.prix_applique) if souscription.prix_applique else 0.0
    primes = getattr(produit, "primes_generees", None) or {}
    prime_nette = primes.get("prime_nette")
    taxes_frais = primes.get("taxes") or primes.get("accessoire") or 0
    if prime_nette is None:
        prime_nette = total_payer
    try:
        prime_nette = float(prime_nette)
    except (TypeError, ValueError):
        prime_nette = total_payer
    try:
        taxes_frais = float(taxes_frais)
    except (TypeError, ValueError):
        taxes_frais = 0.0
    mode_paiement = paiement.type_paiement.value.replace("_", " ").title() if hasattr(paiement.type_paiement, "value") else str(paiement.type_paiement)

    # Garanties produit
    garanties = _garanties_from_product(produit)
    fm = garanties["frais_medicaux"]
    rp = garanties["rapatriement"]
    ad = garanties["assistance_deces"]
    rc = garanties["responsabilité_civile"]
    ac = garanties["accident_corporel"]
    bg = garanties["bagages"]
    an = garanties["annulation"]

    return {
        "num_contrat": num_contrat,
        "date_souscription": _format_date_cp(date_souscription),
        "date_effet": _format_date_cp(date_effet),
        "date_expiration": _format_date_cp(date_expiration),
        "duree_voyage": duree_voyage,
        "compagnie_assurance": nom_compagnie,
        "siege_social": siege_social,
        "intermediaire": "Mobility Health",
        "nom_assure": nom_assure,
        "date_et_lieu_naissance": date_et_lieu_naissance,
        "date_naissance": date_naissance_str,
        "adresse_assure": adresse_assure,
        "coordonnees": coordonnees,
        "profession_assure": profession_assure,
        "nationalite_assure": nationalite_assure,
        "numero_passeport": numero_passeport,
        "date_expiration_passeport": passport_expiry,
        "pays_destination": pays_destination,
        "zone_couverture": zone_couverture,
        "motif_voyage": motif_voyage,
        "age_maximum": age_max_str,
        "prime_nette": f"{prime_nette:,.2f} €".replace(",", " "),
        "taxes_frais": f"{taxes_frais:,.2f} €".replace(",", " "),
        "total_payer": f"{total_payer:,.2f} €".replace(",", " "),
        "mode_paiement": mode_paiement,
        "frais_medicaux_montant": fm["montant"],
        "frais_medicaux_franchise": fm["franchise"],
        "rapatriement_montant": rp["montant"],
        "assistance_deces_montant": ad["montant"],
        "rc_montant": rc["montant"],
        "rc_franchise": rc["franchise"],
        "accident_corporel_montant": ac["montant"],
        "bagages_montant": bg["montant"],
        "bagages_franchise": bg["franchise"],
        "annulation_montant": an["montant"],
        "annulation_franchise": an["franchise"],
        "assurance_telephone": assurance_telephone,
        "assurance_email": assurance_email,
        "assurance_site": assurance_site,
        "assurance_ville": assurance_ville,
        "date_emission": _format_date_cp(dt.now()),
        "date_depart": _format_date_cp(getattr(projet, "date_depart", None) or date_effet) if projet or date_effet else _format_date_cp(date_effet),
        "date_retour": _format_date_cp(getattr(projet, "date_retour", None) or date_expiration) if projet or date_expiration else _format_date_cp(date_expiration),
        "garanties_list": list(produit.garanties) if produit and getattr(produit, "garanties", None) else [],
    }


class PDFService:
    """Service pour générer des attestations PDF"""
    
    @staticmethod
    def generate_attestation_provisoire(
        souscription: Souscription,
        paiement: Paiement,
        user: User,
        numero_attestation: str,
        qr_image_data: Optional[BytesIO] = None,
        verification_url: Optional[str] = None,
        traveler_info: Optional[Dict[str, Any]] = None
    ) -> BytesIO:
        """Génère une attestation provisoire au format PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        def format_date(value: Optional[object], include_time: bool = False) -> str:
            if not value:
                return "N/A"
            if isinstance(value, str):
                return value
            if isinstance(value, dt):
                return value.strftime("%d/%m/%Y %H:%M") if include_time else value.strftime("%d/%m/%Y")
            if isinstance(value, date):
                return value.strftime("%d/%m/%Y")
            if hasattr(value, "strftime"):
                return value.strftime("%d/%m/%Y")
            return "N/A"
        
        produit = getattr(souscription, "produit_assurance", None)
        projet = getattr(souscription, "projet_voyage", None)
        
        assurance_name = settings.ASSURANCE_NAME or (produit.assureur if produit else None) or "Mobility Health"
        assurance_address = settings.ASSURANCE_ADDRESS or "Adresse non renseignée"
        assurance_phone = settings.ASSURANCE_PHONE or "N/A"
        assurance_email = settings.ASSURANCE_EMAIL or settings.SMTP_FROM_EMAIL
        assurance_city = settings.ASSURANCE_CITY or "Abidjan"
        agent_name = settings.ASSURANCE_AGENT_NAME or settings.SMTP_FROM_NAME
        agent_title = settings.ASSURANCE_AGENT_TITLE or "Représentant habilité"
        
        # Utiliser les informations du voyageur si disponibles, sinon fallback sur l'utilisateur
        # IMPORTANT: Pour une souscription pour un tiers, traveler_info contient les infos du tiers
        # depuis le questionnaire administratif. Sinon, il contient les infos de l'abonné.
        if traveler_info and traveler_info.get("fullName"):
            insured_name = traveler_info.get("fullName", "")
            insured_birth = traveler_info.get("birthDate")
            insured_address = traveler_info.get("address") or "Adresse non renseignée"
            # Logger pour debug
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"PDF Attestation - Utilisation des informations du voyageur depuis traveler_info: {insured_name}"
            )
        else:
            # Fallback sur l'utilisateur (abonné) si traveler_info est vide
            insured_name = user.full_name or user.username
            insured_birth = getattr(user, "date_naissance", None)
            insured_address = (
                getattr(user, "adresse", None)
                or getattr(user, "address", None)
                or getattr(user, "city", None)
                or "Adresse non renseignée"
            )
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"PDF Attestation - traveler_info vide, utilisation de l'abonné (fallback): {insured_name}"
            )
        
        destination = projet.destination if projet and getattr(projet, "destination", None) else "N/A"
        travel_objective = (
            getattr(projet, "objet_voyage", None)
            or getattr(projet, "description", None)
            or getattr(projet, "notes", None)
            or "Voyage"
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=8
        )
        
        # Logos : Mobility Health (gauche), Assureur (droite)
        story.append(_build_logo_header_flowable(souscription))
        story.append(Spacer(1, 0.4*cm))
        
        # En-tête général
        story.append(Paragraph("ATTESTATION DE VOYAGE PROVISOIRE", title_style))
        story.append(Spacer(1, 0.5*cm))
        
        info_lines = [
            ("Nom de l'assurance / organisme", assurance_name),
            ("Adresse", assurance_address),
            ("Téléphone", assurance_phone),
            ("Email", assurance_email),
            ("ATTESTATION DE VOYAGE PROVISOIRE N°", numero_attestation),
            ("Date d'émission", format_date(dt.utcnow(), include_time=True)),
        ]
        for label, value in info_lines:
            story.append(Paragraph(f"<b>{label} :</b> {value}", normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph(
            f"Je soussigné(e), {agent_name}, en qualité de {agent_title}, certifie que :",
            normal_style
        ))
        story.append(Spacer(1, 0.3*cm))
        
        # Informations sur l'assuré
        passport_number = traveler_info.get("passportNumber", "") if traveler_info else ""
        passport_expiry = traveler_info.get("passportExpiryDate", "") if traveler_info else ""
        
        assured_data = [
            ["M./Mme :", insured_name],
            ["Date de naissance :", format_date(insured_birth)],
            ["Adresse :", insured_address],
        ]
        
        # Ajouter les informations de passeport si disponibles
        if passport_number:
            assured_data.append(["Numéro de passeport :", passport_number])
        if passport_expiry:
            # Formater la date d'expiration
            try:
                from datetime import datetime
                expiry_date = dt.fromisoformat(passport_expiry.replace('Z', '+00:00'))
                assured_data.append(["Date d'expiration du passeport :", format_date(expiry_date)])
            except:
                assured_data.append(["Date d'expiration du passeport :", passport_expiry])
        
        assured_data.append(["Numéro de police d'assurance :", souscription.numero_souscription])
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ])
        
        table_assure = Table(assured_data, colWidths=[6*cm, 11*cm])
        table_assure.setStyle(table_style)
        story.append(table_assure)
        story.append(Spacer(1, 0.5*cm))
        
        # Informations de voyage
        travel_data = [
            ["Destination :", destination],
            ["Date de départ :", format_date(souscription.date_debut)],
            ["Date de retour prévue :", format_date(souscription.date_fin)],
            ["Objet du voyage :", travel_objective],
        ]
        table_travel = Table(travel_data, colWidths=[6*cm, 11*cm])
        table_travel.setStyle(table_style)
        story.append(Paragraph("Bénéficie d'une couverture provisoire pour le voyage suivant :", heading_style))
        story.append(table_travel)
        story.append(Spacer(1, 0.3*cm))
        
        validity_text = (
            f"Cette attestation est valable uniquement pour la période du {format_date(souscription.date_debut)} "
            f"au {format_date(souscription.date_fin)} et constitue une preuve provisoire de la couverture "
            "d'assurance en attendant l'émission définitive de la police d'assurance."
        )
        story.append(Paragraph(validity_text, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Conditions
        conditions = [
            "La couverture est effective à compter de la date d'émission de la présente attestation.",
            "Cette attestation ne remplace pas le contrat définitif d'assurance.",
            "Toute modification du voyage (dates, destination, participants) doit être signalée immédiatement à l’assurance."
        ]
        story.append(Paragraph("Conditions :", heading_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(item, normal_style)) for item in conditions],
            bulletType='bullet',
            leftIndent=1*cm
        ))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph(f"Fait à : {assurance_city}, le {format_date(dt.utcnow())}", normal_style))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(f"{agent_name}<br/>{agent_title}", normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        # QR Code de vérification
        if qr_image_data:
            qr_image_data.seek(0)
            story.append(Paragraph("VÉRIFICATION PAR QR CODE", heading_style))
            story.append(Spacer(1, 0.2*cm))
            qr_img = Image(qr_image_data, width=4*cm, height=4*cm)
            story.append(qr_img)
            if verification_url:
                story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph(
                    f"Scannez ou visitez : <u>{verification_url}</u>",
                    normal_style
                ))
            story.append(Spacer(1, 0.5*cm))

        # Date d'émission
        date_style = ParagraphStyle(
            'Date',
            parent=normal_style,
            fontSize=10,
            alignment=TA_RIGHT
        )
        story.append(Paragraph(
            f"Émis le {dt.now().strftime('%d/%m/%Y à %H:%M')}",
            date_style
        ))

        # Annexes
        PDFService._append_conditions_generales(story, heading_style, normal_style)
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_attestation_definitive(
        souscription: Souscription,
        paiement: Paiement,
        user: User,
        numero_attestation: str,
        qr_image_data: Optional[BytesIO] = None,
        verification_url: Optional[str] = None,
        traveler_info: Optional[Dict[str, Any]] = None,
        minors_info: Optional[List[Dict[str, Any]]] = None,
    ) -> BytesIO:
        """Génère une attestation définitive au format PDF.
        minors_info: liste des enfants mineurs à charge (dicts avec nom_complet, date_naissance)."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Styles (similaires à l'attestation provisoire)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=8
        )
        
        # Logos : Mobility Health (gauche), Assureur (droite)
        story.append(_build_logo_header_flowable(souscription))
        story.append(Spacer(1, 0.4*cm))
        
        # En-tête
        story.append(Paragraph("ATTESTATION DÉFINITIVE D'ASSURANCE", title_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Numéro d'attestation
        numero_style = ParagraphStyle(
            'Numero',
            parent=normal_style,
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#28a745')
        )
        story.append(Paragraph(f"<b>N° {numero_attestation}</b>", numero_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Informations de l'assuré (identique à provisoire)
        story.append(Paragraph("INFORMATIONS DE L'ASSURÉ", heading_style))
        # Utiliser les informations du voyageur si disponibles, sinon fallback sur l'utilisateur
        if traveler_info and traveler_info.get("fullName"):
            insured_name = traveler_info.get("fullName", "")
            insured_email = traveler_info.get("email") or user.email
        else:
            insured_name = user.full_name or user.username
            insured_email = user.email
        
        # Récupérer les informations de passeport si disponibles
        passport_number = traveler_info.get("passportNumber", "") if traveler_info else ""
        passport_expiry = traveler_info.get("passportExpiryDate", "") if traveler_info else ""
        
        data_assure = [
            ["Nom complet:", insured_name],
            ["Email:", insured_email],
        ]
        
        # Ajouter les informations de passeport si disponibles
        if passport_number:
            data_assure.append(["Numéro de passeport:", passport_number])
        if passport_expiry:
            # Formater la date d'expiration
            try:
                from datetime import datetime
                expiry_date = dt.fromisoformat(passport_expiry.replace('Z', '+00:00'))
                data_assure.append(["Date d'expiration du passeport:", format_date(expiry_date)])
            except:
                data_assure.append(["Date d'expiration du passeport:", passport_expiry])
        
        data_assure.append(["Numéro de souscription:", souscription.numero_souscription])
        table_assure = Table(data_assure, colWidths=[5*cm, 12*cm])
        table_assure.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table_assure)
        story.append(Spacer(1, 0.3*cm))

        # Enfants mineurs à charge (si présents dans les notes)
        if minors_info:
            story.append(Paragraph("ENFANTS MINEURS À CHARGE", heading_style))
            data_minors = [["Nom complet", "Date de naissance"]]
            for m in minors_info:
                nom_complet = (m.get("nom_complet") or "").strip() or "—"
                date_naissance = (m.get("date_naissance") or "").strip() or "—"
                data_minors.append([nom_complet, date_naissance])
            table_minors = Table(data_minors, colWidths=[10*cm, 7*cm])
            table_minors.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f4fd')),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(table_minors)
            story.append(Spacer(1, 0.3*cm))
        
        # Informations de paiement
        story.append(Paragraph("INFORMATIONS DE PAIEMENT", heading_style))
        data_paiement = [
            ["Montant payé:", f"{float(paiement.montant):.2f} €"],
            ["Type de paiement:", paiement.type_paiement.value.replace('_', ' ').title()],
            ["Référence transaction:", paiement.reference_transaction or "N/A"],
            ["Date de paiement:", paiement.date_paiement.strftime("%d/%m/%Y %H:%M") if paiement.date_paiement else "N/A"],
        ]
        table_paiement = Table(data_paiement, colWidths=[5*cm, 12*cm])
        table_paiement.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table_paiement)
        story.append(Spacer(1, 0.3*cm))
        
        # Informations de couverture
        story.append(Paragraph("INFORMATIONS DE COUVERTURE", heading_style))
        data_couverture = [
            ["Date de début:", souscription.date_debut.strftime("%d/%m/%Y")],
            ["Date de fin:", souscription.date_fin.strftime("%d/%m/%Y") if souscription.date_fin else "Non définie"],
            ["Prix appliqué:", f"{float(souscription.prix_applique):.2f} €"],
        ]
        table_couverture = Table(data_couverture, colWidths=[5*cm, 12*cm])
        table_couverture.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table_couverture)
        story.append(Spacer(1, 0.5*cm))
        
        # Validation
        story.append(Paragraph("VALIDATIONS", heading_style))
        validation_text = (
            "Cette attestation a été validée par :<br/>"
            "✓ Médecin<br/>"
            "✓ Équipe technique<br/>"
            "✓ Agent de production MH"
        )
        validation_style = ParagraphStyle(
            'Validation',
            parent=normal_style,
            fontSize=11,
            textColor=colors.HexColor('#28a745'),
            backColor=colors.HexColor('#d4edda'),
            borderPadding=10,
            borderWidth=1,
            borderColor=colors.HexColor('#28a745')
        )
        story.append(Paragraph(validation_text, validation_style))
        story.append(Spacer(1, 0.5*cm))
        
        # QR Code de vérification
        if qr_image_data:
            qr_image_data.seek(0)
            story.append(Paragraph("VÉRIFICATION PAR QR CODE", heading_style))
            story.append(Spacer(1, 0.2*cm))
            qr_img = Image(qr_image_data, width=4*cm, height=4*cm)
            story.append(qr_img)
            if verification_url:
                story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph(
                    f"Scannez ou visitez : <u>{verification_url}</u>",
                    normal_style
                ))
            story.append(Spacer(1, 0.5*cm))

        # Date d'émission
        date_style = ParagraphStyle(
            'Date',
            parent=normal_style,
            fontSize=10,
            alignment=TA_RIGHT
        )
        story.append(Paragraph(
            f"Émis le {dt.now().strftime('%d/%m/%Y à %H:%M')}",
            date_style
        ))

        # Contexte pour Conditions Particulières et Police (données réelles)
        context = _build_conditions_context(souscription, paiement, user, traveler_info)
        # Annexes
        PDFService._append_conditions_particulieres(story, heading_style, normal_style, context)
        PDFService._append_police_assurance(story, heading_style, normal_style, context)
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _append_conditions_generales(story, heading_style, normal_style):
        sections = [
            {
                "title": "Article 1 – Objet du contrat",
                "content": [
                    "Le présent contrat a pour objet de garantir l'assuré contre les conséquences financières d'un événement médical, accidentel ou exceptionnel survenant au cours d'un voyage à l'étranger ainsi que de lui apporter une assistance en cas de difficulté.",
                    "Les prestations sont délivrées selon la formule souscrite et mentionnée aux Conditions Particulières."
                ],
            },
            {
                "title": "Article 2 – Définitions",
                "bullets": [
                    "Assureur : société d'assurance émettrice du contrat.",
                    "Assuré : personne physique bénéficiaire des garanties.",
                    "Voyage : déplacement temporaire hors du pays de résidence, à des fins touristiques, professionnelles ou d'études.",
                    "Maladie : altération soudaine et imprévisible de la santé, médicalement constatée.",
                    "Accident : atteinte corporelle non intentionnelle provenant d'une cause extérieure, soudaine et fortuite.",
                    "Sinistre : réalisation d'un événement couvert par le contrat.",
                    "Rapatriement : transport médicalisé ou non de l'assuré vers son pays de résidence.",
                    "Franchise : somme restant à la charge de l'assuré pour chaque sinistre.",
                    "Assistance : aide matérielle, logistique ou médicale apportée par l'assureur."
                ],
            },
            {
                "title": "Article 3 – Prise d'effet et durée du contrat",
                "content": [
                    "Le contrat prend effet à la date et à l'heure indiquées aux Conditions Particulières, sous réserve du paiement intégral de la prime. Il cesse automatiquement dans les cas suivants :"
                ],
                "bullets": [
                    "À la date de fin de validité indiquée.",
                    "Dès le retour de l'assuré dans son pays de résidence si celui-ci intervient avant la date prévue."
                ],
            },
            {
                "title": "Article 4 – Étendue géographique de la garantie",
                "content": ["Les garanties s'appliquent :"],
                "bullets": [
                    "Dans la zone géographique précisée aux Conditions Particulières.",
                    "À l'exclusion du pays de résidence habituelle de l'assuré.",
                    "Avec exclusion des zones en guerre ou déconseillées par les autorités."
                ],
            },
            {
                "title": "Article 5 – Garanties principales",
                "bullets": [
                    "Frais médicaux et d'hospitalisation à l'étranger : remboursement ou prise en charge directe des dépenses suite à une maladie ou un accident, incluant consultations, analyses, médicaments, hospitalisation et actes chirurgicaux, dans la limite du plafond précisé aux Conditions Particulières.",
                    "Rapatriement sanitaire : organisation et prise en charge du transport médicalisé de l'assuré vers son pays de résidence lorsque l'état de santé l'exige.",
                    "Assistance en cas de décès : organisation du rapatriement du corps et prise en charge des frais administratifs et de transport.",
                    "Assistance médicale et logistique 24h/24 : orientation vers un professionnel de santé, suivi médical et informations pratiques en cas d'urgence.",
                    "Responsabilité civile à l'étranger : couverture des dommages corporels, matériels ou immatériels causés involontairement à des tiers.",
                    "Indemnité en cas d'accident corporel : versement d'un capital en cas de décès ou d'invalidité permanente résultant d'un accident durant le voyage.",
                    "Perte, vol ou retard de bagages (option) : indemnisation selon les montants prévus aux Conditions Particulières.",
                    "Annulation ou interruption de voyage (option) : remboursement des frais non récupérables pour motifs médicaux, administratifs ou décès d'un proche."
                ],
            },
            {
                "title": "Article 6 – Exclusions générales",
                "content": ["Ne sont jamais garantis :"],
                "bullets": [
                    "Les sinistres résultant d'un acte intentionnel ou dolosif de l'assuré, de la participation à une émeute, guerre ou terrorisme, de la pratique d'un sport à risque non couvert ou de l'usage de stupéfiants, alcool ou médicaments non prescrits.",
                    "Les maladies ou affections connues avant la souscription, chroniques, psychiques ou liées à la grossesse au-delà du sixième mois.",
                    "Les frais engagés sans accord préalable de l'assureur, ceux liés aux traitements esthétiques, de fertilité, prothèses ou cures thermales, ainsi que ceux issus d'un voyage entrepris dans un but médical."
                ],
            },
            {
                "title": "Article 7 – Obligations de l'assuré",
                "content": ["En cas de sinistre, l'assuré doit :"],
                "bullets": [
                    "Prévenir immédiatement la plateforme d'assistance indiquée sur la carte d'assurance.",
                    "Fournir toutes les informations nécessaires à l'évaluation du sinistre.",
                    "Transmettre les justificatifs médicaux et administratifs requis.",
                    "Ne pas engager de dépenses importantes sans accord préalable de l'assureur, sauf urgence vitale."
                ],
            },
            {
                "title": "Article 8 – Modalités d'indemnisation",
                "bullets": [
                    "Indemnisation dans la limite des plafonds prévus aux Conditions Particulières.",
                    "Remboursement en FCFA ou en euros sur présentation des pièces originales.",
                    "Possibilité pour l'assureur d'exiger un contrôle médical contradictoire avant règlement."
                ],
            },
            {
                "title": "Article 9 – Durée, renouvellement et résiliation",
                "content": ["Le contrat est établi pour la durée du voyage et n'est pas renouvelable tacitement sauf mention contraire."],
                "bullets": [
                    "Résiliation possible par l'assuré avant le départ, sous conditions.",
                    "Résiliation possible par l'assureur en cas de non-paiement de la prime ou de fraude constatée."
                ],
            },
            {
                "title": "Article 10 – Prescription",
                "content": [
                    "Conformément au Code des assurances, toute action dérivant du contrat est prescrite par deux ans à compter de l'événement donnant naissance à la réclamation."
                ],
            },
            {
                "title": "Article 11 – Loi applicable et juridiction compétente",
                "content": [
                    "Le contrat est régi par la législation du pays de souscription. Tout litige relève des tribunaux compétents du pays de l'assureur, sauf stipulation contraire."
                ],
            },
            {
                "title": "Article 12 – Données personnelles",
                "content": [
                    "Les informations recueillies servent uniquement à la gestion du contrat et au traitement des sinistres. L'assuré dispose d'un droit d'accès, de rectification et de suppression conformément à la législation en vigueur."
                ],
            },
            {
                "title": "Article 13 – Subrogation",
                "content": [
                    "Après indemnisation, l'assureur est subrogé dans les droits et actions de l'assuré contre tout tiers responsable du sinistre à concurrence des sommes versées."
                ],
            },
            {
                "title": "Article 14 – Clause de non-cumul",
                "content": [
                    "Lorsque plusieurs contrats couvrent le même risque, l'assuré doit en informer chaque assureur. La réparation ne peut excéder le montant total du dommage subi."
                ],
            },
            {
                "title": "Article 15 – Divers",
                "bullets": [
                    "La nullité d'une clause n'entraîne pas la nullité du contrat.",
                    "Toute modification du risque doit être immédiatement notifiée à l'assureur.",
                    "Les Conditions Particulières font partie intégrante du présent document."
                ],
            },
        ]
        PDFService._append_structured_section(
            story,
            "CONDITIONS GÉNÉRALES D’ASSURANCE VOYAGE (SANTÉ)",
            sections,
            heading_style,
            normal_style
        )

    @staticmethod
    def _append_conditions_particulieres(story, heading_style, normal_style, context: Optional[Dict[str, Any]] = None):
        c = context or {}
        sections = [
            {
                "title": "1. Identification du contrat",
                "bullets": [
                    f"Numéro du contrat : {c.get('num_contrat', 'N/A')}.",
                    f"Date de souscription : {c.get('date_souscription', 'N/A')}.",
                    f"Date de prise d'effet : {c.get('date_effet', 'N/A')} à 00h00.",
                    f"Date d'expiration : {c.get('date_expiration', 'N/A')} à minuit.",
                    f"Durée du voyage : {c.get('duree_voyage', 'N/A')}.",
                    f"Compagnie d'assurance : {c.get('compagnie_assurance', 'N/A')}.",
                    f"Siège social : {c.get('siege_social', 'N/A')}.",
                    f"Intermédiaire / Courtier : {c.get('intermediaire', 'N/A')}."
                ],
            },
            {
                "title": "2. Identification de l'assuré",
                "bullets": [
                    f"Nom et prénom : {c.get('nom_assure', 'N/A')}.",
                    f"Date et lieu de naissance : {c.get('date_et_lieu_naissance', 'N/A')}.",
                    f"Adresse permanente : {c.get('adresse_assure', 'N/A')}.",
                    f"Téléphone / Email : {c.get('coordonnees', 'N/A')}.",
                    f"Profession : {c.get('profession_assure', 'N/A')}.",
                    f"Nationalité : {c.get('nationalite_assure', 'N/A')}.",
                    f"Numéro de passeport : {c.get('numero_passeport', 'N/A')}.",
                    f"Date d'expiration du passeport : {c.get('date_expiration_passeport', 'N/A')}.",
                    f"Pays de destination : {c.get('pays_destination', 'N/A')}."
                ],
            },
            {
                "title": "3. Objet du contrat",
                "content": [
                    "Le contrat garantit l'assuré contre les conséquences financières d'événements médicaux ou sanitaires survenus à l'étranger pendant la période indiquée, conformément aux garanties ci-dessous."
                ],
            },
            {
                "title": "4. Garanties accordées",
                "table_flowable": _build_garanties_table_flowable(c.get("garanties_list", []), normal_style),
                "bullets": None if c.get("garanties_list") else [
                    f"Frais médicaux et d'hospitalisation : {c.get('frais_medicaux_montant', 'N/A')} – Franchise : {c.get('frais_medicaux_franchise', 'N/A')} – Inclut consultations, médicaments, analyses, imagerie.",
                    "Assistance médicale 24h/24 : Incluse – Sans franchise – Accès au plateau d'assistance.",
                    f"Rapatriement sanitaire : {c.get('rapatriement_montant', 'N/A')} – Sans franchise – Transport médicalisé et accompagnement.",
                    f"Assistance en cas de décès : {c.get('assistance_deces_montant', 'N/A')} – Sans franchise – Rapatriement du corps ou inhumation sur place.",
                    f"Responsabilité civile à l'étranger : {c.get('rc_montant', 'N/A')} – Franchise : {c.get('rc_franchise', 'N/A')} – Dommages causés à autrui.",
                    f"Indemnité en cas d'accident corporel : {c.get('accident_corporel_montant', 'N/A')} – Sans franchise – Décès ou invalidité permanente.",
                    f"Perte / retard de bagages (option) : {c.get('bagages_montant', 'N/A')} – Franchise : {c.get('bagages_franchise', 'N/A')} – Sur présentation de justificatifs.",
                    f"Annulation ou interruption de voyage (option) : {c.get('annulation_montant', 'N/A')} – Franchise : {c.get('annulation_franchise', 'N/A')} – Causes médicales, administratives ou décès."
                ],
            },
            {
                "title": "5. Étendue géographique",
                "bullets": [
                    f"Couverture pendant tout séjour hors du pays de résidence dans la zone suivante : {c.get('zone_couverture', 'N/A')}.",
                    "Exclusion des zones formellement déconseillées par les autorités diplomatiques."
                ],
            },
            {
                "title": "6. Conditions d'admission",
                "bullets": [
                    f"Être âgé de moins de {c.get('age_maximum', 'N/A')} ans à la souscription.",
                    "Disposer d'un état de santé stable et ne pas voyager dans un but médical.",
                    "Résider habituellement dans le pays de souscription."
                ],
            },
            {
                "title": "7. Montant et modalités de paiement de la prime",
                "bullets": [
                    f"Prime nette : {c.get('prime_nette', 'N/A')}.",
                    f"Taxes et frais : {c.get('taxes_frais', 'N/A')}.",
                    f"Total à payer : {c.get('total_payer', 'N/A')}.",
                    f"Mode de paiement : {c.get('mode_paiement', 'N/A')}.",
                    "Échéance : paiement unique avant le départ."
                ],
            },
            {
                "title": "8. Obligations de l'assuré",
                "bullets": [
                    "Informer l'assureur dès la survenance d'un sinistre avant toute initiative personnelle.",
                    "Fournir toutes les pièces justificatives nécessaires.",
                    "Respecter les instructions de la plateforme d'assistance pour les évacuations et hospitalisations.",
                    "Informer l'assureur de tout changement dans la durée ou le lieu du voyage."
                ],
            },
            {
                "title": "9. Exclusions principales",
                "bullets": [
                    "Maladies ou accidents survenus avant la prise d'effet du contrat.",
                    "Affections chroniques ou récidivantes connues avant le départ.",
                    "Conséquences d'un état d'ébriété, usage de stupéfiants ou tentative de suicide.",
                    "Sinistres liés à la guerre, insurrection, émeute ou acte de terrorisme.",
                    "Traitements esthétiques, de fertilité ou prothèses non urgentes.",
                    "Voyages entrepris malgré un avis médical défavorable."
                ],
            },
            {
                "title": "10. Références aux Conditions Générales",
                "content": [
                    "Les présentes Conditions Particulières complètent les Conditions Générales du contrat d'assurance voyage santé, que l'assuré reconnaît avoir reçues et acceptées."
                ],
            },
            {
                "title": "11. Déclarations de l'assuré",
                "bullets": [
                    "Communiquer des renseignements exacts et sincères.",
                    "Ne pas dissimuler d'information médicale ou administrative.",
                    "Reconnaître qu'une fausse déclaration peut entraîner la nullité du contrat ou la réduction des indemnités."
                ],
            },
        ]
        PDFService._append_structured_section(
            story,
            "CONDITIONS PARTICULIÈRES DU CONTRAT D’ASSURANCE VOYAGE (SANTÉ)",
            sections,
            heading_style,
            normal_style
        )

    @staticmethod
    def _append_police_assurance(story, heading_style, normal_style, context: Optional[Dict[str, Any]] = None):
        c = context or {}
        sections = [
            {
                "title": "1. Compagnie d'assurance",
                "bullets": [
                    f"Dénomination : {c.get('compagnie_assurance', 'IT-TECH ASSURANCE VOYAGE')}.",
                    f"Siège social : {c.get('siege_social', 'N/A')}.",
                    f"Téléphone : {c.get('assurance_telephone', 'N/A')}.",
                    f"E-mail : {c.get('assurance_email', 'N/A')}.",
                    f"Site web : {c.get('assurance_site', 'N/A')}."
                ],
            },
            {
                "title": "2. Identification de l'assuré",
                "bullets": [
                    f"Nom et prénom : {c.get('nom_assure', 'N/A')}.",
                    f"Date de naissance : {c.get('date_naissance', c.get('date_effet', 'N/A'))}.",
                    f"Numéro de passeport : {c.get('numero_passeport', 'N/A')}.",
                    f"Date d'expiration du passeport : {c.get('date_expiration_passeport', 'N/A')}.",
                    f"Nationalité : {c.get('nationalite_assure', 'N/A')}.",
                    f"Adresse permanente : {c.get('adresse_assure', 'N/A')}.",
                    f"Téléphone / E-mail : {c.get('coordonnees', 'N/A')}."
                ],
            },
            {
                "title": "3. Détails du voyage",
                "bullets": [
                    f"Pays de destination : {c.get('pays_destination', 'N/A')}.",
                    f"Motif du voyage : {c.get('motif_voyage', 'Voyage')}.",
                    f"Date de départ : {c.get('date_depart', 'N/A')}.",
                    f"Date de retour : {c.get('date_retour', 'N/A')}.",
                    f"Durée totale : {c.get('duree_voyage', 'N/A')}.",
                    f"Zone de couverture : {c.get('zone_couverture', 'N/A')}."
                ],
            },
            {
                "title": "4. Garanties accordées",
                "table_flowable": _build_garanties_table_flowable(c.get("garanties_list", []), normal_style),
                "bullets": None if c.get("garanties_list") else [
                    f"Frais médicaux et d'hospitalisation à l'étranger : {c.get('frais_medicaux_montant', 'N/A')} – franchise : {c.get('frais_medicaux_franchise', 'N/A')}.",
                    f"Rapatriement sanitaire : {c.get('rapatriement_montant', 'N/A')} – aucune franchise.",
                    "Assistance médicale 24h/24 : incluse – sans franchise.",
                    f"Assistance en cas de décès : {c.get('assistance_deces_montant', 'N/A')} – aucune franchise.",
                    f"Responsabilité civile à l'étranger : {c.get('rc_montant', 'N/A')} – franchise de {c.get('rc_franchise', 'N/A')}.",
                    f"Indemnité accident corporel (décès ou invalidité) : {c.get('accident_corporel_montant', 'N/A')} – sans franchise.",
                    f"Perte / vol de bagages (option) : {c.get('bagages_montant', 'N/A')} – franchise de {c.get('bagages_franchise', 'N/A')}.",
                    f"Annulation / interruption de voyage (option) : {c.get('annulation_montant', 'N/A')} – franchise de {c.get('annulation_franchise', 'N/A')}."
                ],
            },
            {
                "title": "5. Dispositions particulières",
                "bullets": [
                    "Le contrat est valable exclusivement pendant la période indiquée.",
                    "Il ne couvre pas les soins reçus dans le pays de résidence habituelle.",
                    f"En cas de sinistre, l'assuré contacte immédiatement la plateforme d'assistance (Assistance 24h/24 : {c.get('assurance_telephone', 'N/A')} ou {c.get('assurance_email', 'N/A')})."
                ],
            },
            {
                "title": "6. Exclusions principales",
                "bullets": [
                    "Maladies existantes avant le départ.",
                    "Affections chroniques, psychiques ou liées à la grossesse après le sixième mois.",
                    "Accidents résultant d'actes de guerre, émeutes, terrorisme ou radiation.",
                    "Blessures dues à la consommation d'alcool, de drogues ou à une participation sportive non déclarée.",
                    "Soins esthétiques, dentaires non urgents et prothèses."
                ],
            },
            {
                "title": "7. Durée, effet et expiration",
                "bullets": [
                    "Prise d'effet à 00h00 (heure locale) à la date de départ indiquée.",
                    "Expiration automatique à minuit (heure locale) à la date de retour prévue.",
                    "Toute prolongation nécessite une demande écrite préalable."
                ],
            },
            {
                "title": "8. Loi applicable et juridiction",
                "content": [
                    "Le contrat est régi par la législation de la République du Congo et tout litige relève des tribunaux du siège de la compagnie."
                ],
            },
            {
                "title": "9. Déclaration de l'assuré",
                "bullets": [
                    "Reconnaît avoir lu et compris les Conditions Générales et Particulières.",
                    "Certifie avoir déclaré des informations exactes et sincères.",
                    "Confirme avoir reçu un exemplaire signé de la présente police."
                ],
            },
            {
                "title": "10. Signatures et pièces jointes",
                "bullets": [
                    f"Fait à {c.get('assurance_ville', 'N/A')}, le {c.get('date_emission', 'N/A')} – signé par le représentant de l'assureur et l'assuré.",
                    "Pièces jointes : Conditions générales, Conditions particulières, Attestation d'assurance à présenter aux autorités."
                ],
            },
        ]
        PDFService._append_structured_section(
            story,
            "POLICE D’ASSURANCE VOYAGE (SANTÉ ET ASSISTANCE)",
            sections,
            heading_style,
            normal_style
        )

    @staticmethod
    def _append_structured_section(story, title, sections, heading_style, normal_style):
        story.append(PageBreak())
        story.append(Paragraph(title, heading_style))
        story.append(Spacer(1, 0.3*cm))
        article_style = ParagraphStyle(
            'AppendixHeading',
            parent=normal_style,
            fontSize=12,
            textColor=colors.HexColor('#111827'),
            spaceBefore=10,
            spaceAfter=4,
            leading=14,
            fontName='Helvetica-Bold'
        )
        for section in sections:
            story.append(Paragraph(section["title"], article_style))
            for content in section.get("content", []):
                story.append(Paragraph(content, normal_style))
            table_flowable = section.get("table_flowable")
            if table_flowable is not None:
                story.append(table_flowable)
                story.append(Spacer(1, 0.2*cm))
            bullets = section.get("bullets")
            if bullets:
                story.append(PDFService._build_list_flowable(bullets, normal_style))
            story.append(Spacer(1, 0.2*cm))

    @staticmethod
    def _build_list_flowable(items, normal_style):
        list_items = [ListItem(Paragraph(item, normal_style)) for item in items]
        return ListFlowable(
            list_items,
            bulletType='bullet',
            leftIndent=1*cm
        )

