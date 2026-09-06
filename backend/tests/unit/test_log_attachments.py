from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _household(client) -> str:
    return client.post(
        "/api/households", json={"name": "Home", "household_type": "foster"}
    ).json()["id"]


def _child(client, household_id: str) -> str:
    return client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]


def _journal(client, household_id: str, child_id: str) -> str:
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "journal_entry",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 19, 21, 30, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "time": "16:30",
                "incident": "Small scrape on left knee after soccer.",
            },
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _pdf_text(content: bytes) -> str:
    return "".join(
        (page.extract_text() or "") for page in PdfReader(BytesIO(content)).pages
    )


def test_form_types_mark_photo_capable_forms(client) -> None:
    rows = {item["code"]: item for item in client.get("/api/form-types").json()}
    assert rows["journal_entry"]["allows_photos"] is True
    assert rows["incident"]["allows_photos"] is True
    assert rows["fire_drill"]["allows_photos"] is False


def test_attach_and_fetch_journal_photo(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id = _household(client)
    child_id = _child(client, household_id)
    log_id = _journal(client, household_id, child_id)
    uploaded = client.post(
        f"/api/households/{household_id}/logs/{log_id}/attachments",
        files={"file": ("bruise.png", PNG_1X1, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert body["filename"] == "bruise.png"
    assert body["content_type"].startswith("image/png")
    assert "storage_path" not in body
    viewed = client.get(f"/api/households/{household_id}/logs/{log_id}")
    assert viewed.status_code == 200
    attachments = viewed.json()["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "bruise.png"
    fetched = client.get(
        f"/api/households/{household_id}/logs/{log_id}/attachments/{attachments[0]['id']}"
    )
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/png")
    assert fetched.content.startswith(b"\x89PNG")
    assert Path(tmp_path).exists()


def test_attach_converts_heic_to_jpeg(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    from tests.unit.test_images import _sample_heic

    household_id = _household(client)
    child_id = _child(client, household_id)
    log_id = _journal(client, household_id, child_id)
    uploaded = client.post(
        f"/api/households/{household_id}/logs/{log_id}/attachments",
        files={"file": ("bruise.heic", _sample_heic(), "image/heic")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["content_type"].startswith("image/jpeg")
    fetched = client.get(
        f"/api/households/{household_id}/logs/{log_id}/attachments/"
        f"{uploaded.json()['id']}"
    )
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/jpeg")
    assert fetched.content.startswith(b"\xff\xd8")


def test_attach_rejects_non_image_and_other_forms(
    client, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id = _household(client)
    child_id = _child(client, household_id)
    log_id = _journal(client, household_id, child_id)
    rejected = client.post(
        f"/api/households/{household_id}/logs/{log_id}/attachments",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert rejected.status_code == 400
    assert "HEIC" in rejected.json()["detail"]
    drill = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "fire_drill",
            "occurred_at": datetime(2026, 8, 19, 15, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "start_time": "10:00",
                "end_time": "10:04",
                "evacuation_seconds": 47,
                "participants": [child_id],
            },
        },
    )
    assert drill.status_code == 201, drill.text
    blocked = client.post(
        f"/api/households/{household_id}/logs/{drill.json()['id']}/attachments",
        files={"file": ("bruise.png", PNG_1X1, "image/png")},
    )
    assert blocked.status_code == 400


def test_official_journal_export_omits_attached_photos(
    client, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id = _household(client)
    child_id = _child(client, household_id)
    log_id = _journal(client, household_id, child_id)
    client.post(
        f"/api/households/{household_id}/logs/{log_id}/attachments",
        files={"file": ("bruise.png", PNG_1X1, "image/png")},
    )
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_journal_entries",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    assert b"/XObject" not in response.content
    assert "Small scrape on left knee after soccer." in _pdf_text(response.content)


def test_entry_export_includes_photos_only_when_requested(
    client, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id = _household(client)
    child_id = _child(client, household_id)
    log_id = _journal(client, household_id, child_id)
    client.post(
        f"/api/households/{household_id}/logs/{log_id}/attachments",
        files={"file": ("bruise.png", PNG_1X1, "image/png")},
    )
    without_photos = client.get(f"/api/households/{household_id}/logs/{log_id}/export")
    assert without_photos.status_code == 200, without_photos.text
    assert without_photos.content.startswith(b"%PDF")
    text = _pdf_text(without_photos.content)
    assert "Journal Entry" in text
    assert "Small scrape on left knee after soccer." in text
    assert b"/XObject" not in without_photos.content
    with_photos = client.get(
        f"/api/households/{household_id}/logs/{log_id}/export?include_photos=true"
    )
    assert with_photos.status_code == 200, with_photos.text
    assert b"/XObject" in with_photos.content
    assert "Small scrape on left knee after soccer." in _pdf_text(with_photos.content)


def test_entry_export_escapes_xml_in_payload(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id = _household(client)
    child_id = _child(client, household_id)
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "journal_entry",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 19, 21, 30, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "time": "16:30",
                "incident": "Cut & bruise <knee> after soccer.",
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.get(
        f"/api/households/{household_id}/logs/{created.json()['id']}/export"
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    text = _pdf_text(response.content)
    assert "Cut & bruise <knee> after soccer." in text


def test_entry_export_notes_missing_photo_files(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id = _household(client)
    child_id = _child(client, household_id)
    log_id = _journal(client, household_id, child_id)
    attached = client.post(
        f"/api/households/{household_id}/logs/{log_id}/attachments",
        files={"file": ("bruise.png", PNG_1X1, "image/png")},
    )
    assert attached.status_code == 200, attached.text
    for path in Path(tmp_path).rglob("*"):
        if path.is_file():
            path.unlink()
    response = client.get(
        f"/api/households/{household_id}/logs/{log_id}/export?include_photos=true"
    )
    assert response.status_code == 200, response.text
    text = _pdf_text(response.content)
    assert "could not be loaded" in text.lower()
    assert "bruise" in text.lower()
    assert b"/XObject" not in response.content
