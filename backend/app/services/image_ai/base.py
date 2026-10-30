class ImageProviderError(RuntimeError):
    """A problem with the image service that is safe to show to the user."""


class ImageProvider:
    name = "base"

    def edit(self, image: bytes, prompt: str, strength: float) -> bytes:
        """Return a redesigned version of `image` as PNG bytes."""
        raise NotImplementedError
