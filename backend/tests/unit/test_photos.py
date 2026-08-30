from pathlib import Path

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _member(client) -> tuple[str, str]:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "family"}
    ).json()["id"]
    member_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    return household_id, member_id


def test_photo_get_is_404_when_missing(client) -> None:
    household_id, member_id = _member(client)
    response = client.get(f"/api/households/{household_id}/members/{member_id}/photo")
    assert response.status_code == 404


def test_upload_and_fetch_profile_photo(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id, member_id = _member(client)
    uploaded = client.post(
        f"/api/households/{household_id}/members/{member_id}/photo",
        files={"file": ("portrait.png", PNG_1X1, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert body["has_photo"] is True
    assert "photo_path" not in body

    fetched = client.get(f"/api/households/{household_id}/members/{member_id}/photo")
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/png")
    assert fetched.content.startswith(b"\x89PNG")
    assert Path(tmp_path).exists()


def test_upload_rejects_non_image(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id, member_id = _member(client)
    response = client.post(
        f"/api/households/{household_id}/members/{member_id}/photo",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_member_list_includes_has_photo(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    household_id, member_id = _member(client)
    client.post(
        f"/api/households/{household_id}/members/{member_id}/photo",
        files={"file": ("portrait.png", PNG_1X1, "image/png")},
    )
    rows = client.get(f"/api/households/{household_id}/members").json()
    match = next(item for item in rows if item["id"] == member_id)
    assert match["has_photo"] is True
    assert "photo_path" not in match
