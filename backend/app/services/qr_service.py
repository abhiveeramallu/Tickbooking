import base64
from io import BytesIO

import qrcode


def generate_qr_code_bytes(booking_reference: str) -> bytes:
    image = qrcode.make(booking_reference)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def to_data_url(image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

