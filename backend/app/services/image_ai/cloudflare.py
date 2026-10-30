"""Cloudflare Workers AI (free tier): Stable Diffusion image-to-image.

The photo and the prompt go in; a new picture comes out. Credentials stay on the server.
Docs: https://developers.cloudflare.com/workers-ai/models/stable-diffusion-v1-5-img2img/
"""

import base64
import io

import httpx
from PIL import Image

from app.core.config import settings
from app.services.image_ai.base import ImageProvider, ImageProviderError

MODEL = "@cf/runwayml/stable-diffusion-v1-5-img2img"
MAX_SIDE = 512  # the model is trained at 512px; larger inputs are slower and cost more neurons


def prepare(image: bytes) -> bytes:
    """Resize to the model's working size (multiples of 8) and re-encode as PNG."""
    with Image.open(io.BytesIO(image)) as source:
        photo = source.convert("RGB")
    photo.thumbnail((MAX_SIDE, MAX_SIDE))
    width, height = (max(64, side - side % 8) for side in photo.size)
    out = io.BytesIO()
    photo.resize((width, height)).save(out, "PNG")
    return out.getvalue()


class CloudflareProvider(ImageProvider):
    name = "cloudflare"

    def edit(self, image: bytes, prompt: str, strength: float) -> bytes:
        url = f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}/ai/run/{MODEL}"
        body = {
            "prompt": prompt,
            "image_b64": base64.b64encode(prepare(image)).decode(),
            "strength": min(max(strength, 0.1), 1.0),
            "guidance": 7.5,
            "num_steps": 20,
        }
        try:
            response = httpx.post(
                url, json=body, headers={"Authorization": f"Bearer {settings.cf_api_token}"}, timeout=90
            )
        except httpx.HTTPError:
            raise ImageProviderError("The image service could not be reached. Please try again.") from None

        if response.status_code == 429:
            raise ImageProviderError("The image service is busy right now. Please try again in a minute.")
        if response.status_code >= 400:
            raise ImageProviderError(
                f"The image service could not create this design (error {response.status_code})."
            )

        if response.headers.get("content-type", "").startswith("image/"):
            return response.content
        try:  # some responses wrap the picture as base64 inside JSON
            return base64.b64decode(response.json()["result"]["image"])
        except (ValueError, KeyError, TypeError):
            raise ImageProviderError("The image service returned an unexpected answer.") from None
