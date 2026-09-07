# Validation record

Prepared on 6 September 2026.

- Nine regression tests passed under Python 3.12.13. They cover broken TOML,
  misnested settings, unsupported effort values, both presets, model-ID input,
  preview with no writes, backup/restore, restoration of original file absence,
  backup corruption, symlink refusal, and lab credential-storage persistence.
- Both Bash launchers passed `bash -n` syntax checks.
- All supplied repository JSON and TOML templates parsed successfully.
- The read-only diagnostic ran against the recovery template.
- No installed Codex CLI was available in the preparation environment. Real
  Codex startup, authentication, requests, and VS Code integration were not
  exercised. Network conditions in that environment would not establish the
  condition of the user's Arch Linux machine.
- ShellCheck and shfmt were not available; their checks were not run.

The local tests establish file-handling behavior and selected syntax checks.
The user's installed client remains the compatibility and connection test.
