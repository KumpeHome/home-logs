import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_frontend_nginx_allows_pdf_multipart_uploads() -> None:
    conf = (ROOT / "frontend" / "nginx.conf").read_text()
    assert "client_max_body_size" in conf
    assert "proxy_http_version 1.1" in conf
    assert 'proxy_set_header Expect ""' in conf


def test_frontend_entrypoint_writes_oidc_from_env(tmp_path) -> None:
    src = (ROOT / "frontend" / "docker-entrypoint.sh").read_text()
    script = tmp_path / "docker-entrypoint.sh"
    script.write_text(src.replace("/usr/share/nginx/html", str(tmp_path)))
    script.chmod(0o755)
    subprocess.run(
        [str(script), "true"],
        check=True,
        env={
            **os.environ,
            "OIDC_ISSUER": "https://auth.stage.kumpe.app",
            "OIDC_CLIENT_ID": "home-logs-spa",
            "OIDC_AUDIENCE": "https://homelogs.app/api",
            "OIDC_SCOPES": "openid profile email",
        },
    )
    js = (tmp_path / "env.js").read_text()
    dockerfile = (ROOT / "frontend" / "Dockerfile").read_text()
    index_html = (ROOT / "frontend" / "src" / "index.html").read_text()
    assert "https://auth.stage.kumpe.app" in js
    assert "home-logs-spa" in js
    assert "window.__ENV__" in js
    assert "docker-entrypoint.sh" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert 'src="env.js"' in index_html


def test_backend_image_makes_upload_volume_writable() -> None:
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text()
    entrypoint = (ROOT / "backend" / "docker-entrypoint.sh").read_text()
    assert "docker-entrypoint.sh" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert "chown" in entrypoint
    assert "UPLOAD_DIR" in entrypoint
    assert "runuser -u appuser" in entrypoint
