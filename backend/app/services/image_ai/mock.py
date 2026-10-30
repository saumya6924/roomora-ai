"""Offline stand-in for a real image model, so the studio works in tests and demos without any API key.

It does not redesign the room: it tints the photo from the prompt and stamps a caption, so each
version is visibly different and the whole upload -> generate -> history flow can be exercised.
"""

import hashlib
import io
from colorsys import hsv_to_rgb

from PIL import Image, ImageDraw, ImageEnhance

from app.services.image_ai.base import ImageProvider

MAX_SIDE = 1024


class MockProvider(ImageProvider):
    name = "mock"

    def edit(self, image: bytes, prompt: str, strength: float) -> bytes:
        with Image.open(io.BytesIO(image)) as source:
            photo = source.convert("RGB")
        photo.thumbnail((MAX_SIDE, MAX_SIDE))

        hue = int(hashlib.sha256(prompt.encode()).hexdigest()[:4], 16) / 0xFFFF
        tint = tuple(int(c * 255) for c in hsv_to_rgb(hue, 0.45, 0.95))
        photo = Image.blend(photo, Image.new("RGB", photo.size, tint), min(max(strength, 0.1), 0.6) * 0.5)
        photo = ImageEnhance.Contrast(photo).enhance(1.08)

        draw = ImageDraw.Draw(photo)
        bar = max(22, photo.height // 14)
        draw.rectangle([0, photo.height - bar, photo.width, photo.height], fill=(63, 66, 50))
        draw.text(
            (10, photo.height - bar + bar // 4), f"Roomora AI preview · {prompt[:70]}", fill=(250, 248, 241)
        )

        out = io.BytesIO()
        photo.save(out, "PNG")
        return out.getvalue()
