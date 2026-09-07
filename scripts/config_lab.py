#!/usr/bin/env python3
"""Diagnose Codex and manage reversible configuration replacements.

Requires Python 3.11+. Run with --help for commands and command-specific help.
No third-party Python dependencies. Never reads authentication file contents.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent
GLOBAL_KEYS = {
  "model", "model_reasoning_effort", "plan_mode_reasoning_effort",
  "approval_policy", "sandbox_mode", "web_search", "developer_instructions",
}
EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}


# -----------------------------------------------------------------------------
# Validation: TOML syntax plus focused checks, not a full Codex schema validator.
# -----------------------------------------------------------------------------
def inspect_config(data: bytes) -> tuple[dict, list[str]]:
  config = tomllib.loads(data.decode("utf-8"))
  issues = []
  for table in ("auto_review", "sandbox_workspace_write", "features"):
    values = config.get(table, {})
    if not isinstance(values, dict):
      issues.append(f"{table} must be a table")
      continue
    for key in sorted(GLOBAL_KEYS.intersection(values)):
      issues.append(f"{key} is nested under [{table}], not global")
  for key in ("model_reasoning_effort", "plan_mode_reasoning_effort"):
    allowed = EFFORTS | ({"none"} if key.startswith("plan_") else set())
    if key in config and (
      not isinstance(config[key], str) or config[key] not in allowed
    ):
      issues.append(f"{key} is outside the documented effort values")
  features = config.get("features", {})
  if isinstance(features, dict):
    for name, value in features.items():
      if isinstance(value, dict) and name != "network_proxy":
        issues.append(f"features.{name}: verify table support in this client")
  sandbox = config.get("sandbox_workspace_write", {})
  if isinstance(sandbox, dict):
    if "network_access" in sandbox:
      if type(sandbox["network_access"]) is not bool:
        issues.append("sandbox network_access must be a boolean")
    roots = sandbox.get("writable_roots", [])
    if isinstance(roots, list) and any(
      "/Users/YOU" in str(x) for x in roots
    ):
      issues.append("writable_roots contains an example macOS path")
  return config, issues


def validate(path: Path) -> int:
  if not path.is_file():
    print(f"MISSING: {path}")
    return 1
  try:
    _, issues = inspect_config(path.read_bytes())
  except (tomllib.TOMLDecodeError, UnicodeError) as error:
    print(f"INVALID TOML: {error}")
    return 1
  for issue in issues:
    print(f"CHECK: {issue}")
  if not issues:
    print("PASS: TOML syntax and focused checks; client compatibility untested")
  return int(bool(issues))


# -----------------------------------------------------------------------------
# Writes: opt-in, private backups, atomic replacement, reversible restore.
# -----------------------------------------------------------------------------
def check_target(path: Path) -> None:
  for item in (path, *path.parents):
    if item.is_symlink():
      raise ValueError(f"Refusing symlink path: {item}")
  if path.exists() and not path.is_file():
    raise ValueError(f"Not a regular file: {path}")


def atomic_write(path: Path, data: bytes) -> None:
  check_target(path)
  path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  fd, temporary = tempfile.mkstemp(prefix=".config-lab-", dir=path.parent)
  try:
    with os.fdopen(fd, "wb") as handle:
      handle.write(data)
      handle.flush()
      os.fsync(handle.fileno())
    os.replace(temporary, path)
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)


def replace_with_backup(target: Path, data: bytes) -> Path:
  check_target(target)
  target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  backup_root = target.parent / "config-lab-backups"
  for item in (backup_root, *backup_root.parents):
    if item.is_symlink():
      raise ValueError(f"Refusing symlink path: {item}")
  backup_root.mkdir(mode=0o700, exist_ok=True)
  stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-")
  backup = Path(tempfile.mkdtemp(prefix=stamp, dir=backup_root))
  existed = target.exists()
  old = target.read_bytes() if existed else b""
  if existed:
    atomic_write(backup / "config.toml", old)
  manifest = {
    "target": str(target.absolute()), "existed": existed,
    "sha256": hashlib.sha256(old).hexdigest(),
  }
  atomic_write(backup / "manifest.json", json.dumps(manifest).encode())
  atomic_write(target, data)
  return backup


def restore(backup: Path, write: bool) -> None:
  manifest = json.loads((backup / "manifest.json").read_text())
  target = Path(manifest["target"])
  if not target.is_absolute() or target.name != "config.toml":
    raise ValueError("Invalid backup target")
  check_target(target)
  data = (backup / "config.toml").read_bytes() if manifest["existed"] else b""
  if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
    raise ValueError("Backup checksum mismatch")
  print(f"Restore target: {target}")
  print("Existing candidate will be backed up before restoration.")
  if not write:
    print("Preview only; add --write to restore.")
    return
  saved = replace_with_backup(target, data)
  if not manifest["existed"]:
    target.unlink()
  print(f"Restored. Previous candidate backup: {saved}")


def candidate(preset: str, model: str | None) -> bytes:
  data = (ROOT / "config" / f"{preset}.toml").read_text()
  if model:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", model):
      raise ValueError("Model must be an exact model ID, without whitespace")
    data = f'model = "{model}"\n' + data
  _, issues = inspect_config(data.encode())
  if issues:
    raise ValueError("; ".join(issues))
  return data.encode()


# -----------------------------------------------------------------------------
# Diagnostics: bounded commands; report environment presence, never its values.
# -----------------------------------------------------------------------------
def capture(args: list[str], timeout: int = 15) -> tuple[int, str]:
  try:
    result = subprocess.run(
      args, capture_output=True, text=True, timeout=timeout, check=False,
    )
    return result.returncode, result.stdout.strip()
  except FileNotFoundError:
    return 127, ""
  except subprocess.TimeoutExpired:
    return 124, ""


def probe(job: tuple[str, str]) -> str:
  host, family = job
  args = ["curl", "-q", "--silent", "--output", "/dev/null",
          "--write-out", "%{http_code}", "--connect-timeout", "5",
          "--max-time", "10", "--proto", "=https"]
  if family != "auto":
    args.append("-" + family)
  code, output = capture(args + [f"https://{host}/"], timeout=12)
  status = output if re.fullmatch(r"\d{3}", output) else "unknown"
  return f"{host:30} family={family:4} curl_exit={code:<3} HTTP={status}"


def doctor(path: Path, network: bool, families: bool) -> int:
  print("Codex configuration diagnostic (no credentials or raw logs included)")
  print(f"UTC: {datetime.now(timezone.utc).isoformat()}")
  print(f"Python: {sys.version.split()[0]}")
  for name in ("codex", "code", "curl", "node", "npm", "uvx", "npx"):
    executable = shutil.which(name)
    print(f"{name}: {executable or 'NOT FOUND'}")
    if executable and name in {"codex", "code", "curl"}:
      code, output = capture([executable, "--version"])
      # Only a conservative version token; never emit arbitrary wrapper output.
      version = re.search(r"\b\d+\.\d+(?:\.\d+)?\b", output)
      print(f"  version={version[0] if version else 'unknown'} exit={code}")
  for name in (
    "CODEX_HOME", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "CODEX_CA_CERTIFICATE", "SSL_CERT_FILE", "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS", "NODE_TLS_REJECT_UNAUTHORIZED",
  ):
    print(f"env {name}: {'SET' if name in os.environ else 'unset'}")
  print(f"Config: {path}")
  result = validate(path)
  print(f"auth.json exists: {(path.parent / 'auth.json').is_file()}")
  print("Absence does not imply logged out: a credential store may be in use.")
  if network:
    hosts = ("chatgpt.com", "auth.openai.com", "api.openai.com",
             "files.oaiusercontent.com", "developers.openai.com")
    modes = ("auto", "4", "6") if families else ("auto",)
    with ThreadPoolExecutor(max_workers=5) as executor:
      for line in executor.map(probe, [(h, f) for h in hosts for f in modes]):
        print(line)
    print("HTTP responses are transport clues, not login/upload validation.")
    print("curl: 5/6=DNS; 7=connect; 28=timeout; 35=TLS; 60=certificate.")
  return result


# -----------------------------------------------------------------------------
# Command-line interface.
# -----------------------------------------------------------------------------
def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  commands = parser.add_subparsers(dest="command", required=True)
  check = commands.add_parser("validate", help="Check TOML and common mistakes")
  check.add_argument("path", type=Path)
  default = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
  diagnose = commands.add_parser("doctor", help="Read-only local diagnostics")
  diagnose.add_argument("--config", type=Path, default=default / "config.toml")
  diagnose.add_argument("--network", action="store_true",
                        help="Also send unauthenticated HTTPS requests")
  diagnose.add_argument("--ip-families", action="store_true",
                        help="With --network, compare IPv4 and IPv6")
  for name, description in (
    ("init-lab", "Create isolated lab state; refuse to overwrite it"),
    ("apply", "Preview replacement; use --write to back up and apply"),
  ):
    command = commands.add_parser(name, help=description)
    command.add_argument("--preset", choices=("recovery", "development"),
                         default="recovery")
    command.add_argument("--model", help="Exact ID from your /model menu")
    if name == "apply":
      command.add_argument("--target", type=Path,
                           default=default / "config.toml")
      command.add_argument("--write", action="store_true")
  undo = commands.add_parser("restore", help="Restore a config-lab backup")
  undo.add_argument("backup", type=Path)
  undo.add_argument("--write", action="store_true")
  args = parser.parse_args()
  if args.command == "validate":
    return validate(args.path.expanduser())
  if args.command == "doctor":
    return doctor(args.config.expanduser(), args.network, args.ip_families)
  if args.command == "restore":
    restore(args.backup.expanduser(), args.write)
    return 0
  data = candidate(args.preset, args.model)
  if args.command == "init-lab":
    target = ROOT / ".local-state" / "codex" / "config.toml"
    check_target(target)
    if target.exists():
      raise ValueError("Lab already exists; use apply --target to change it")
    # File-backed credentials prevent reuse of the ordinary OS keyring entry.
    data = b'cli_auth_credentials_store = "file"\n' + data
    atomic_write(target, data)
    print(f"Created: {target}")
    print("Next: bash scripts/codex-lab.sh login")
    return 0
  target = args.target.expanduser().absolute()
  if target == ROOT / ".local-state" / "codex" / "config.toml":
    data = b'cli_auth_credentials_store = "file"\n' + data
  if target.name != "config.toml":
    raise ValueError("Target filename must be config.toml")
  check_target(target)
  print(f"Target: {target}")
  print("Full replacement, not a merge. Credentials/sessions are not changed.")
  print(data.decode())
  if args.write:
    print(f"Applied. Backup: {replace_with_backup(target, data)}")
  else:
    print("Preview only; add --write to apply.")
  return 0


if __name__ == "__main__":
  try:
    sys.exit(main())
  except (OSError, ValueError) as error:
    print(f"ERROR: {error}", file=sys.stderr)
    sys.exit(1)
