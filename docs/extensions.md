# Add capabilities after recovery

Treat each addition as a separate experiment: change one setting, start a new
conversation, verify its purpose, and keep the working version in Git. The
backups from `apply` preserve the prior config.

## MCP

The optional docs server is in `config/optional-mcp.toml`. After basic login and
requests work, either merge its table once into the active Codex config or use:

```bash
bash scripts/codex-lab.sh mcp add openaiDeveloperDocs \
  --url https://developers.openai.com/mcp
bash scripts/codex-lab.sh mcp list
```

Do not do both: that would configure the same server twice. Check `mcp --help`
if your installed CLI uses different arguments. MCP is optional; it is not the
connection between Codex and OpenAI's model service. Codex CLI and its extension
share MCP configuration. VS Code's separate `mcp.json` has a different schema.
[OpenAI MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

The existing GitKraken integration can be restored later if you actually use
its tools and its executable exists. Re-enable browser and document-conversion
servers individually after checking their installed runtimes and authentication.
Avoid installing several servers merely to debug basic connectivity.

## Agents and memories

The repository's `AGENTS.md` expresses durable coding preferences without
requiring an orchestration plugin. It is text-based guidance, not automatic
synchronization with browser memories. Read it and adapt it to each project.

Use `codex features list` (or the lab wrapper with those arguments) to inspect
what the installed client recognizes before enabling optional features. Do not
paste a bulk flag list from a different client build. For parallel work, first
verify the current agent settings and available capabilities, then start with
one bounded independent subtask; measure usefulness before increasing concurrency.

Enable memories only if you want persistent local context for that installation.
They do not import all your ChatGPT history merely because a flag is enabled.
Keep plugin installation, hooks and memory changes separate from the baseline
recovery test. Install a single orchestration approach only when a concrete
workflow needs it.

## Zsh completion (optional)

After the ordinary CLI works, generate its completion definition:

```zsh
mkdir -p "$HOME/.local/share/zsh/site-functions"
codex completion zsh > "$HOME/.local/share/zsh/site-functions/_codex"
```

Put this before your existing completion initialization in the zsh configuration
file you already load:

```zsh
fpath=("$HOME/.local/share/zsh/site-functions" $fpath)
```

Keep your existing zinit/`compinit` setup; do not initialize completion twice.
This is optional manual setup, not something the repository appends automatically.
