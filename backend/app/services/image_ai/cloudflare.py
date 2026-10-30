"""Cloudflare Workers AI (free tier): FLUX.2 [klein] 4B image editing.

The room photo and the prompt go in; a redesigned picture comes out. Credentials stay on the server.
Docs: https://developers.cloudflare.com/workers-ai/models/flux-2-klein-4b/

Cost: about 5 neurons per input image and about 26 per 512x512 output tile, against the free
10,000 neurons a day, so a 768px result costs well under 100 neurons.
"""

import base64
import io
import logging

import httpx
from PIL import Image

from app.core.config import settings
from app.services.image_ai.base import ImageProvider, ImageProviderError

log = logging.getLogger(__name__)

MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
INPUT_MAX = 480  # the model needs each input image to be smaller than 512x512
OUTPUT_MAX = 768  # longest side of the redesigned picture (the model allows 256-1920)

EDIT_INSTRUCTION = (
    "Redesign the interior shown in the input photo. {prompt}. "
    "Keep the same room layout, walls, windows and camera perspective."
)


def prepare(image: bytes) -> tuple[bytes, int, int]:
    """The photo shrunk to what the model accepts (as PNG), plus the output size to ask for."""
    with Image.open(io.BytesIO(image)) as source:
        photo = source.convert("RGB")
    photo.thumbnail((INPUT_MAX, INPUT_MAX))
    out = io.BytesIO()
    photo.save(out, "PNG")

    scale = OUTPUT_MAX / max(photo.size)
    width, height = (max(256, round(side * scale / 16) * 16) for side in photo.size)  # multiples of 16
    return out.getvalue(), width, height


def error_summary(response: httpx.Response) -> str:
    """Cloudflare's own error codes and messages, e.g. '10000: Authentication error'."""
    try:
        errors = response.json().get("errors") or []
        return "; ".join(f"{e.get('code')}: {e.get('message')}" for e in errors) or response.text[:200]
    except ValueError:
        return response.text[:200]


def picture_from(response: httpx.Response) -> bytes:
    """The answer is either the raw image or JSON holding it as base64."""
    if response.headers.get("content-type", "").startswith("image/"):
        return response.content
    try:
        data = response.json()["result"]["image"]
        return base64.b64decode(data.split(",", 1)[-1])  # tolerate a data:image/png;base64, prefix
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ImageProviderError("The image service returned an unexpected answer.") from None


class CloudflareProvider(ImageProvider):
    name = "cloudflare"

    def edit(self, image: bytes, prompt: str, strength: float) -> bytes:
        # `strength` belongs to the older image-to-image models; this model has no such setting.
        url = f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}/ai/run/{MODEL}"
        photo, width, height = prepare(image)
        instruction = EDIT_INSTRUCTION.format(prompt=prompt.strip().rstrip("."))
        try:
            response = httpx.post(
                url,
                data={"prompt": instruction, "width": width, "height": height},
                files={"input_image_0": ("room.png", photo, "image/png")},
                headers={"Authorization": f"Bearer {settings.cf_api_token}"},
                timeout=90,
            )
        except httpx.HTTPError:
            raise ImageProviderError("The image service could not be reached. Please try again.") from None

        if response.status_code >= 400:
            # Cloudflare explains itself in the body (no secrets in it): keep it in the server log.
            log.warning(
                "Cloudflare Workers AI answered %s: %s", response.status_code, error_summary(response)
            )
        if response.status_code == 429:
            raise ImageProviderError("The image service is busy right now. Please try again in a minute.")
        if response.status_code in (401, 403):
            raise ImageProviderError(
                "The image service refused our credentials. "
                "The administrator needs to check the Workers AI token and model access."
            )
        if response.status_code >= 400:
            raise ImageProviderError(
                f"The image service could not create this design (error {response.status_code})."
            )
        return picture_from(response)
