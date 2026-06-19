#!/bin/bash
# Entry point for Render native-Python deployment of auth-service.
# Works from any working directory because paths are resolved from this script's location.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$REPO_ROOT/clan-identity-be/services/auth-service"
LIBS_DIR="$REPO_ROOT/clan-identity-be/libs"

export PYTHONPATH="$SERVICE_DIR:$LIBS_DIR${PYTHONPATH:+:$PYTHONPATH}"

cd "$SERVICE_DIR"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
