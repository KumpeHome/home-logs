#!/bin/sh
set -e
UPLOAD_DIR="${UPLOAD_DIR:-/data/uploads}"
mkdir -p "$UPLOAD_DIR"
chown -R appuser:appuser "$UPLOAD_DIR"
exec runuser -u appuser -- "$@"
