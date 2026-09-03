import contextlib
import os

import pytest

from app.core.errors import DomainError
from app.storage.files import LocalFileStore


def test_save_creates_household_and_category_dirs(tmp_path) -> None:
    store = LocalFileStore(str(tmp_path / "uploads"))
    path = store.save("hid-1", "templates", "visit.pdf", b"%PDF-1.4")
    stored = tmp_path / "uploads" / "hid-1" / "templates" / "visit.pdf"
    assert stored.read_bytes() == b"%PDF-1.4"
    assert path == str(stored)


def test_save_raises_domain_error_when_upload_dir_not_writable(tmp_path) -> None:
    root = tmp_path / "uploads"
    root.mkdir()
    root.chmod(0o555)
    store = LocalFileStore(str(root))
    try:
        with pytest.raises(DomainError, match="Could not store the uploaded file"):
            store.save("hid-1", "templates", "visit.pdf", b"%PDF-1.4")
    finally:
        root.chmod(0o755)


def test_save_allows_nested_category_under_root(tmp_path) -> None:
    store = LocalFileStore(str(tmp_path / "uploads"))
    path = store.save("hid-1", "photos/member-1", "portrait.jpg", b"img")
    stored = tmp_path / "uploads" / "hid-1" / "photos" / "member-1" / "portrait.jpg"
    assert stored.read_bytes() == b"img"
    assert path == str(stored)


def test_save_rejects_household_id_that_escapes_root(tmp_path) -> None:
    root = tmp_path / "uploads"
    store = LocalFileStore(str(root))
    with pytest.raises(DomainError, match="Invalid storage path"):
        store.save("../escaped", "templates", "visit.pdf", b"%PDF-1.4")
    assert not (tmp_path / "escaped").exists()
    assert list(root.rglob("visit.pdf")) == []


def test_save_rejects_category_that_escapes_root(tmp_path) -> None:
    root = tmp_path / "uploads"
    store = LocalFileStore(str(root))
    with pytest.raises(DomainError, match="Invalid storage path"):
        store.save("hid-1", "../../outside", "visit.pdf", b"%PDF-1.4")
    assert not (tmp_path / "outside").exists()
    assert list(root.rglob("visit.pdf")) == []


def test_save_rejects_absolute_path_segment(tmp_path) -> None:
    root = tmp_path / "uploads"
    store = LocalFileStore(str(root))
    with pytest.raises(DomainError, match="Invalid storage path"):
        store.save("hid-1", str(tmp_path / "outside"), "visit.pdf", b"%PDF-1.4")
    assert list(root.rglob("visit.pdf")) == []


def test_save_does_not_follow_filename_symlink(tmp_path) -> None:
    root = tmp_path / "uploads"
    target_dir = root / "hid-1" / "templates"
    target_dir.mkdir(parents=True)
    other = target_dir / "other.pdf"
    other.write_bytes(b"original")
    (target_dir / "visit.pdf").symlink_to(other)
    store = LocalFileStore(str(root))
    with pytest.raises(DomainError):
        store.save("hid-1", "templates", "visit.pdf", b"new-content")
    assert other.read_bytes() == b"original"


def test_save_does_not_follow_category_symlink_within_root(tmp_path) -> None:
    root = tmp_path / "uploads"
    other = root / "hid-other" / "templates"
    other.mkdir(parents=True)
    household = root / "hid-1"
    household.mkdir()
    (household / "templates").symlink_to(other)
    store = LocalFileStore(str(root))
    with pytest.raises(DomainError):
        store.save("hid-1", "templates", "visit.pdf", b"data")
    assert list(other.iterdir()) == []


def test_save_does_not_write_outside_root_when_dir_replaced_with_symlink(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "uploads"
    outside = tmp_path / "outside"
    outside.mkdir()
    store = LocalFileStore(str(root))
    real_mkdir = os.mkdir

    def replace_household_with_symlink(path, mode=0o777, *, dir_fd=None):
        real_mkdir(path, mode, dir_fd=dir_fd)
        name = path if isinstance(path, str) else os.fsdecode(path)
        if os.path.basename(name) != "hid-1":
            return
        household = root / "hid-1"
        if household.is_dir() and not household.is_symlink():
            household.rmdir()
            household.symlink_to(outside)

    monkeypatch.setattr(os, "mkdir", replace_household_with_symlink)
    with contextlib.suppress(DomainError):
        store.save("hid-1", "templates", "visit.pdf", b"%PDF-1.4")
    assert list(outside.rglob("visit.pdf")) == []
