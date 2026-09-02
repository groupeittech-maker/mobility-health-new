from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Any
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps

RESAMPLE_METHOD = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS

# Chemin vers le logo (relatif au répertoire du projet)
LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend-simple",
    "assets",
    "logo_officiel_mh.png",
)


class CardService:
    """Générateur de carte numérique à partir d'une attestation."""

    WIDTH = 1000
    HEIGHT = 600
    TEAL_BAND_HEIGHT = 110
    # Charte Mobility HealthCare (logo : violet #512D81 + teal #1DB09C)
    PURPLE_DARK = "#3d1e62"
    PURPLE_BRAND = "#4e267c"
    TEAL_ACCENT = "#14AE98"
    TEAL_BORDER = "#14AE98"
    TEXT_COLOR = "#FFFFFF"
    TEXT_ON_LIGHT_TITLE = "#4e267c"
    TEXT_ON_LIGHT_LABEL = "#14AE98"
    TEXT_ON_LIGHT_VALUE = "#1a1528"
    TEXT_ON_LIGHT_MUTED = "#5c5470"
    PLACEHOLDER_BG = "#eef1f6"  # Neutre clair si pas de photo (sur carte blanche)
    # Motifs filigrane fournis (copiés tels quels)
    PATTERN_PURPLE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend-simple",
        "assets",
        "card-pattern-purple.png",
    )
    PATTERN_TEAL_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend-simple",
        "assets",
        "card-pattern-teal.png",
    )

    # Chemins vers les logos
    NSIA_LOGO_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend-simple",
        "assets",
        "nsia-logo.png"
    )
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    MOBILITY_LOGO_CANDIDATES = [
        os.path.join(_ROOT, "frontend-simple", "assets", "logo_officiel_mh.png"),
        os.path.join(_ROOT, "mobile-app", "assets", "images", "logo_officiel_mh.png"),
        os.path.join(_ROOT, "frontend-simple", "assets", "logo_officiel_mh.jpg"),
        os.path.join(_ROOT, "mobile-app", "assets", "images", "logo_officiel_mh.jpg"),
    ]
    _MOBILITY_LOGO_CACHE: Optional[Image.Image] = None

    @classmethod
    def generate_insurance_card(
        cls,
        user,
        souscription,
        numero_attestation: str,
        verification_url: str,
        photo_bytes: Optional[bytes] = None,
        qr_bytes: Optional[bytes] = None,
        traveler_info: Optional[Dict[str, Any]] = None,
        *,
        allow_missing_photo: bool = False,
    ) -> BytesIO:
        """Génère une carte numérique (PNG) selon le modèle NSIA/Mobility Health."""
        if not allow_missing_photo:
            if not photo_bytes or len(photo_bytes) < 32:
                raise ValueError(
                    "La photo d'identité est obligatoire pour générer la e-carte."
                )
            try:
                with Image.open(BytesIO(photo_bytes)) as probe:
                    probe.verify()
            except Exception as e:
                raise ValueError(
                    "La photo fournie est illisible. Utilisez une image JPG ou PNG."
                ) from e

        # Fond structuré : en-tête blanc, bandeau principal violet, liseré bas teal.
        card = cls._create_card_background()
        draw = ImageDraw.Draw(card)
        
        # Charger les polices
        fonts = cls._load_fonts()

        # Taille max commune pour les deux logos (assureur = même taille que Mobility HealthCare)
        LOGO_MAX_WIDTH = 200
        LOGO_MAX_HEIGHT = 80

        # Logo MOBILITY HealthCare (en haut à gauche)
        mobility_logo = cls._load_mobility_logo()
        if mobility_logo:
            w, h = mobility_logo.width, mobility_logo.height
            if w > LOGO_MAX_WIDTH or h > LOGO_MAX_HEIGHT:
                ratio = min(LOGO_MAX_WIDTH / w, LOGO_MAX_HEIGHT / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                mobility_logo = mobility_logo.resize((new_w, new_h), RESAMPLE_METHOD)
            card.paste(mobility_logo, (40, 40), mobility_logo if mobility_logo.mode == "RGBA" else None)

        # Logo de l'assureur (en haut à droite) - même taille max que Mobility HealthCare
        assureur_logo = cls._load_assureur_logo(souscription)
        if assureur_logo:
            w, h = assureur_logo.width, assureur_logo.height
            if w > LOGO_MAX_WIDTH or h > LOGO_MAX_HEIGHT:
                ratio = min(LOGO_MAX_WIDTH / w, LOGO_MAX_HEIGHT / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                assureur_logo = assureur_logo.resize((new_w, new_h), RESAMPLE_METHOD)
            logo_x = cls.WIDTH - assureur_logo.width - 40
            card.paste(assureur_logo, (logo_x, 40), assureur_logo if assureur_logo.mode == "RGBA" else None)

        # Titre centré "CARTE D'ASSURANCE VOYAGE"
        title_text = "CARTE D'ASSURANCE VOYAGE"
        # Ajuste dynamiquement la taille du titre pour éviter toute coupe latérale.
        title_font = fonts["title"]
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        while title_width > cls.WIDTH - 60 and getattr(title_font, "size", 0) > 38:
            title_font = cls._font(size=title_font.size - 2, bold=True)
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
        title_x = (cls.WIDTH - title_width) // 2
        title_y = 140
        draw.text((title_x, title_y), title_text, font=title_font, fill=cls.TEXT_ON_LIGHT_VALUE)

        # Photo de profil (à gauche, sous le titre)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Photo bytes reçus: {len(photo_bytes) if photo_bytes else 0} bytes")
        photo = cls._prepare_photo(photo_bytes)
        photo_x = 70
        # Un peu plus haut pour laisser de la hauteur au bloc texte (maquette)
        photo_y = 258
        # Collage RGB sans masque (évite ambiguïtés PIL) ; ImageDraw recréé après modification bitmap
        if photo.mode == "RGBA":
            card.paste(photo, (photo_x, photo_y), photo)
        else:
            card.paste(photo, (photo_x, photo_y))
        draw = ImageDraw.Draw(card)
        # Cadre photo (teal charte MHC)
        draw.rectangle(
            [photo_x - 12, photo_y - 12, photo_x + photo.width + 12, photo_y + photo.height + 12],
            outline=(245, 245, 245),
            width=10,
        )

        # Informations à droite de la photo — prénom aligné sur le haut de l’image (pas le cadre)
        info_x = photo_x + photo.width + 58
        photo_frame_top = photo_y - 12  # bord supérieur du cadre blanc (QR / limites)
        photo_text_align_y = photo_y

        # Extraire les informations du voyageur/assuré
        # Priorité: traveler_info > user.full_name
        full_name = ""
        if traveler_info:
            # traveler_info peut contenir fullName ou prenoms/nom séparés
            full_name = traveler_info.get("fullName", "") or ""
            if not full_name:
                # Essayer de reconstruire depuis prenoms et nom
                prenoms_part = traveler_info.get("prenoms", "") or traveler_info.get("firstName", "") or ""
                nom_part = traveler_info.get("nom", "") or traveler_info.get("lastName", "") or ""
                if prenoms_part or nom_part:
                    full_name = f"{prenoms_part} {nom_part}".strip()
        
        # Si pas de fullName dans traveler_info, utiliser user
        if not full_name:
            full_name = getattr(user, "full_name", None) or getattr(user, "username", "") or ""
        
        # Séparer le nom complet en prénom et nom
        name_parts = full_name.strip().split(maxsplit=1) if full_name else []
        prenoms = name_parts[0] if len(name_parts) > 0 else ""
        nom = name_parts[1] if len(name_parts) > 1 else ""
        
        # Log pour debug
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Extraction nom/prénom - full_name: '{full_name}', prenoms: '{prenoms}', nom: '{nom}'")

        # N° DE POLICE : afficher le numéro de souscription (et non le numéro d'attestation)
        numero_police = getattr(souscription, "numero_souscription", "—")

        # Couleurs du bandeau violet
        label_on_purple = (245, 245, 245)
        value_on_purple = (255, 255, 255)
        teal_top = cls.HEIGHT - cls.TEAL_BAND_HEIGHT
        # Polices maquette : lisibles, compactes pour tenir dans le bandeau violet
        font_label = cls._font(24, bold=True)
        font_name = cls._font(36, bold=True)
        font_police = cls._font(28, bold=True)
        font_small = cls._font(21, bold=True)

        qr_size = 118
        qr_pad = 8
        qr_x = cls.WIDTH - qr_size - qr_pad - 58
        text_max = max(120, qr_x - info_x - 36)

        def _bbox_h(ft, txt: str) -> int:
            timg = Image.new("RGB", (1, 1))
            td = ImageDraw.Draw(timg)
            bb = td.textbbox((0, 0), txt, font=ft)
            return bb[3] - bb[1]

        # Espacements : pas de libellés Prénoms/Nom ; police remontée ; plus d’air avant validité
        GAP_NAMES = 22
        GAP_BEFORE_POLICE = 26

        y = float(photo_text_align_y)
        prenoms_text = cls._truncate_text(prenoms or "—", font_name, max_width=text_max)
        draw.text((info_x, int(y)), prenoms_text, font=font_name, fill=value_on_purple)
        y += _bbox_h(font_name, prenoms_text or "X") + GAP_NAMES
        nom_text = cls._truncate_text(nom or "—", font_name, max_width=text_max)
        draw.text((info_x, int(y)), nom_text, font=font_name, fill=value_on_purple)
        y += _bbox_h(font_name, nom_text or "X") + GAP_BEFORE_POLICE

        # N° de police
        draw.text((info_x, int(y)), "N° de police", font=font_label, fill=label_on_purple)
        y += _bbox_h(font_label, "N° de police") + 8
        police_text = (numero_police or "—").upper()
        police_bottom = cls._draw_text_full(
            draw,
            (info_x, int(y)),
            police_text,
            font_police,
            value_on_purple,
            max_width=text_max,
        )
        y = float(police_bottom) + 34.0

        # Date de validité (après le numéro)
        end_date = getattr(souscription, "date_fin", None)
        if end_date:
            if isinstance(end_date, str):
                date_str = end_date
            else:
                months_fr = ["jan", "fév", "mar", "avr", "mai", "jun",
                             "jul", "aoû", "sep", "oct", "nov", "déc"]
                date_str = f"{end_date.day} {months_fr[end_date.month - 1]} {end_date.year}"
        else:
            date_str = "—"

        validity_line_y = int(y)
        min_below_police = int(police_bottom) + 8
        if validity_line_y < min_below_police:
            validity_line_y = min_below_police
        approx_line = _bbox_h(font_small, "Ay")
        if validity_line_y + approx_line > teal_top - 6:
            validity_line_y = min(validity_line_y, teal_top - approx_line - 6)
        if validity_line_y < min_below_police:
            validity_line_y = min_below_police

        label_v = "Valable jusqu'au :"
        draw.text((info_x, validity_line_y), label_v, font=font_small, fill=label_on_purple)
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        lb = temp_draw.textbbox((0, 0), label_v, font=font_small)
        label_w = lb[2] - lb[0]
        draw.text((info_x + label_w + 8, validity_line_y), date_str, font=font_small, fill=value_on_purple)

        # Bas de la ligne « Valable jusqu'au » (alignement avec le bas du QR)
        tb_l = temp_draw.textbbox((0, 0), label_v, font=font_small)
        tb_d = temp_draw.textbbox((0, 0), date_str, font=font_small)
        validity_bottom = validity_line_y + max(tb_l[3] - tb_l[1], tb_d[3] - tb_d[1])

        # QR : bas du cartouche blanc = bas de la ligne de validité
        if qr_bytes:
            qr = Image.open(BytesIO(qr_bytes)).convert("RGB")
            qr_out = Image.new("RGBA", qr.size, (0, 0, 0, 0))
            qr_data = qr.load()
            qr_out_data = qr_out.load()
            dark = (26, 21, 40, 255)  # proche TEXT_ON_LIGHT_VALUE
            for py in range(qr.height):
                for px in range(qr.width):
                    r, g, b = qr_data[px, py]
                    if r < 128 and g < 128 and b < 128:
                        qr_out_data[px, py] = dark
                    else:
                        qr_out_data[px, py] = (0, 0, 0, 0)

            qr_out = qr_out.resize((qr_size, qr_size), RESAMPLE_METHOD)
            # Bas du cartouche blanc = bas de la ligne « Valable jusqu'au » (bord inférieur du rectangle)
            # rectangle : [..., qr_y - qr_pad, ..., qr_y + qr_size + qr_pad] → bas = qr_y + qr_size + qr_pad
            qr_y = int(validity_bottom - qr_size - qr_pad)
            top_min = photo_frame_top - qr_pad
            if qr_y < top_min:
                qr_y = top_min
            draw = ImageDraw.Draw(card)
            draw.rectangle(
                [qr_x - qr_pad, qr_y - qr_pad, qr_x + qr_size + qr_pad, qr_y + qr_size + qr_pad],
                fill=(255, 255, 255),
            )
            card.paste(qr_out, (qr_x, qr_y), qr_out)

        # Ajouter des coins arrondis à la carte
        card = cls._add_rounded_corners(card, radius=20)
        
        buffer = BytesIO()
        card.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _add_rounded_corners(image: Image.Image, radius: int = 20) -> Image.Image:
        """Ajoute des coins arrondis à l'image."""
        # Créer un masque avec des coins arrondis
        mask = Image.new("L", image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        width, height = image.size
        
        # Dessiner un rectangle arrondi blanc (masque)
        mask_draw.rounded_rectangle(
            [(0, 0), (width, height)],
            radius=radius,
            fill=255
        )
        
        # Appliquer le masque si l'image a un canal alpha, sinon créer une version RGBA
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Créer une nouvelle image avec transparence
        rounded = Image.new("RGBA", image.size, (0, 0, 0, 0))
        rounded.paste(image, (0, 0))
        rounded.putalpha(mask)
        
        # Reconvertir en RGB pour la compatibilité
        final = Image.new("RGB", rounded.size, (255, 255, 255))
        final.paste(rounded, mask=rounded.split()[3])  # Utiliser le canal alpha comme masque
        
        return final

    @staticmethod
    def _load_assureur_logo(souscription) -> Optional[Image.Image]:
        """Charge le logo de l'assureur depuis la souscription."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Récupérer l'assureur depuis le produit d'assurance
            produit = getattr(souscription, "produit_assurance", None)
            if not produit:
                logger.warning("Aucun produit d'assurance trouvé pour la souscription")
                # Essayer de charger depuis la DB si on a accès à la session
                try:
                    from app.core.database import SessionLocal
                    from app.models.produit_assurance import ProduitAssurance
                    db = SessionLocal()
                    try:
                        produit = db.query(ProduitAssurance).filter(
                            ProduitAssurance.id == souscription.produit_assurance_id
                        ).first()
                    finally:
                        db.close()
                except Exception as e:
                    logger.debug(f"Impossible de charger le produit depuis la DB: {e}")
                if not produit:
                    return None
            
            assureur = getattr(produit, "assureur_obj", None)
            if not assureur and hasattr(produit, "assureur_id") and produit.assureur_id:
                # Essayer de charger depuis la DB
                try:
                    from app.core.database import SessionLocal
                    from app.models.assureur import Assureur
                    db = SessionLocal()
                    try:
                        assureur = db.query(Assureur).filter(
                            Assureur.id == produit.assureur_id
                        ).first()
                    finally:
                        db.close()
                except Exception as e:
                    logger.debug(f"Impossible de charger l'assureur depuis la DB: {e}")
            
            if not assureur:
                logger.warning("Aucun assureur trouvé pour le produit d'assurance")
                return None
            
            logo_url = getattr(assureur, "logo_url", None)
            if not logo_url:
                logger.warning("Aucun logo_url trouvé pour l'assureur")
                return None
            
            logger.info(f"Chargement du logo de l'assureur depuis: {logo_url}")
            
            # Si c'est une URL Minio (contient le bucket et le chemin)
            if logo_url.startswith("http") or "/" in logo_url:
                # Essayer de télécharger depuis Minio si c'est un chemin Minio
                if not logo_url.startswith("http"):
                    # C'est probablement un chemin Minio (bucket/object)
                    from app.services.minio_service import MinioService
                    # Essayer de trouver le bucket (peut être dans différents buckets)
                    buckets_to_try = ["logos", "assureurs", "assets", MinioService.BUCKET_ATTESTATIONS]
                    for bucket in buckets_to_try:
                        try:
                            logo_bytes = MinioService.get_file(bucket, logo_url)
                            if logo_bytes:
                                logo = Image.open(BytesIO(logo_bytes))
                                if logo.mode != "RGBA":
                                    logo = logo.convert("RGBA")
                                logger.info(f"Logo chargé depuis Minio: {bucket}/{logo_url}")
                                return logo
                        except Exception as e:
                            logger.debug(f"Impossible de charger depuis {bucket}/{logo_url}: {e}")
                            continue
                
                # Si c'est une URL HTTP, essayer de télécharger
                if logo_url.startswith("http"):
                    try:
                        import httpx
                        with httpx.Client(timeout=5.0) as client:
                            response = client.get(logo_url)
                            if response.status_code == 200:
                                logo = Image.open(BytesIO(response.content))
                                if logo.mode != "RGBA":
                                    logo = logo.convert("RGBA")
                                logger.info(f"Logo chargé depuis URL: {logo_url}")
                                return logo
                    except Exception as e:
                        logger.warning(f"Impossible de télécharger le logo depuis {logo_url}: {e}")
            
            # Si c'est un chemin local
            if os.path.exists(logo_url):
                logo = Image.open(logo_url)
                if logo.mode != "RGBA":
                    logo = logo.convert("RGBA")
                logger.info(f"Logo chargé depuis fichier local: {logo_url}")
                return logo
            
            logger.warning(f"Impossible de charger le logo depuis: {logo_url}")
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du logo de l'assureur: {e}")
            return None

    @staticmethod
    def _knockout_near_black_background(logo: Image.Image, threshold: int = 42) -> Image.Image:
        """Rend le fond noir du logo officiel transparent (e-carte violette, lisibilité)."""
        if logo.mode != "RGBA":
            logo = logo.convert("RGBA")
        pixels = logo.load()
        w, h = logo.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if r <= threshold and g <= threshold and b <= threshold:
                    pixels[x, y] = (0, 0, 0, 0)
        return logo

    @classmethod
    def _load_mobility_logo(cls) -> Optional[Image.Image]:
        """Charge le logo officiel Mobility HealthCare (PNG) — cache en mémoire."""
        import logging

        if cls._MOBILITY_LOGO_CACHE is not None:
            return cls._MOBILITY_LOGO_CACHE.copy()
        log = logging.getLogger(__name__)
        for path in cls.MOBILITY_LOGO_CANDIDATES:
            try:
                if os.path.isfile(path):
                    logo = Image.open(path)
                    if logo.mode != "RGBA":
                        logo = logo.convert("RGBA")
                    if "logo_mobility_healthcare_officiel.png" in path:
                        logo = cls._knockout_near_black_background(logo)
                    log.info("Logo Mobility e-carte chargé: %s", path)
                    cls._MOBILITY_LOGO_CACHE = logo
                    return logo.copy()
            except Exception as e:
                log.debug("Logo Mobility ignoré (%s): %s", path, e)
        return None

    @classmethod
    def _create_card_background(cls) -> Image.Image:
        """Fond e-carte : en-tête blanc, bandeau violet principal, liseré teal en bas."""
        card = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(card)
        purple_rgb = cls._hex_to_rgb(cls.PURPLE_BRAND)
        teal_rgb = cls._hex_to_rgb(cls.TEAL_ACCENT)
        # Bandeau principal violet
        draw.rectangle((0, 230, cls.WIDTH, cls.HEIGHT), fill=purple_rgb)
        # Liseré bas teal
        draw.rectangle((0, cls.HEIGHT - cls.TEAL_BAND_HEIGHT, cls.WIDTH, cls.HEIGHT), fill=teal_rgb)
        # Fine séparation sous l'en-tête blanc
        draw.line((0, 230, cls.WIDTH, 230), fill=(82, 52, 128), width=2)
        teal_y0 = cls.HEIGHT - cls.TEAL_BAND_HEIGHT
        # Motifs fournis en PNG, répétés en diagonale par bande sans traverser la séparation.
        cls._tile_pattern_band_from_asset(card, 232, teal_y0, cls.PATTERN_PURPLE_PATH)
        cls._tile_pattern_band_from_asset(card, teal_y0, cls.HEIGHT, cls.PATTERN_TEAL_PATH)
        return card

    @classmethod
    def _tile_pattern_band_from_asset(
        cls,
        card: Image.Image,
        y_min: int,
        y_max: int,
        asset_path: str,
    ) -> None:
        """Colle un motif PNG fourni, répété en diagonale, limité à la bande [y_min, y_max)."""
        if y_max <= y_min + 6 or not asset_path or not os.path.isfile(asset_path):
            return
        try:
            motif = Image.open(asset_path).convert("RGBA")
        except Exception:
            return

        # Réduire la taille du motif pour en afficher plus.
        src_w, src_h = motif.size
        scale = 0.42
        mw = max(20, int(src_w * scale))
        mh = max(20, int(src_h * scale))
        motif = motif.resize((mw, mh), RESAMPLE_METHOD)
        if mw < 8 or mh < 8:
            return

        # Pas de coupe: on colle uniquement des motifs entièrement inclus dans la bande.
        step_x = mw + 30
        step_y = mh + 14
        y = y_min + 8
        row = 0
        while y + mh <= y_max - 4:
            x_shift = (row * (step_x // 2)) % step_x
            x = -mw + x_shift
            while x + mw <= cls.WIDTH + mw:
                if x >= 0 and x + mw <= cls.WIDTH:
                    card.paste(motif, (x, y), motif)
                x += step_x
            y += step_y
            row += 1

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        h = hex_color.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    @classmethod
    def _draw_logo_inspired_dot_pattern(cls, card: Image.Image) -> None:
        """Points discrets teal, violet, lavande et menthe (charte logo MHC), sur toute la carte."""
        w, h = card.size
        overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        palette = [
            (0x1D, 0xB0, 0x9C, 52),
            (0x51, 0x2D, 0x81, 48),
            (0x16, 0x8F, 0x7E, 38),
            (0x7B, 0x68, 0xB5, 32),
            (0x78, 0xD4, 0xC4, 30),
            (0x51, 0x2D, 0x81, 22),
            (0x1D, 0xB0, 0x9C, 24),
        ]
        step = 11
        for row in range(0, h, step):
            for col in range(0, w, step):
                n = (row // step * 17 + col // step * 13 + (row + col) // 40) % len(palette)
                fill_rgba = palette[n]
                jitter_x = (row // step % 3) - 1
                jitter_y = (col // step % 3) - 1
                cx = col + step // 2 + jitter_x
                cy = row + step // 2 + jitter_y
                dist = abs(cx - w // 2) + abs(cy - h // 2)
                base_r = 2 if (n % 2 == 0) else 1
                dot_r = base_r + (1 if dist % 120 < 28 else 0)
                draw.ellipse(
                    (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
                    fill=fill_rgba,
                )
        card_rgba = card.convert("RGBA")
        card_rgba = Image.alpha_composite(card_rgba, overlay)
        card.paste(card_rgba.convert("RGB"), (0, 0))

    @staticmethod
    def _draw_text_full(
        draw: ImageDraw.Draw,
        position: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill,
        max_width: int,
        line_height_ratio: float = 1.2,
    ) -> int:
        """Affiche le texte en entier : une ligne si possible, sinon plusieurs lignes (pas de troncature).
        Retourne la coordonnée Y juste sous la dernière ligne dessinée."""
        if not text:
            return int(position[1])
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        single_line_width = bbox[2] - bbox[0]
        x0, y0 = position[0], position[1]
        if single_line_width <= max_width:
            draw.text(position, text, font=font, fill=fill)
            return y0 + (bbox[3] - bbox[1])
        # Découper en lignes pour tenir dans max_width (couper aux espaces si possible)
        words = text.split()
        lines = []
        current = []
        current_width = 0
        space_bbox = temp_draw.textbbox((0, 0), " ", font=font)
        space_w = space_bbox[2] - space_bbox[0]
        for w in words:
            w_bbox = temp_draw.textbbox((0, 0), w, font=font)
            w_w = w_bbox[2] - w_bbox[0]
            if current and current_width + space_w + w_w > max_width:
                lines.append(" ".join(current))
                current = [w]
                current_width = w_w
            else:
                current.append(w)
                current_width = current_width + (space_w if current else 0) + w_w
        if current:
            lines.append(" ".join(current))
        bbox_h = temp_draw.textbbox((0, 0), "Ay", font=font)
        line_height = int((bbox_h[3] - bbox_h[1]) * line_height_ratio)
        x, y = position
        bottom = y
        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            lb_line = temp_draw.textbbox((0, 0), line, font=font)
            bottom = y + (lb_line[3] - lb_line[1])
            y += line_height
            if y > CardService.HEIGHT - 120:
                break
        return bottom

    @staticmethod
    def _truncate_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        """Tronque le texte si nécessaire pour éviter le débordement."""
        if not text:
            return ""
        
        # Créer une image temporaire pour mesurer le texte
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Vérifier si le texte dépasse la largeur maximale
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return text
        
        # Tronquer le texte et ajouter "..."
        ellipsis = "..."
        ellipsis_bbox = temp_draw.textbbox((0, 0), ellipsis, font=font)
        ellipsis_width = ellipsis_bbox[2] - ellipsis_bbox[0]
        available_width = max_width - ellipsis_width
        
        # Trouver la longueur maximale du texte qui tient
        truncated = text
        while len(truncated) > 0:
            bbox = temp_draw.textbbox((0, 0), truncated, font=font)
            if (bbox[2] - bbox[0]) <= available_width:
                break
            truncated = truncated[:-1]
        
        return truncated + ellipsis if truncated != text else text

    @staticmethod
    def _prepare_photo(photo_bytes: Optional[bytes]) -> Image.Image:
        """Prépare la photo de profil (utilise la photo réelle si disponible)."""
        import logging
        logger = logging.getLogger(__name__)
        target_size = (260, 300)
        
        if photo_bytes:
            try:
                logger.info(f"Traitement de la photo: {len(photo_bytes)} bytes")
                photo = Image.open(BytesIO(photo_bytes)).convert("RGB")
                # Corriger l'orientation selon les métadonnées EXIF (évite photo de travers)
                try:
                    photo = ImageOps.exif_transpose(photo)
                except Exception as ex:
                    logger.debug(f"exif_transpose ignoré: {ex}")
                logger.info(f"Photo ouverte: {photo.size[0]}x{photo.size[1]}")
                # Redimensionner en gardant le ratio et en centrant
                photo = ImageOps.fit(photo, target_size, method=RESAMPLE_METHOD)
                logger.info(f"Photo redimensionnée: {photo.size[0]}x{photo.size[1]}")
                return photo
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la photo: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Pas de photo : zone réservée unie (sans silhouette)
        return Image.new("RGB", target_size, CardService.PLACEHOLDER_BG)

    @staticmethod
    def _load_fonts():
        """Charge les polices nécessaires pour la carte."""
        return {
            "title": CardService._font(size=56, bold=True),
            "value": CardService._font(size=40, bold=True),
            "value_police": CardService._font(size=34, bold=True),
            "label": CardService._font(size=26, bold=True),
            "small": CardService._font(size=22, bold=True),
            "logo_bold": CardService._font(size=24, bold=True),
            "logo_regular": CardService._font(size=18),
            "logo_small": CardService._font(size=14),
        }

    @staticmethod
    def _font(size: int, bold: bool = False):
        candidates = []
        base_paths = [
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts",
            "/System/Library/Fonts",
            "C:/Windows/Fonts",
        ]
        font_names = ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf"]
        if bold:
            font_names = ["DejaVuSans-Bold.ttf", "Arialbd.ttf", "Arial Bold.ttf"]

        for base in base_paths:
            for name in font_names:
                candidates.append(os.path.join(base, name))

        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    continue

        return ImageFont.load_default()

    
    @staticmethod
    def _format_date(value: Optional[datetime]) -> str:
        """Formate une date pour l'affichage."""
        if not value:
            return "—"
        if isinstance(value, str):
            return value
        return value.strftime("%d/%m/%Y")

