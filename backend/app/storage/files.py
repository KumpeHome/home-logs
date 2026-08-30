from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.errors import DomainError


class LocalFileStore:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or get_settings().upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        household_id: str,
        category: str,
        filename: str,
        data: bytes,
    ) -> str:
        safe = filename.replace("/", "_").replace("\\", "_")
        directory = self.root / household_id / category
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / safe
            path.write_bytes(data)
        except OSError as exc:
            raise DomainError("Could not store the uploaded file. Try again.") from exc
        return str(path)

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()
