"""Image uploads for products and portfolios (public bucket)."""

import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.enums import Role
from app.core.ratelimit import upload_limit
from app.core.security import require_role
from app.core.storage import StorageError, get_storage
from app.models import User

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png"), "WEBP": ("image/webp", "webp")}


def read_image(upload: UploadFile) -> tuple[bytes, str, str]:
    """Read and validate an uploaded image. Returns (bytes, content type, extension)."""
    data = upload.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413, detail=f"Image is larger than {settings.max_upload_bytes // 1_000_000} MB"
        )
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            fmt = image.format or ""
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="That file is not a valid image") from None
    if fmt not in ALLOWED:
        raise HTTPException(status_code=400, detail="Only JPG, PNG or WebP images are allowed")
    content_type, ext = ALLOWED[fmt]
    return data, content_type, ext


@router.post("/image", dependencies=[Depends(upload_limit)])
def upload_image(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_role(Role.SELLER, Role.DESIGNER, Role.ADMIN)),
):
    data, content_type, ext = read_image(file)
    path = f"{user.id}/{uuid.uuid4().hex}.{ext}"  # random name: the client never chooses the path
    storage = get_storage()
    try:
        storage.put(settings.public_bucket, path, data, content_type)
    except StorageError:
        raise HTTPException(status_code=502, detail="Could not store the image. Please try again.") from None
    url = storage.public_url(settings.public_bucket, path)
    if url.startswith("/"):  # local development: make it absolute so the frontend can load it
        url = str(request.base_url).rstrip("/") + url
    return {"url": url}
