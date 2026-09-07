from pathlib import Path

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
MINI_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _household(client) -> str:
    return client.post(
        "/api/households", json={"name": "Home", "household_type": "foster"}
    ).json()["id"]


def _child(client, household_id: str) -> str:
    return client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]


def _clear_upload_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()


def test_upload_and_fetch_household_document(client, tmp_path, monkeypatch) -> None:
    _clear_upload_dir(tmp_path, monkeypatch)
    household_id = _household(client)
    uploaded = client.post(
        f"/api/households/{household_id}/documents",
        data={"title": "Court order", "category": "court"},
        files={"file": ("order.pdf", MINI_PDF, "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    doc_id = uploaded.json()["id"]
    listed = client.get(f"/api/households/{household_id}/documents")
    assert listed.status_code == 200
    row = next(item for item in listed.json() if item["id"] == doc_id)
    assert row["filename"] == "order.pdf"
    assert "storage_path" not in row
    fetched = client.get(f"/api/households/{household_id}/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("application/pdf")
    assert fetched.content.startswith(b"%PDF")
    assert "order.pdf" in fetched.headers.get("content-disposition", "")
    assert Path(tmp_path).exists()


def test_fetch_document_is_404_when_missing(client) -> None:
    household_id = _household(client)
    response = client.get(
        f"/api/households/{household_id}/documents/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_upload_and_fetch_report_card(client, tmp_path, monkeypatch) -> None:
    _clear_upload_dir(tmp_path, monkeypatch)
    household_id = _household(client)
    child_id = _child(client, household_id)
    enrollment = client.post(
        f"/api/households/{household_id}/enrollments",
        json={
            "member_id": child_id,
            "school_name": "Lincoln Elementary",
            "grade_level": "4",
            "school_year": "2026-2027",
        },
    )
    assert enrollment.status_code == 201, enrollment.text
    enrollment_id = enrollment.json()["id"]
    uploaded = client.post(
        f"/api/households/{household_id}/enrollments/{enrollment_id}/report-cards",
        data={"term": "Q1"},
        files={"file": ("card.png", PNG_1X1, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    card_id = uploaded.json()["id"]
    fetched = client.get(
        f"/api/households/{household_id}/enrollments/{enrollment_id}/report-cards/{card_id}"
    )
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/png")
    assert fetched.content.startswith(b"\x89PNG")
    assert "card.png" in fetched.headers.get("content-disposition", "")


def test_stored_file_response_strips_header_injection_from_filename() -> None:
    from app.api.routers.domain import stored_file_response

    response = stored_file_response(MINI_PDF, filename='order.pdf\r\nX-Injected: yes"')
    disposition = response.headers["content-disposition"]
    assert "\r" not in disposition
    assert "\n" not in disposition
    assert "X-Injected" not in disposition
    assert "order.pdf" in disposition
