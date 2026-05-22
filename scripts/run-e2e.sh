#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${DATABASE_URL:-}" && -f "$ROOT_DIR/apps/data-pipeline/.env" ]]; then
  DATABASE_URL="$(
    awk '
      /^[[:space:]]*DATABASE_URL[[:space:]]*=/ {
        sub(/^[[:space:]]*DATABASE_URL[[:space:]]*=[[:space:]]*/, "")
        gsub(/^"|"$/, "")
        print
        exit
      }
    ' "$ROOT_DIR/apps/data-pipeline/.env"
  )"
  export DATABASE_URL
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required. Export it or set it in apps/data-pipeline/.env." >&2
  exit 1
fi

VITEST_CONFIG="$(mktemp "${TMPDIR:-/tmp}/p1-s13-vitest.XXXXXX.mjs")"
trap 'rm -f "$VITEST_CONFIG"' EXIT

if ROOT_FOR_CONFIG="$(cd "$ROOT_DIR" && pwd -W 2>/dev/null)"; then
  ROOT_FOR_CONFIG="${ROOT_FOR_CONFIG//\\/\/}"
else
  ROOT_FOR_CONFIG="${ROOT_DIR//\\/\/}"
fi
cat > "$VITEST_CONFIG" <<EOF
export default {
  root: '${ROOT_FOR_CONFIG}/apps/api',
  test: {
    include: ['../../tests/e2e/test_phase1_ts_read_e2e.ts'],
    environment: 'node',
  },
};
EOF

(
  cd "$ROOT_DIR/apps/data-pipeline"
  uv run pytest ../../tests/e2e/test_phase1_pipeline_e2e.py
)

(
  cd "$ROOT_DIR"
  pnpm --filter @fcc/api exec vitest run --config "$VITEST_CONFIG"
)
