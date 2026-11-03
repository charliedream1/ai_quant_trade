#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON:-python3}"
INSTALL_DEPS=0
SERVE=0
HOST="127.0.0.1"
PORT="8000"
STRICT=0
DOCS_SITE_DIR="site"

usage() {
  cat <<'USAGE'
Usage: bash scripts/build_docs.sh [options]

Options:
  --python PATH       Python executable to use (default: $PYTHON or python3)
  --install-deps      Install MkDocs dependencies before checking/building
  --serve             Start mkdocs serve after a successful build
  --host HOST         Host for mkdocs serve (default: 127.0.0.1)
  --port PORT         Port for mkdocs serve (default: 8000)
  --strict            Pass --strict to mkdocs build
  --site-dir PATH     Generated output inside this repository (default: site)
  -h, --help          Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --install-deps)
      INSTALL_DEPS=1
      shift
      ;;
    --serve)
      SERVE=1
      shift
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --strict)
      STRICT=1
      shift
      ;;
    --site-dir)
      DOCS_SITE_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

"$PYTHON_BIN" -c 'import pathlib, sys; root = pathlib.Path.cwd().resolve(); target = pathlib.Path(sys.argv[1]).resolve(); sys.exit(0 if target != root and target.is_relative_to(root) else "site-dir must be a generated directory inside the repository")' "$DOCS_SITE_DIR"

step() {
  echo
  echo "==> $*"
}

scan_generated_site() {
  if [[ ! -d "$DOCS_SITE_DIR" ]]; then
    echo "$DOCS_SITE_DIR not found. Run mkdocs build first." >&2
    exit 1
  fi

  local patterns=(
    "_projects"
    "gen_project_wrappers"
    "../snippets"
    "{% include"
    "include-markdown"
    "ai_notes"
  )

  if command -v rg >/dev/null 2>&1; then
    local rg_args=(-n -S -F)
    local pattern
    for pattern in "${patterns[@]}"; do
      rg_args+=(-e "$pattern")
    done
    set +e
    rg "${rg_args[@]}" -- "$DOCS_SITE_DIR"
    local rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then
      echo "Forbidden legacy docs content found in $DOCS_SITE_DIR." >&2
      exit 1
    fi
    if [[ $rc -ne 1 ]]; then
      echo "rg failed while scanning $DOCS_SITE_DIR." >&2
      exit "$rc"
    fi
  else
    local grep_args=(-R -n -F)
    local pattern
    for pattern in "${patterns[@]}"; do
      grep_args+=(-e "$pattern")
    done
    set +e
    grep "${grep_args[@]}" -- "$DOCS_SITE_DIR"
    local rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then
      echo "Forbidden legacy docs content found in $DOCS_SITE_DIR." >&2
      exit 1
    fi
    if [[ $rc -ne 1 ]]; then
      echo "grep failed while scanning $DOCS_SITE_DIR." >&2
      exit "$rc"
    fi
  fi

  echo "[site scan] OK - no legacy project/include references found."
}

DEPS=("-r" "requirements-docs.txt")

step "Python version"
"$PYTHON_BIN" --version

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  step "Install MkDocs dependencies"
  "$PYTHON_BIN" -m pip install --no-cache-dir "${DEPS[@]}"
fi

step "MkDocs version"
"$PYTHON_BIN" -m mkdocs --version

step "Check docs publish scope"
"$PYTHON_BIN" zz_scripts/check_docs_publish_scope.py

step "Check MkDocs config and assets"
"$PYTHON_BIN" zz_scripts/check_docs_build.py

step "Build docs site"
BUILD_ARGS=(-m mkdocs build --clean --site-dir "$DOCS_SITE_DIR")
if [[ "$STRICT" -eq 1 ]]; then
  BUILD_ARGS+=(--strict)
fi
"$PYTHON_BIN" "${BUILD_ARGS[@]}"

step "Scan generated site"
scan_generated_site

echo
echo "==> Build complete: $DOCS_SITE_DIR"
echo "==> Local URL after serving: http://${HOST}:${PORT}/ai_quant_trade/"

if [[ "$SERVE" -eq 1 ]]; then
  echo
  echo "==> Starting MkDocs dev server. Press Ctrl+C to stop."
  "$PYTHON_BIN" -m mkdocs serve -a "${HOST}:${PORT}"
fi
