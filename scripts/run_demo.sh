#!/usr/bin/env bash
# Thin wrapper: run demo CLI from project root (prefers local .venv)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  exec "$ROOT/.venv/bin/python" -m gf_layout_flow.cli "$@"
fi
exec python3 -m gf_layout_flow.cli "$@"
