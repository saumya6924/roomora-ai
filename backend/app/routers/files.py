"""Serves private files in local-development mode, using the same signed-URL idea as Supabase.

In the cloud, Supabase Storage mints and checks the signed URLs itself and this route is unused.
"""

import mimetypes

import jwt
from fastapi import APIRouter, HTTPException, Response

from app.core.config import settings
from app.core.storage import LocalStorage, StorageError

router = APIRouter(tags=["Files"])


@router.get("/files")
def private_file(token: str):
    if settings.use_supabase_storage:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        data = LocalStorage().get(claims["b"], claims["p"])
    except (jwt.PyJWTError, KeyError, StorageError):
        raise HTTPException(status_code=404, detail="Not found") from None
    media_type = mimetypes.guess_type(claims["p"])[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type, headers={"Cache-Control": "private, max-age=60"})
