"""File storage abstraction. MVP ships a local-disk backend with signed (pre-signed style) URLs."""
from __future__ import annotations

import asyncio
import hashlib
import re
import uuid
from pathlib import Path

from core.config import settings
from core.security import create_download_token

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    base = Path(name).name or "file"
    cleaned = _SAFE.sub("_", base).strip("._") or "file"
    return cleaned[:200]


class StorageError(Exception):
    pass


class LocalStorage:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.LOCAL_STORAGE_PATH).resolve()

    def _path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise StorageError("Invalid storage key")
        return path

    async def save(self, org_id: uuid.UUID, case_id: uuid.UUID, filename: str, data: bytes) -> tuple[str, str]:
        """Persist bytes; returns (storage_key, sha256)."""
        digest = hashlib.sha256(data).hexdigest()
        key = f"{org_id}/{case_id}/{uuid.uuid4().hex}_{safe_filename(filename)}"
        path = self._path_for(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)
        return key, digest

    async def read(self, key: str) -> bytes:
        path = self._path_for(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise StorageError("File not found in storage") from exc

    def presigned_url(self, document_id: uuid.UUID, org_id: uuid.UUID) -> tuple[str, int]:
        expires = settings.PRESIGNED_URL_EXPIRE_SECONDS
        token = create_download_token(str(document_id), str(org_id), expires)
        base = settings.PUBLIC_API_URL.rstrip("/")
        return f"{base}/api/v1/documents/{document_id}/download?token={token}", expires


def get_storage() -> LocalStorage:
    if settings.STORAGE_BACKEND != "local":
        # S3 backend is on the roadmap; the interface (save/read/presigned_url) is backend-agnostic.
        raise StorageError(f"Unsupported STORAGE_BACKEND '{settings.STORAGE_BACKEND}' in MVP")
    return LocalStorage()
