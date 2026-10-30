"""File storage: Supabase Storage in the cloud, a local folder for development and tests.

Public files (product photos, portfolio) get a permanent URL. Private files (room photos and AI
results) are only reachable through a short-lived signed URL minted by the backend.
"""

import time
from pathlib import Path

import httpx
import jwt

from app.core.config import settings


class StorageError(RuntimeError):
    pass


class SupabaseStorage:
    def __init__(self) -> None:
        self.base = settings.supabase_url.rstrip("/") + "/storage/v1"
        self.headers = {
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "apikey": settings.supabase_service_key,
        }

    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        r = httpx.post(
            f"{self.base}/object/{bucket}/{path}",
            content=data,
            headers={**self.headers, "Content-Type": content_type, "x-upsert": "false"},
            timeout=30,
        )
        if r.status_code >= 300:
            raise StorageError(f"Upload failed ({r.status_code})")

    def get(self, bucket: str, path: str) -> bytes:
        r = httpx.get(f"{self.base}/object/{bucket}/{path}", headers=self.headers, timeout=30)
        if r.status_code >= 300:
            raise StorageError(f"Download failed ({r.status_code})")
        return r.content

    def delete(self, bucket: str, path: str) -> None:
        httpx.request(
            "DELETE",
            f"{self.base}/object/{bucket}",
            headers=self.headers,
            json={"prefixes": [path]},
            timeout=30,
        )

    def public_url(self, bucket: str, path: str) -> str:
        return f"{self.base}/object/public/{bucket}/{path}"

    def signed_url(self, bucket: str, path: str, expires: int = 300) -> str:
        r = httpx.post(
            f"{self.base}/object/sign/{bucket}/{path}",
            headers=self.headers,
            json={"expiresIn": expires},
            timeout=30,
        )
        if r.status_code >= 300:
            raise StorageError(f"Could not sign URL ({r.status_code})")
        return f"{self.base}{r.json()['signedURL']}"


class LocalStorage:
    """Development fallback. Public files are served by the API at /media; private ones at /files."""

    def __init__(self) -> None:
        self.root = Path(settings.media_dir)

    def _path(self, bucket: str, path: str) -> Path:
        target = (self.root / bucket / path).resolve()
        if not str(target).startswith(str(self.root.resolve())):
            raise StorageError("Invalid path")
        return target

    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        target = self._path(bucket, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def get(self, bucket: str, path: str) -> bytes:
        target = self._path(bucket, path)
        if not target.is_file():
            raise StorageError("File not found")
        return target.read_bytes()

    def delete(self, bucket: str, path: str) -> None:
        self._path(bucket, path).unlink(missing_ok=True)

    def public_url(self, bucket: str, path: str) -> str:
        return f"/media/{bucket}/{path}"

    def signed_url(self, bucket: str, path: str, expires: int = 300) -> str:
        token = jwt.encode(
            {"b": bucket, "p": path, "exp": int(time.time()) + expires},
            settings.secret_key,
            algorithm="HS256",
        )
        return f"/files?token={token}"


def get_storage() -> SupabaseStorage | LocalStorage:
    return SupabaseStorage() if settings.use_supabase_storage else LocalStorage()
