import base64
import logging
from io import BytesIO

_logger = logging.getLogger(__name__)


class QrGenerator:
    @staticmethod
    def generate_base64(verification_link, box_size=6, border=2):
        if not verification_link:
            return None
        try:
            import qrcode
        except ImportError as exc:
            _logger.error("qrcode library is not installed: %s", exc)
            return None

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=box_size,
                border=border,
            )
            qr.add_data(verification_link)
            qr.make(fit=True)
            image = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        except Exception as exc:
            _logger.exception("Failed to generate QR code: %s", exc)
            return None
