"""The room-photo studio: upload a photo, generate redesigned versions, keep the whole history.

The original is never modified. Every edit is a new row that points at the version it was made from.
Photos live in the PRIVATE bucket and are only reachable through short-lived signed URLs.
"""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import ImageKind
from app.core.ratelimit import studio_limit, upload_limit
from app.core.security import get_current_user
from app.core.storage import StorageError, get_storage
from app.db.session import get_db
from app.models import DesignImage, User
from app.routers.uploads import read_image
from app.schemas.common import Message
from app.schemas.designs import DesignRequirements
from app.services.ai_editor import edit_requirements
from app.services.ai_editor.prompt import has_hindi
from app.services.image_ai import ImageProviderError, get_provider
from app.services.stats import now_utc

router = APIRouter(prefix="/studio", tags=["Room Photo Studio"])


class GenerateRequest(BaseModel):
    source_id: int
    prompt: str = Field(min_length=2, max_length=500)  # English, Hindi or Hinglish
    strength: float = Field(default=0.6, ge=0.1, le=1.0)


class StudioImageOut(BaseModel):
    id: int
    kind: ImageKind
    parent_id: int | None
    prompt: str
    provider: str
    created_at: datetime
    url: str  # short-lived signed URL


def image_out(image: DesignImage, request: Request) -> dict:
    url = get_storage().signed_url(settings.private_bucket, image.storage_path)
    if url.startswith("/"):  # local development
        url = str(request.base_url).rstrip("/") + url
    return {
        "id": image.id,
        "kind": image.kind,
        "parent_id": image.parent_id,
        "prompt": image.prompt,
        "provider": image.provider,
        "created_at": image.created_at,
        "url": url,
    }


def own_image(db: Session, user: User, image_id: int) -> DesignImage:
    image = db.get(DesignImage, image_id)
    if image is None or image.user_id != user.id:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


def to_english(prompt: str) -> str:
    """Image models read English best. A Hindi command is turned into an English description first."""
    if not has_hindi(prompt):
        return prompt
    result = edit_requirements(prompt, DesignRequirements(), "hi")
    return result["prompt"] if result["changes"] else prompt


def store(user: User, data: bytes, ext: str, content_type: str) -> str:
    path = f"{user.id}/{uuid.uuid4().hex}.{ext}"
    try:
        get_storage().put(settings.private_bucket, path, data, content_type)
    except StorageError:
        raise HTTPException(status_code=502, detail="Could not store the image. Please try again.") from None
    return path


@router.post("/upload", response_model=StudioImageOut, status_code=201, dependencies=[Depends(upload_limit)])
def upload_room_photo(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data, content_type, ext = read_image(file)
    image = DesignImage(
        user_id=user.id, kind=ImageKind.ORIGINAL, storage_path=store(user, data, ext, content_type)
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image_out(image, request)


@router.post(
    "/generate", response_model=StudioImageOut, status_code=201, dependencies=[Depends(studio_limit)]
)
def generate(
    data: GenerateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source = own_image(db, user, data.source_id)

    since = now_utc() - timedelta(days=1)
    made_today = (
        db.query(DesignImage)
        .filter(
            DesignImage.user_id == user.id,
            DesignImage.kind == ImageKind.GENERATED,
            DesignImage.created_at >= since,
        )
        .count()
    )
    if made_today >= settings.studio_daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"You have reached today's limit of {settings.studio_daily_limit} designs. "
            "Try again tomorrow.",
        )

    try:
        original = get_storage().get(settings.private_bucket, source.storage_path)
        picture = get_provider().edit(original, to_english(data.prompt), data.strength)
    except ImageProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    except StorageError:
        raise HTTPException(
            status_code=502, detail="Could not read the source image. Please try again."
        ) from None

    version = DesignImage(
        user_id=user.id,
        parent_id=source.id,
        kind=ImageKind.GENERATED,
        prompt=data.prompt,
        provider=get_provider().name,
        storage_path=store(user, picture, "png", "image/png"),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return image_out(version, request)


def _family(db: Session, user: User, image: DesignImage) -> list[DesignImage]:
    """The original and every version made from it, oldest first."""
    everything = db.query(DesignImage).filter(DesignImage.user_id == user.id).order_by(DesignImage.id).all()
    by_id = {i.id: i for i in everything}
    root = image
    while root.parent_id and root.parent_id in by_id:
        root = by_id[root.parent_id]
    family, frontier = [root], {root.id}
    for candidate in everything:
        if candidate.parent_id in frontier:
            family.append(candidate)
            frontier.add(candidate.id)
    return family


@router.get("/history", response_model=list[StudioImageOut])
def history(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    images = (
        db.query(DesignImage)
        .filter(DesignImage.user_id == user.id)
        .order_by(DesignImage.id.desc())
        .limit(60)
        .all()
    )
    return [image_out(i, request) for i in images]


@router.get("/images/{image_id}", response_model=StudioImageOut)
def get_image(
    image_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return image_out(own_image(db, user, image_id), request)


@router.get("/images/{image_id}/versions", response_model=list[StudioImageOut])
def versions(
    image_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return [image_out(i, request) for i in _family(db, user, own_image(db, user, image_id))]


@router.delete("/images/{image_id}", response_model=Message)
def delete_image(image_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a version. Deleting an original removes everything made from it."""
    image = own_image(db, user, image_id)
    doomed = [
        i for i in _family(db, user, image) if i.id == image.id or _descends_from(db, user, i, image.id)
    ]
    for item in doomed:
        get_storage().delete(settings.private_bucket, item.storage_path)
    for item in sorted(doomed, key=lambda i: i.id, reverse=True):  # children before parents
        db.delete(item)
    db.commit()
    return {"message": "Image deleted"}


def _descends_from(db: Session, user: User, image: DesignImage, ancestor_id: int) -> bool:
    by_id = {i.id: i for i in db.query(DesignImage).filter(DesignImage.user_id == user.id)}
    cursor = image
    while cursor.parent_id:
        if cursor.parent_id == ancestor_id:
            return True
        cursor = by_id.get(cursor.parent_id)
        if cursor is None:
            return False
    return False
