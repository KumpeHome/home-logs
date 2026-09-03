from __future__ import annotations

import contextlib
import errno
import os
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import DomainError

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_FILE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC | _NOFOLLOW
_SYMLINK_ERRNOS = {errno.ELOOP, errno.ENOTDIR}


def _path_components(*parts: str) -> list[str]:
    components: list[str] = []
    for part in parts:
        if os.path.isabs(part):
            raise DomainError("Invalid storage path.")
        for raw in part.replace("\\", "/").split("/"):
            if raw in ("", ".", ".."):
                raise DomainError("Invalid storage path.")
            components.append(raw)
    return components


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
        parts = _path_components(household_id, category, safe)
        candidate = os.path.join(os.path.realpath(self.root), *parts)
        try:
            return self._write_contained(candidate, data)
        except OSError as exc:
            if exc.errno in _SYMLINK_ERRNOS:
                raise DomainError("Invalid storage path.") from exc
            raise DomainError("Could not store the uploaded file. Try again.") from exc

    def _write_contained(self, candidate: str, data: bytes) -> str:
        root = os.path.realpath(self.root)
        prefix = root if root.endswith(os.sep) else root + os.sep
        normalized = os.path.normpath(candidate)
        if not normalized.startswith(prefix):
            raise DomainError("Invalid storage path.")
        resolved = os.path.realpath(candidate)
        if not resolved.startswith(prefix):
            raise DomainError("Invalid storage path.")
        names = os.path.relpath(normalized, root).split(os.sep)
        file_name = names.pop()
        if not file_name or any(name in ("", ".", "..") for name in names):
            raise DomainError("Invalid storage path.")
        fds: list[int] = [os.open(self.root, _DIR_FLAGS)]
        try:
            for name in names:
                with contextlib.suppress(FileExistsError):
                    os.mkdir(name, dir_fd=fds[-1])
                fds.append(os.open(name, _DIR_FLAGS | _NOFOLLOW, dir_fd=fds[-1]))
            file_fd = os.open(file_name, _FILE_FLAGS, 0o644, dir_fd=fds[-1])
            with os.fdopen(file_fd, "wb") as handle:
                handle.write(data)
        finally:
            for fd in reversed(fds):
                os.close(fd)
        return normalized

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()
