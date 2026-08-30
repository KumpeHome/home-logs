#!/bin/sh
set -e

js_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

cat > /usr/share/nginx/html/env.js <<EOF
window.__ENV__ = {
  OIDC_ISSUER: "$(js_escape "${OIDC_ISSUER:-}")",
  OIDC_CLIENT_ID: "$(js_escape "${OIDC_CLIENT_ID:-}")",
  OIDC_AUDIENCE: "$(js_escape "${OIDC_AUDIENCE:-}")",
  OIDC_SCOPES: "$(js_escape "${OIDC_SCOPES:-}")"
};
EOF

exec "$@"
