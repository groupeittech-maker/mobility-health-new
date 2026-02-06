from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Any
import os
import math

from PIL import Image, ImageDraw, ImageFont, ImageOps

RESAMPLE_METHOD = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS

# Chemin vers le logo (relatif au répertoire du projet)
LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend-simple",
    "assets",
    "logo_officiel_mh.jpg"
)


class CardService:
    """Générateur de carte numérique à partir d'une attestation."""

    WIDTH = 1000
    HEIGHT = 600
    # Couleurs du nouveau design (e-carte prototype)
    PURPLE_DARK = "#34135A"  # Violet foncé (gauche du dégradé)
    PURPLE_INDIGO = "#4a2070"  # Indigo/violet droit du dégradé
    PURPLE_LIGHT = "#7a2fa3"  # Violet clair/magenta
    TEAL_BORDER = "#08ada0"  # Ligne teal en bas de carte
    TEXT_COLOR = "#FFFFFF"  # Texte blanc
    PLACEHOLDER_BG = "#d3d3d3"  # Fond gris clair pour placeholder photo
    GOLD = "#FFD700"  # Or pour logo NSIA
    SILVER = "#C0C0C0"  # Argent pour logo NSIA
    
    # Chemins vers les logos
    NSIA_LOGO_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend-simple",
        "assets",
        "nsia-logo.png"
    )
    MOBILITY_LOGO_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend-simple",
        "assets",
        "mobility-logo.png"
    )
    AFRICA_MAP_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend-simple",
        "assets",
        "africa-map.png"
    )

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
    ) -> BytesIO:
        """Génère une carte numérique (PNG) selon le modèle NSIA/Mobility Health."""
        # Fond : dégradé violet + motifs (ondulations gauche, demi-teintes droite)
        card = cls._create_card_background()
        draw = ImageDraw.Draw(card)
        
        # Charger les polices
        fonts = cls._load_fonts()

        # Taille max commune pour les deux logos (assureur = même taille que Mobility HealthCare)
        LOGO_MAX_WIDTH = 200
        LOGO_MAX_HEIGHT = 80

        # Logo de l'assureur (en haut à gauche) - charger depuis l'assureur de la souscription
        assureur_logo = cls._load_assureur_logo(souscription)
        if assureur_logo:
            w, h = assureur_logo.width, assureur_logo.height
            if w > LOGO_MAX_WIDTH or h > LOGO_MAX_HEIGHT:
                ratio = min(LOGO_MAX_WIDTH / w, LOGO_MAX_HEIGHT / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                assureur_logo = assureur_logo.resize((new_w, new_h), RESAMPLE_METHOD)
            card.paste(assureur_logo, (40, 40), assureur_logo if assureur_logo.mode == "RGBA" else None)

        # Logo MOBILITY HealthCare (en haut à droite) - même taille max que l'assureur
        mobility_logo = cls._load_mobility_logo()
        if mobility_logo:
            w, h = mobility_logo.width, mobility_logo.height
            if w > LOGO_MAX_WIDTH or h > LOGO_MAX_HEIGHT:
                ratio = min(LOGO_MAX_WIDTH / w, LOGO_MAX_HEIGHT / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                mobility_logo = mobility_logo.resize((new_w, new_h), RESAMPLE_METHOD)
            logo_x = cls.WIDTH - mobility_logo.width - 40
            card.paste(mobility_logo, (logo_x, 40), mobility_logo if mobility_logo.mode == "RGBA" else None)

        # Titre centré "CARTE D'ASSURANCE VOYAGE"
        title_text = "CARTE D'ASSURANCE VOYAGE"
        title_bbox = draw.textbbox((0, 0), title_text, font=fonts["title"])
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (cls.WIDTH - title_width) // 2
        title_y = 120
        draw.text((title_x, title_y), title_text, font=fonts["title"], fill=cls.TEXT_COLOR)

        # Photo de profil (à gauche, sous le titre)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Photo bytes reçus: {len(photo_bytes) if photo_bytes else 0} bytes")
        photo = cls._prepare_photo(photo_bytes)
        photo_x = 60
        photo_y = title_y + 80
        card.paste(photo, (photo_x, photo_y), photo if photo.mode == "RGBA" else None)

        # Informations de l'assuré (à droite de la photo)
        info_x = photo_x + photo.width + 40
        info_y = photo_y + 20

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

        # PRENOMS - avec gestion du débordement
        draw.text((info_x, info_y), "PRENOMS", font=fonts["label"], fill=cls.TEXT_COLOR)
        prenoms_text = cls._truncate_text(prenoms.upper(), fonts["value"], max_width=cls.WIDTH - info_x - 200)
        draw.text((info_x, info_y + 35), prenoms_text, font=fonts["value"], fill=cls.TEXT_COLOR)

        # NOM - avec gestion du débordement
        draw.text((info_x, info_y + 90), "NOM", font=fonts["label"], fill=cls.TEXT_COLOR)
        nom_text = cls._truncate_text(nom.upper(), fonts["value"], max_width=cls.WIDTH - info_x - 200)
        draw.text((info_x, info_y + 125), nom_text, font=fonts["value"], fill=cls.TEXT_COLOR)

        # N° DE POLICE - affiché en entier (sans troncature)
        draw.text((info_x, info_y + 180), "N° DE POLICE", font=fonts["label"], fill=cls.TEXT_COLOR)
        police_text = (numero_police or "").upper()
        cls._draw_text_full(draw, (info_x, info_y + 215), police_text, fonts["value"], cls.TEXT_COLOR, max_width=cls.WIDTH - info_x - 200)

        # QR code (à droite) - blanc sur fond transparent pour visibilité sur fond violet
        if qr_bytes:
            qr = Image.open(BytesIO(qr_bytes)).convert("RGB")
            # Créer une version blanche du QR code
            qr_white = Image.new("RGBA", qr.size, (0, 0, 0, 0))
            qr_data = qr.load()
            qr_white_data = qr_white.load()
            for y in range(qr.height):
                for x in range(qr.width):
                    # Si le pixel est noir (module du QR), le rendre blanc
                    r, g, b = qr_data[x, y]
                    if r < 128 and g < 128 and b < 128:
                        qr_white_data[x, y] = (255, 255, 255, 255)  # Blanc opaque
                    else:
                        qr_white_data[x, y] = (0, 0, 0, 0)  # Transparent
            
            qr_white = qr_white.resize((180, 180), RESAMPLE_METHOD)
            qr_x = cls.WIDTH - qr_white.width - 60
            qr_y = photo_y + 20
            # Coller avec transparence
            card.paste(qr_white, (qr_x, qr_y), qr_white)

        # Date de validité (en bas à gauche)
        end_date = getattr(souscription, "date_fin", None)
        if end_date:
            if isinstance(end_date, str):
                date_str = end_date
            else:
                # Formater comme "22 déc 2025"
                months_fr = ["jan", "fév", "mar", "avr", "mai", "jun", 
                            "jul", "aoû", "sep", "oct", "nov", "déc"]
                date_str = f"{end_date.day} {months_fr[end_date.month - 1]} {end_date.year}"
        else:
            date_str = "—"

        validity_y = cls.HEIGHT - 80
        draw.text((60, validity_y), "Valable jusqu'au", font=fonts["small"], fill=cls.TEXT_COLOR)
        draw.text((60, validity_y + 30), date_str, font=fonts["small"], fill=cls.TEXT_COLOR)

        # Bordure teal en bas
        border_height = 8
        draw.rectangle(
            (0, cls.HEIGHT - border_height, cls.WIDTH, cls.HEIGHT),
            fill=cls.TEAL_BORDER
        )

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
    def _load_mobility_logo() -> Optional[Image.Image]:
        """Charge le logo Mobility Health depuis le fichier."""
        try:
            if os.path.exists(CardService.MOBILITY_LOGO_PATH):
                logo = Image.open(CardService.MOBILITY_LOGO_PATH)
                # Convertir en RGBA si nécessaire pour la transparence
                if logo.mode != "RGBA":
                    logo = logo.convert("RGBA")
                return logo
        except Exception as e:
            print(f"Erreur lors du chargement du logo Mobility: {e}")
        return None

    @classmethod
    def _create_card_background(cls) -> Image.Image:
        """Crée le fond de la e-carte : dégradé violet + ondulations gauche + demi-teintes droite (prototype MHC)."""
        card = Image.new("RGB", (cls.WIDTH, cls.HEIGHT), cls.PURPLE_DARK)
        cls._draw_gradient(card)
        cls._draw_wavy_pattern(card)
        cls._draw_halftone_pattern(card)
        return card

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        h = hex_color.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    @classmethod
    def _draw_gradient(cls, card: Image.Image) -> None:
        """Dégradé horizontal : violet foncé (gauche) vers indigo (droite)."""
        r1, g1, b1 = cls._hex_to_rgb(cls.PURPLE_DARK)
        r2, g2, b2 = cls._hex_to_rgb(cls.PURPLE_INDIGO)
        w, h = card.size
        draw = ImageDraw.Draw(card)
        for x in range(w):
            t = x / max(w - 1, 1)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            draw.line([(x, 0), (x, h)], fill=(r, g, b))

    @classmethod
    def _draw_wavy_pattern(cls, card: Image.Image) -> None:
        """Motif d'ondulations légères sur la moitié gauche (lignes courbes translucides)."""
        w, h = card.size
        left_half = w // 2
        overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # Violet foncé semi-transparent pour les vagues
        fill_rgba = (0x34, 0x13, 0x5A, 28)
        for wave in range(6):
            phase = wave * 0.8
            points = []
            for x in range(0, left_half + 20, 4):
                y = h // 2 + int(18 * math.sin(x / 35 + phase)) + int(12 * math.sin(x / 60 + phase * 1.3))
                if 0 <= y < h:
                    points.append((x, y))
            if len(points) >= 2:
                draw.line(points, fill=fill_rgba, width=2)
        card_rgba = card.convert("RGBA")
        card_rgba = Image.alpha_composite(card_rgba, overlay)
        card.paste(card_rgba.convert("RGB"), (0, 0))

    @classmethod
    def _draw_halftone_pattern(cls, card: Image.Image) -> None:
        """Motif demi-teintes (points) sur la moitié droite, densité variable."""
        w, h = card.size
        overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # Points violet foncé, opacité modérée
        fill_rgba = (0x2a, 0x0f, 0x4a, 90)
        mid_x = w // 2
        for row in range(0, h, 14):
            for col in range(mid_x, w, 14):
                # Rayon légèrement plus grand au centre-droit
                cx = mid_x + (w - mid_x) // 2
                dist = abs(col - cx) + abs(row - h // 2)
                r = 3 if dist < 150 else (2 if dist < 280 else 1)
                if r >= 1:
                    draw.ellipse(
                        (col - r, row - r, col + r, row + r),
                        fill=fill_rgba,
                    )
        card_rgba = card.convert("RGBA")
        card_rgba = Image.alpha_composite(card_rgba, overlay)
        card.paste(card_rgba.convert("RGB"), (0, 0))

    @staticmethod
    def _draw_africa_background(card: Image.Image) -> None:
        """Pose en arrière-plan une carte de l'Afrique (asset africa-map.png) en gardant la couleur violette."""
        if not os.path.exists(CardService.AFRICA_MAP_PATH):
            return
        try:
            map_img = Image.open(CardService.AFRICA_MAP_PATH).convert("RGBA")
            map_img = map_img.resize((CardService.WIDTH, CardService.HEIGHT), RESAMPLE_METHOD)
            r, g, b = 0x34, 0x13, 0x5A
            overlay = Image.new("RGBA", card.size, (r, g, b, 0))
            if len(map_img.split()) >= 4:
                alpha = map_img.split()[3]
            else:
                # Carte noir et blanc : utiliser la luminance (continent = zones sombres ou claires)
                gray = map_img.convert("L")
                alpha = gray.point(lambda x: 255 - x if x < 128 else x)
            alpha = alpha.point(lambda x: min(255, int(x * 0.25)))
            overlay.putalpha(alpha)
            card_rgba = card.convert("RGBA")
            card_rgba = Image.alpha_composite(card_rgba, overlay)
            card.paste(card_rgba.convert("RGB"), (0, 0))
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("Arrière-plan Afrique non appliqué: %s", e)

    @staticmethod
    def _draw_text_full(
        draw: ImageDraw.Draw,
        position: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: str,
        max_width: int,
        line_height_ratio: float = 1.2,
    ) -> None:
        """Affiche le texte en entier : une ligne si possible, sinon plusieurs lignes (pas de troncature)."""
        if not text:
            return
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        single_line_width = bbox[2] - bbox[0]
        if single_line_width <= max_width:
            draw.text(position, text, font=font, fill=fill)
            return
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
        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height
            if y > CardService.HEIGHT - 120:
                break

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
        target_size = (180, 220)
        
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

        # Créer un placeholder avec silhouette si pas de photo
        placeholder = Image.new("RGB", target_size, CardService.PLACEHOLDER_BG)
        ph_draw = ImageDraw.Draw(placeholder)
        
        # Dessiner une silhouette de personne (simplifiée)
        # Tête (cercle)
        head_center = (target_size[0] // 2, 50)
        head_radius = 35
        ph_draw.ellipse(
            [head_center[0] - head_radius, head_center[1] - head_radius,
             head_center[0] + head_radius, head_center[1] + head_radius],
            fill="#FFFFFF"
        )
        
        # Corps (rectangle arrondi pour le torse)
        body_top = head_center[1] + head_radius + 5
        body_width = 100
        body_height = 80
        body_x = (target_size[0] - body_width) // 2
        ph_draw.rounded_rectangle(
            [body_x, body_top, body_x + body_width, body_top + body_height],
            radius=10,
            fill="#FFFFFF"
        )
        
        # Col (petit rectangle pour la chemise/cravate)
        collar_width = 60
        collar_height = 15
        collar_x = (target_size[0] - collar_width) // 2
        ph_draw.rectangle(
            [collar_x, body_top, collar_x + collar_width, body_top + collar_height],
            fill="#FFFFFF"
        )
        
        return placeholder

    @staticmethod
    def _load_fonts():
        """Charge les polices nécessaires pour la carte."""
        return {
            "title": CardService._font(size=36, bold=True),
            "value": CardService._font(size=28, bold=True),
            "label": CardService._font(size=20, bold=True),
            "small": CardService._font(size=18),
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

