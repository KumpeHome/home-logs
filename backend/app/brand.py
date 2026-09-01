from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

BRAND_DIR = Path(__file__).resolve().parent / "static" / "brand"
BRAND_ASSETS: dict[str, tuple[Path, str]] = {
    "logo.png": (BRAND_DIR / "logo.png", "image/png"),
    "logo.webp": (BRAND_DIR / "logo.webp", "image/webp"),
}
BRAND_CACHE_HEADERS = {
    "Cache-Control": "public, max-age=86400",
    "Access-Control-Allow-Origin": "*",
    "Cross-Origin-Resource-Policy": "cross-origin",
}


def brand_index() -> dict[str, str]:
    return {fmt: f"/api/brand/logo.{fmt}" for fmt in ("png", "webp")}


def brand_file(filename: str) -> FileResponse:
    asset = BRAND_ASSETS.get(filename)
    if asset is None:
        raise HTTPException(status_code=404, detail="Not found")
    path, media_type = asset
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path,
        media_type=media_type,
        headers=BRAND_CACHE_HEADERS,
    )
