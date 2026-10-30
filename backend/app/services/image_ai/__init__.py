"""Image redesign providers. Pick one with IMAGE_PROVIDER = auto | cloudflare | mock."""

from app.core.config import settings
from app.services.image_ai.base import ImageProvider, ImageProviderError
from app.services.image_ai.cloudflare import CloudflareProvider
from app.services.image_ai.mock import MockProvider

__all__ = ["ImageProvider", "ImageProviderError", "get_provider"]


def get_provider() -> ImageProvider:
    choice = settings.image_provider
    has_cloudflare = bool(settings.cf_account_id and settings.cf_api_token)
    if choice == "cloudflare" or (choice == "auto" and has_cloudflare):
        if not has_cloudflare:
            raise ImageProviderError("The image service is not configured.")
        return CloudflareProvider()
    return MockProvider()
