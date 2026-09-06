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
    CARD_BACKGROUND_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend-simple",
        "assets",
        "card-background.jpg",
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
        """Génère la carte digitale MHC (fond violet, badge formule, n° assuré)."""
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

        card = cls._create_card_background()
        draw = ImageDraw.Draw(card)
        font_badge = cls._font(28, bold=True)
        font_name = cls._font(40, bold=True)
        font_label = cls._font(16, bold=True)
        font_number = cls._font(34, bold=True)
        font_value = cls._font(26, bold=True)
        font_tagline = cls._font(14)

        plan = cls._plan_label(souscription)
        badge_x, badge_y = 40, 38
        badge_pad_x, badge_pad_y = 22, 10
        badge_box = draw.textbbox((0, 0), plan, font=font_badge)
        badge_w = (badge_box[2] - badge_box[0]) + badge_pad_x * 2
        badge_h = (badge_box[3] - badge_box[1]) + badge_pad_y * 2
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            radius=6,
            fill=cls.TEAL_ACCENT,
        )
        draw.text((badge_x + badge_pad_x, badge_y + badge_pad_y - 2), plan, font=font_badge, fill=(255, 255, 255))

        mobility_logo = cls._load_mobility_logo()
        if mobility_logo:
            max_w, max_h = 220, 78
            w, h = mobility_logo.size
            if w > max_w or h > max_h:
                ratio = min(max_w / w, max_h / h)
                mobility_logo = mobility_logo.resize((int(w * ratio), int(h * ratio)), RESAMPLE_METHOD)
            logo_x = cls.WIDTH - mobility_logo.width - 40
            card.paste(
                mobility_logo,
                (logo_x, 32),
                mobility_logo if mobility_logo.mode == "RGBA" else None,
            )
            draw = ImageDraw.Draw(card)
        else:
            draw.text((cls.WIDTH - 280, 36), "MOBILITY HealthCare", font=font_value, fill=(255, 255, 255))
            draw.text((cls.WIDTH - 280, 72), "Travel safe, Live free.", font=font_tagline, fill=(210, 210, 230))

        full_name = ""
        if traveler_info:
            full_name = traveler_info.get("fullName", "") or ""
            if not full_name:
                prenoms_part = traveler_info.get("prenoms") or traveler_info.get("firstName") or ""
                nom_part = traveler_info.get("nom") or traveler_info.get("lastName") or ""
                full_name = f"{prenoms_part} {nom_part}".strip()
        if not full_name:
            full_name = getattr(user, "full_name", None) or getattr(user, "username", "") or "—"

        photo_w, photo_h = 230, 230
        photo = cls._prepare_photo(photo_bytes, target_size=(photo_w, photo_h))
        photo_x = cls.WIDTH - photo_w - 70
        photo_y = 148
        draw.rectangle(
            [photo_x - 6, photo_y - 6, photo_x + photo_w + 6, photo_y + photo_h + 6],
            fill=(255, 255, 255),
        )
        card.paste(photo, (photo_x, photo_y))
        draw = ImageDraw.Draw(card)

        text_max = photo_x - 80
        name_text = cls._truncate_text(full_name, font_name, max_width=text_max)
        draw.text((48, 150), name_text, font=font_name, fill=(255, 255, 255))

        insured_number = cls._format_insured_number(numero_attestation, souscription)
        draw.text((48, 230), "NUMÉRO ASSURÉ", font=font_label, fill=(196, 198, 220))
        draw.text((48, 256), insured_number, font=font_number, fill=(255, 255, 255))

        start_date = cls._format_date(getattr(souscription, "date_debut", None))
        end_date = cls._format_date(getattr(souscription, "date_fin", None))
        draw.text((48, 350), "VALIDITÉ", font=font_label, fill=(196, 198, 220))
        draw.text((48, 380), f"Du  {start_date}", font=font_value, fill=(255, 255, 255))
        draw.text((48, 418), f"Au  {end_date}", font=font_value, fill=(255, 255, 255))

        adults, children = cls.resolve_ayants_droit(souscription, traveler_info)
        group_label = cls.format_ayants_droit_label(adults, children)
        icon_size = 32
        label_box = draw.textbbox((0, 0), group_label, font=font_value)
        label_w = label_box[2] - label_box[0]
        group_w = icon_size + 12 + label_w
        icon_x = photo_x + max(0, (photo_w - group_w) // 2)
        icon_y = photo_y + photo_h + 18
        cls._draw_group_icon(draw, icon_x, icon_y, size=icon_size, fill=(255, 255, 255))
        draw.text((icon_x + icon_size + 12, icon_y + 2), group_label, font=font_value, fill=(255, 255, 255))

        card = cls._add_rounded_corners(card, radius=28)
        buffer = BytesIO()
        card.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer

    @staticmethod
    def format_ayants_droit_label(adults: int, children: int) -> str:
        """Affiche « 1 - 03 » : 1 adulte et 3 enfants ayant droit."""
        adults = max(1, int(adults or 1))
        children = max(0, int(children or 0))
        return f"{adults} - {children:02d}"

    @classmethod
    def resolve_ayants_droit(cls, souscription, traveler_info: Optional[Dict[str, Any]] = None) -> tuple:
        """Retourne (nb_adultes, nb_enfants) à partir du voyage / des notes."""
        info = traveler_info or {}
        adults = cls._optional_int(
            info.get("adultsCount") or info.get("nb_adultes") or info.get("nombre_adultes")
        )
        children = cls._optional_int(
            info.get("childrenCount") or info.get("nb_enfants") or info.get("nombre_enfants")
        )
        notes = "\n".join(
            part
            for part in (
                getattr(souscription, "notes", None),
                getattr(getattr(souscription, "projet_voyage", None), "notes", None),
            )
            if part
        )
        parsed_children = cls.count_children_from_notes(notes)
        if children is None:
            children = parsed_children
        elif parsed_children:
            children = max(children, parsed_children)

        projet = getattr(souscription, "projet_voyage", None)
        participants = cls._optional_int(getattr(projet, "nombre_participants", None)) if projet else None
        if not children and participants and participants > 1 and cls._notes_mention_minors(notes):
            children = max(0, participants - (adults or 1))

        if not children:
            import re
            label = str(info.get("groupLabel") or info.get("group_label") or "")
            match = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", label)
            if match:
                adults = adults or int(match.group(1))
                children = int(match.group(2))

        return (adults or 1), (children or 0)

    @staticmethod
    def _optional_int(value) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _notes_mention_minors(notes: str) -> bool:
        import re
        return bool(re.search(r"mineur|minors|enfant", notes or "", re.IGNORECASE))

    @staticmethod
    def count_children_from_notes(notes: Optional[str]) -> int:
        """Compte les enfants ayant droit dans les notes projet / souscription."""
        import re
        if not notes:
            return 0
        match = re.search(r"Nombre d['’]enfants mineurs\s*:\s*(\d+)", notes, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"Minors count\s*:\s*(\d+)", notes, re.IGNORECASE)
        if match:
            return int(match.group(1))
        enfants = re.findall(r"^\s*Enfant\s+\d+\s*:", notes, re.IGNORECASE | re.MULTILINE)
        if enfants:
            return len(enfants)
        match = re.search(r"Mineurs accompagnés\s*:\s*(.+)$", notes, re.IGNORECASE | re.MULTILINE)
        if match:
            born = re.findall(r"né\(e\)\s+le", match.group(1), re.IGNORECASE)
            if born:
                return len(born)
            parts = [part.strip() for part in match.group(1).split(";") if part.strip() and "passeport" not in part.lower() and "validité" not in part.lower()]
            return len(parts)
        return 0

    @staticmethod
    def _draw_group_icon(draw: ImageDraw.Draw, x: int, y: int, size: int = 32, fill=(255, 255, 255)) -> None:
        """Icône « groupe » (3 silhouettes) sous la photo."""
        head = max(4, size // 6)
        body_h = size - head - 4

        def person(cx: int, cy: int, scale: float = 1.0) -> None:
            r = int(head * scale)
            draw.ellipse([cx - r, cy, cx + r, cy + 2 * r], fill=fill)
            top = cy + 2 * r + 1
            draw.ellipse(
                [cx - int(r * 1.7), top, cx + int(r * 1.7), top + int(body_h * scale)],
                fill=fill,
            )

        person(x + int(size * 0.22), y + 4, 0.78)
        person(x + int(size * 0.78), y + 4, 0.78)
        person(x + int(size * 0.50), y, 1.0)

    @staticmethod
    def _plan_label(souscription) -> str:
        produit = getattr(souscription, "produit_assurance", None)
        nom = str(getattr(produit, "nom", "") or getattr(produit, "code", "") or "").upper()
        for token in ("PREMIUM", "GOLD", "PLATINUM", "VIP", "PLUS", "STANDARD"):
            if token in nom:
                return token
        return "STANDARD"

    @staticmethod
    def _format_insured_number(numero_attestation: str, souscription) -> str:
        digits = "".join(ch for ch in str(numero_attestation or "") if ch.isdigit())
        extra = "".join(ch for ch in str(getattr(souscription, "numero_souscription", "") or "") if ch.isdigit())
        packed = (digits + extra + "0000000000000000")[:16]
        return " ".join(packed[i : i + 4] for i in range(0, 16, 4))

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
                    if path.endswith(("logo_officiel_mh.png", "logo_mobility_healthcare_officiel.png")):
                        logo = cls._knockout_near_black_background(logo)
                    log.info("Logo Mobility e-carte chargé: %s", path)
                    cls._MOBILITY_LOGO_CACHE = logo
                    return logo.copy()
            except Exception as e:
                log.debug("Logo Mobility ignoré (%s): %s", path, e)
        return None

    @classmethod
    def _create_card_background(cls) -> Image.Image:
        """Fond maquette officiel (card-background.jpg) redimensionné à la taille e-carte."""
        width, height = cls.WIDTH, cls.HEIGHT
        if os.path.isfile(cls.CARD_BACKGROUND_PATH):
            try:
                with Image.open(cls.CARD_BACKGROUND_PATH) as source:
                    return ImageOps.fit(source.convert("RGB"), (width, height), method=RESAMPLE_METHOD)
            except Exception:
                pass
        return cls._create_card_background_fallback()

    @classmethod
    def _create_card_background_fallback(cls) -> Image.Image:
        """Secours si l'asset JPG est absent (tests CI, déploiement partiel)."""
        import math

        width, height = cls.WIDTH, cls.HEIGHT
        card = Image.new("RGB", (width, height), (12, 8, 28))
        pixels = card.load()
        left = cls._hex_to_rgb(cls.PURPLE_BRAND)
        mid = (32, 14, 62)
        right = (8, 6, 22)
        for x in range(width):
            t = x / max(width - 1, 1)
            if t < 0.45:
                u = t / 0.45
                r = int(left[0] + (mid[0] - left[0]) * u)
                g = int(left[1] + (mid[1] - left[1]) * u)
                b = int(left[2] + (mid[2] - left[2]) * u)
            else:
                u = (t - 0.45) / 0.55
                r = int(mid[0] + (right[0] - mid[0]) * u)
                g = int(mid[1] + (right[1] - mid[1]) * u)
                b = int(mid[2] + (right[2] - mid[2]) * u)
            for y in range(height):
                v = 1 - (y / height) * 0.10
                pixels[x, y] = (max(0, int(r * v)), max(0, int(g * v)), max(0, int(b * v)))

        overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cls._draw_dotted_globe(draw, width, height)
        return Image.alpha_composite(card.convert("RGBA"), overlay).convert("RGB")

    @staticmethod
    def _draw_dotted_globe(draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Pointillés en projection orthographique : méridiens/parallèles d'un globe."""
        import math

        cx = int(width * 0.82)
        cy = int(height * 0.50)
        radius = int(height * 0.70)
        lon0 = math.radians(12)
        tilt = math.radians(18)
        ink = (198, 220, 238)

        def to_xyz(lat: float, lon: float):
            x = math.cos(lat) * math.sin(lon - lon0)
            y = math.sin(lat)
            z = math.cos(lat) * math.cos(lon - lon0)
            y2 = y * math.cos(tilt) - z * math.sin(tilt)
            z2 = y * math.sin(tilt) + z * math.cos(tilt)
            return x, y2, z2

        def project(lat: float, lon: float):
            x, y, z = to_xyz(lat, lon)
            if z <= 0.04:
                return None
            return int(cx + radius * x), int(cy - radius * y), z

        def stamp(x: int, y: int, depth: float, size: int = 2) -> None:
            alpha = int(48 + 175 * max(0.0, min(1.0, depth ** 0.85)))
            draw.ellipse((x, y, x + size, y + size), fill=(*ink, alpha))

        def dotted_curve(samples, min_gap: int = 8, size: int = 2) -> None:
            last = None
            for lat, lon in samples:
                point = project(lat, lon)
                if point is None:
                    last = None
                    continue
                px, py, depth = point
                if last is not None:
                    dx = px - last[0]
                    dy = py - last[1]
                    if dx * dx + dy * dy < min_gap * min_gap:
                        continue
                stamp(px, py, depth, size=size)
                last = (px, py)

        for lat_deg in range(-75, 76, 15):
            lat = math.radians(lat_deg)
            samples = [(lat, math.radians(lon)) for lon in range(-180, 181, 2)]
            dotted_curve(samples, min_gap=8, size=2)

        for lon_deg in range(-180, 180, 20):
            lon = math.radians(lon_deg)
            samples = [(math.radians(lat), lon) for lat in range(-90, 91, 2)]
            dotted_curve(samples, min_gap=8, size=2)

        equator = [(0.0, math.radians(lon)) for lon in range(-180, 181, 2)]
        dotted_curve(equator, min_gap=6, size=3)

        for angle in range(0, 360, 3):
            rad = math.radians(angle)
            facing = 0.28 + 0.72 * max(0.0, 0.55 + 0.45 * math.cos(rad - math.radians(20)))
            stamp(
                int(cx + radius * math.cos(rad)),
                int(cy - radius * math.sin(rad)),
                facing,
                size=2,
            )

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
    def _prepare_photo(photo_bytes: Optional[bytes], target_size: tuple = (230, 230)) -> Image.Image:
        """Prépare la photo de profil (photo réelle ou silhouette)."""
        import logging
        logger = logging.getLogger(__name__)

        if photo_bytes:
            try:
                photo = Image.open(BytesIO(photo_bytes)).convert("RGB")
                try:
                    photo = ImageOps.exif_transpose(photo)
                except Exception as ex:
                    logger.debug(f"exif_transpose ignoré: {ex}")
                return ImageOps.fit(photo, target_size, method=RESAMPLE_METHOD)
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la photo: {e}")

        return CardService._placeholder_portrait(target_size)

    @staticmethod
    def _placeholder_portrait(target_size: tuple) -> Image.Image:
        """Silhouette type e-carte lorsqu'aucune photo n'est encore disponible."""
        w, h = target_size
        image = Image.new("RGB", target_size, (198, 214, 230))
        draw = ImageDraw.Draw(image)
        fill = (236, 242, 248)
        head_r = int(min(w, h) * 0.15)
        cx, cy = w // 2, int(h * 0.34)
        draw.ellipse([cx - head_r, cy - head_r, cx + head_r, cy + head_r], fill=fill)
        shoulder_top = cy + head_r + 6
        draw.pieslice(
            [int(w * 0.16), shoulder_top, int(w * 0.84), h + int(h * 0.35)],
            start=180,
            end=360,
            fill=fill,
        )
        return image

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

