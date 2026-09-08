#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Run Codex with this lab's configuration and credential directory.
# Usage: bash scripts/codex-lab.sh [Codex arguments...]
# Examples: login; login status; login --device-auth; --help
# -----------------------------------------------------------------------------
set -euo pipefail

function main() {
  local lab_root
  lab_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
  if [[ ! -f "$lab_root/.local-state/codex/config.toml" ]]; then
    printf '%s\n' 'Run: python3 scripts/config_lab.py init-lab' >&2
    return 1
  fi
  command -v codex >/dev/null || {
    printf '%s\n' 'Codex CLI is not on PATH.' >&2
    return 127
  }
  cd -- "$lab_root"
  export CODEX_HOME="$lab_root/.local-state/codex"
  exec codex "$@"
}

main "$@"
