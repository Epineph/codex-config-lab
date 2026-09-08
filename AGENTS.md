# Working preferences

- Write formal, direct explanations. Separate observations from hypotheses.
- Preserve behavior unless the requested change requires changing it.
- Use two-space indentation and an 81-column limit where practical.
- Bash functions use `function name() { ...; }`, clear help and section comments.
- Prefer simple, documented interfaces over large collections of feature flags.
- Explain mathematical reasoning step by step when relevant. In R, prefer `=`
  assignments unless an interface specifically requires another form.
- Review existing changes before editing. Keep each experiment small and
  reversible. Do not publish or push without the user's instruction.
- Never inspect credential contents or include secrets in diagnostic reports.
- Do not weaken TLS verification or administrative policy to resolve a failure.
- Verify backups/restoration when changing configuration-writing behavior.
- Use a single agent for this small lab; propose parallel work only when useful.
