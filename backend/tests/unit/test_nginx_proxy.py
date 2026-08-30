from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_frontend_nginx_allows_pdf_multipart_uploads() -> None:
    conf = (ROOT / "frontend" / "nginx.conf").read_text()
    assert "client_max_body_size" in conf
    assert "proxy_http_version 1.1" in conf
    assert 'proxy_set_header Expect ""' in conf


def test_backend_image_makes_upload_volume_writable() -> None:
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text()
    entrypoint = (ROOT / "backend" / "docker-entrypoint.sh").read_text()
    assert "docker-entrypoint.sh" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert "chown" in entrypoint
    assert "UPLOAD_DIR" in entrypoint
    assert "runuser -u appuser" in entrypoint
