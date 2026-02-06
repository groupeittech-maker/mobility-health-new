from io import BytesIO
from typing import Optional

import qrcode


class QRCodeService:
    """Service utilitaire pour générer des QR codes."""

    @staticmethod
    def generate_qr_image(
        data: str,
        box_size: int = 10,
        border: int = 4,
        fill_color: str = "black",
        back_color: str = "white"
    ) -> BytesIO:
        """
        Génère une image PNG contenant le QR code représentant `data`.

        Args:
            data: Le contenu encodé dans le QR code.
            box_size: Taille de chaque carré du QR code.
            border: Taille de la bordure autour du QR code.
            fill_color: Couleur des modules.
            back_color: Couleur d'arrière-plan.

        Returns:
            BytesIO positionné au début contenant l'image PNG.
        """
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

















