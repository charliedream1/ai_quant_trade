#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANAGER="uv"
PROFILE="base"
PYTHON_BIN="${PYTHON:-python3}"
RUNTIME_ROOT=""
INSTALL_ZVEC=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manager) MANAGER="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --python) PYTHON_BIN="$2"; shift 2 ;;
    --runtime-root) RUNTIME_ROOT="$2"; shift 2 ;;
    --install-zvec) INSTALL_ZVEC=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '1,100p' "$ROOT_DIR/scripts/setup_project.sh"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

ARGS=("$ROOT_DIR/scripts/setup_project.py" --manager "$MANAGER" --profile "$PROFILE" --python "$PYTHON_BIN")
[[ -n "$RUNTIME_ROOT" ]] && ARGS+=(--runtime-root "$RUNTIME_ROOT")
[[ "$INSTALL_ZVEC" -eq 1 ]] && ARGS+=(--install-zvec)
[[ "$DRY_RUN" -eq 1 ]] && ARGS+=(--dry-run)
exec "$PYTHON_BIN" "${ARGS[@]}"
