# Codex configuration lab for Arch Linux

A reversible recovery and configuration experiment for Codex CLI and VS Code.
Start with recovery, establish that login and a new conversation work, and then
apply the development preset. This is an example repository, not an installer
that changes your computer upon opening it.

## Requirements

- Python 3.11 or newer, Bash, and an existing Codex CLI installation.
- `curl` for optional network diagnostics; `code` for the VS Code experiment.
- Git is optional until you want to track your own changes.

No Python packages, sudo, shell-profile changes, or authentication tokens are
required to inspect this repository. Login requires your own account.

## 1. Diagnose the existing configuration

From the extracted `codex-config-lab` directory:

```bash
python3 scripts/config_lab.py doctor --network
```

The command reads the actual configuration at `$CODEX_HOME/config.toml`, or
`~/.codex/config.toml` when that variable is unset. A nonzero exit indicates a
missing configuration or a failed configuration check, not necessarily a network
failure. It reports paths, versions and whether selected environment variables
are set; it does not print their values, tokens, raw logs, or config contents.
Check the report for personal paths before sharing it.

To save a report locally:

```bash
mkdir -p reports
python3 scripts/config_lab.py doctor --network > reports/diagnostic.txt 2>&1
```

For an IPv4/IPv6 comparison:

```bash
python3 scripts/config_lab.py doctor --network --ip-families
```

See [findings](docs/findings.md) and [network interpretation](docs/network.md).

## 2. Start an isolated CLI experiment

```bash
python3 scripts/config_lab.py init-lab
bash scripts/codex-lab.sh login
bash scripts/codex-lab.sh login status
bash scripts/codex-lab.sh
```

In the new conversation, ask: `Reply with OK. Do not run tools or edit files.`
Then use `/model` to inspect the models and reasoning choices actually available
to this client and account. A successful login alone is not a successful model
request. Do not resume an old conversation for this first test.

`init-lab` creates `.local-state/codex/config.toml` and refuses to overwrite an
existing lab. The wrappers set `CODEX_HOME` only for their child processes. File
credential storage is selected for the lab, so authentication is kept inside
that directory instead of reusing an OS keyring entry. Do not publish that
state. The supplied Git ignore rules exclude it.

The lab still inherits your shell's proxy/certificate environment and machine
policy. It is an isolation test for user configuration, not a network sandbox or
a bypass of administrative requirements. System configuration and applicable
ancestor project instructions may still matter. Place this lab outside an
existing configured repository for the clearest comparison.

If browser login cannot return through localhost, try:

```bash
bash scripts/codex-lab.sh login --device-auth
```

Device login must be available/enabled for your account. See
[OpenAI authentication guidance](https://learn.chatgpt.com/docs/auth).
Do not send anyone `auth.json`, API keys, cookies, or device codes.

## 3. Test VS Code separately

Install the official extension into the lab's separate extension directory:

```bash
bash scripts/vscode-lab.sh --install
bash scripts/vscode-lab.sh
```

Open the Codex sidebar and start a new conversation. The lab VS Code instance
has separate user data and extensions, and uses the same lab `CODEX_HOME` as the
CLI. Do not enable Settings Sync in this experiment. Sign in through the sidebar
if requested. If testing a changed process environment, close the lab's VS Code
instance completely before relaunching it.

Use Codex Settings → Open config.toml to confirm that the extension opened the
lab's configuration. If it opens your ordinary config instead, record that
path and the extension version; do not apply changes there accidentally.

The workspace opens this repository instead of an empty `folders` array. It
uses two-space indentation and an 81-column ruler, with automatic edits on save
disabled for a deliberate first trial. Your normal VS Code settings and
keybindings remain available in your usual editor instance.

The extension uses its own bundled executable. Do not set
`chatgpt.cliExecutable` merely to match the terminal CLI: OpenAI documents that
setting as development-only and warns that overrides can break extension
functionality. [IDE settings](https://learn.chatgpt.com/docs/developer-settings?surface=ide)

## 4. Enable the development preset

After the recovery conversation succeeds, preview the development configuration:

```bash
python3 scripts/config_lab.py apply --preset development \
  --target "$PWD/.local-state/codex/config.toml"
```

Apply it:

```bash
python3 scripts/config_lab.py apply --preset development \
  --target "$PWD/.local-state/codex/config.toml" --write
```

Optionally add `--model 'EXACT_MODEL_ID'` to either command, replacing the
placeholder with the ID confirmed in your model picker. The template deliberately
lets the client choose its default until you make that choice. Model labels in
a browser session do not establish availability in a separately installed CLI.

The development preset requests `xhigh` reasoning for normal and Plan modes,
live search, and network access for sandboxed shell commands. `xhigh` is
model-dependent; if unavailable, select a supported model/effort in the UI or
edit the template. The documented effort values do not include `max`.
[Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

There is no blanket collection of experimental feature flags. Add an optional
capability only after the baseline works, following [extensions](docs/extensions.md).

## 5. Apply to your ordinary installation, when ready

Close active Codex sessions and VS Code first. Preview:

```bash
python3 scripts/config_lab.py apply --preset recovery
```

If the displayed target is correct, apply:

```bash
python3 scripts/config_lab.py apply --preset recovery --write
```

This is a **complete config replacement**, with a private, timestamped backup.
It does not merge broken TOML, delete credentials, remove installed plugins, or
modify sessions. Replacing config removes its explicit MCP, plugin, trust,
model, and hook entries from the active file; other configuration layers or
plugin stores can still contribute behavior. Only the isolated experiment
starts with a separate user state directory.

The target defaults to the current `CODEX_HOME`, or `~/.codex`. You can select an
explicit `--target "$HOME/.codex/config.toml"`. Symlink targets or symlink parent
directories are refused; edit a symlink-managed configuration through its own
configuration manager instead. Configurations and backup files are written
with private file permissions (0600).

Use `codex login status`, then `codex login` if needed, then start a new `codex`
conversation and reopen VS Code. Both clients share configuration layers.
[Configuration basics](https://learn.chatgpt.com/docs/config-file/config-basic)

After successful recovery, repeat with `--preset development`, optionally
specifying the confirmed model ID.

## Restore

Each applied change prints its backup directory. Substitute that exact path:

```bash
python3 scripts/config_lab.py restore '/absolute/path/to/backup-directory'
python3 scripts/config_lab.py restore '/absolute/path/to/backup-directory' --write
```

Restoration backs up the current candidate before restoring the previous bytes.
If no config existed before the original change, restoration removes only the
new config. An old broken config is restored faithfully and may break Codex
again. Do not edit or share backup contents; a previous config could contain
inline secrets.

## Repository checks and first coding trial

```bash
python3 -m unittest discover -s tests -v
python3 scripts/config_lab.py validate config/recovery.toml
python3 scripts/config_lab.py validate config/development.toml
bash -n scripts/codex-lab.sh
bash -n scripts/vscode-lab.sh
```

The tests cover restoration and configuration failure cases. They do not test
real OpenAI authentication, model availability, or your local network.

To start tracking the extracted source:

```bash
git init
git add .
git commit -m "Add Codex configuration recovery lab"
```

For a first Codex editing trial, ask it to improve one paragraph of this README,
inspect `git diff`, then decide whether to commit. The supplied source does not
contain your uploaded files or credentials. Nothing is pushed to GitHub.
