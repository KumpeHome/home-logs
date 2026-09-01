from fastapi.testclient import TestClient

from app.main import create_app


def test_brand_index_lists_png_and_webp_without_auth() -> None:
    with TestClient(create_app(init_db=False)) as client:
        response = client.get("/api/brand")
        assert response.status_code == 200
        body = response.json()
        assert body["png"] == "/api/brand/logo.png"
        assert body["webp"] == "/api/brand/logo.webp"


def test_brand_logo_png_is_public() -> None:
    with TestClient(create_app(init_db=False)) as client:
        response = client.get("/api/brand/logo.png")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/png")
        assert response.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert response.headers.get("access-control-allow-origin") == "*"
        assert "public" in response.headers.get("cache-control", "")


def test_brand_logo_allows_head_for_oidc_probes() -> None:
    with TestClient(create_app(init_db=False)) as client:
        response = client.head("/api/brand/logo.png")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/png")


def test_brand_logo_is_also_at_asset_paths_oidc_clients_try() -> None:
    with TestClient(create_app(init_db=False)) as client:
        for path in (
            "/api/assets/brand/logo.png",
            "/assets/brand/logo.png",
            "/favicon.ico",
        ):
            response = client.get(path)
            assert response.status_code == 200, path
            assert response.headers["content-type"].startswith("image/png")
            assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_brand_webp_is_also_at_asset_paths() -> None:
    with TestClient(create_app(init_db=False)) as client:
        for path in ("/api/assets/brand/logo.webp", "/assets/brand/logo.webp"):
            response = client.get(path)
            assert response.status_code == 200, path
            assert response.content[8:12] == b"WEBP"


def test_brand_logo_webp_is_public() -> None:
    with TestClient(create_app(init_db=False)) as client:
        response = client.get("/api/brand/logo.webp")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/webp")
        assert response.content[:4] == b"RIFF"
        assert response.content[8:12] == b"WEBP"


def test_brand_unknown_file_is_not_found() -> None:
    with TestClient(create_app(init_db=False)) as client:
        response = client.get("/api/brand/../pyproject.toml")
        assert response.status_code == 404
        response = client.get("/api/brand/secret.txt")
        assert response.status_code == 404


def test_brand_assets_are_fixed_files_not_built_from_the_request() -> None:
    from app.brand import BRAND_ASSETS, BRAND_DIR

    png_path, png_type = BRAND_ASSETS["logo.png"]
    webp_path, webp_type = BRAND_ASSETS["logo.webp"]
    assert png_path == BRAND_DIR / "logo.png"
    assert webp_path == BRAND_DIR / "logo.webp"
    assert png_type == "image/png"
    assert webp_type == "image/webp"
    assert set(BRAND_ASSETS) == {"logo.png", "logo.webp"}
