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
