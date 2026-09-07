#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Separate VS Code data/extensions, sharing the lab's Codex home.
# Usage: bash scripts/vscode-lab.sh [--install]
# --install downloads the official Codex extension into the lab only.
# -----------------------------------------------------------------------------
set -euo pipefail

function main() {
  local lab_root
  local -a code_args
  lab_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
  if [[ $# -gt 1 || ( $# -eq 1 && "$1" != '--install' ) ]]; then
    printf '%s\n' 'Usage: vscode-lab.sh [--install]' >&2
    return 2
  fi
  if [[ ! -f "$lab_root/.local-state/codex/config.toml" ]]; then
    printf '%s\n' 'Run: python3 scripts/config_lab.py init-lab' >&2
    return 1
  fi
  command -v code >/dev/null || {
    printf '%s\n' 'VS Code (code) is not on PATH.' >&2
    return 127
  }
  cd -- "$lab_root"
  export CODEX_HOME="$lab_root/.local-state/codex"
  code_args=(
    --user-data-dir "$lab_root/.local-state/vscode-data"
    --extensions-dir "$lab_root/.local-state/vscode-extensions"
  )
  if [[ "${1:-}" == '--install' ]]; then
    exec code "${code_args[@]}" --install-extension openai.chatgpt
  fi
  exec code "${code_args[@]}" --new-window \
    "$lab_root/codex-config-lab.code-workspace"
}

main "$@"
