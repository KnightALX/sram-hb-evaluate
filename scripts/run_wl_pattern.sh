#!/usr/bin/env bash
# Thin wrapper: run SRAM long-WL baseline CLI from project root
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/gf-wl-pattern" ]]; then
  exec "$ROOT/.venv/bin/gf-wl-pattern" "$@"
fi
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  exec "$ROOT/.venv/bin/python" -c "from gf_layout_flow.cli import wl_pattern_main; raise SystemExit(wl_pattern_main())" "$@"
fi
exec python3 -m gf_layout_flow.cli --wl-pattern "$@"
