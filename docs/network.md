# Distinguish configuration, login, and upload failures

The upload error names `files.oaiusercontent.com`. That browser request is
outside Codex's shell sandbox. Editing `sandbox_workspace_write.network_access`
cannot fix a browser's DNS, proxy, TLS or filtering failure.

The diagnostic probes are deliberately unauthenticated requests to site roots.
They neither upload files nor reproduce the signed upload URL. A server can
reject a root URL even when real uploads work.

| Result | Interpretation / next step |
| --- | --- |
| TOML parse error | Resolve configuration first; authentication may never have started |
| curl exit 5 or 6 | Proxy/host name resolution failed; investigate configured DNS/proxy |
| curl exit 7 | Connection failed; investigate reachability, firewall or proxy |
| curl exit 28 | Timeout; could involve DNS, routing, proxy or server response |
| curl exit 35 or 60 | TLS handshake or certificate validation failed |
| HTTP 401, 403, 404 or 405 with curl exit 0 | An HTTP response arrived; not proof that login/upload is allowed |
| IPv4 works; IPv6 alone fails | IPv6 path deserves investigation; absent IPv6 can also be normal |
| Lab works, ordinary clients fail | Existing configuration/state becomes the main suspect |
| CLI works, isolated VS Code fails | Inspect extension version, logs and effective Codex config path |
| Browser uploads fail but Codex works | Focus on browser/upload path |

A proxy can generate its own HTTP error, so an HTTP response does not always
prove the intended origin was reached. Curl can use a different proxy, DNS or
certificate configuration from a browser or the Codex extension. Its `-q`
option ignores `.curlrc`; its environment proxy settings still apply.

A practical comparison sequence:

1. Retry one small text upload in a private browser window, checking whether
   any extensions are allowed there. If that works, inspect browser extensions
   or site data before changing system networking.
2. Compare the same computer on a mobile hotspot. Success there implicates the
   original network path; failure does not identify one specific cause.
3. Check whether a VPN, custom DNS filter, local proxy or network security
   product was recently changed. Record the original setting before a temporary
   comparison. On an administered network, use the administrator's process.
4. For TLS errors, check the system clock (`timedatectl status`) and the trusted
   CA configuration. Do not use `curl -k` or disable TLS verification as a fix.
5. Inspect the failed request in browser Developer Tools → Network. Record the
   hostname, status and error, not signed URL query strings or cookies.
6. Check the live OpenAI service status in your browser if both configuration
   and network tests are inconclusive. This package makes no claim about a
   currently active service incident.

A legitimate TLS-inspecting proxy may require an approved CA bundle. OpenAI
supports `CODEX_CA_CERTIFICATE`, falling back to `SSL_CERT_FILE`. Use a CA file
provided by the responsible administrator, not an arbitrary downloaded
certificate. [Authentication and custom CAs](https://learn.chatgpt.com/docs/auth)

If the diagnostic says proxy/base-URL/CA variables are set, inspect those values
locally. Do not publish a full `env` dump; proxy URLs can contain credentials.
A GUI application may have inherited a different environment from your current
terminal. Close and relaunch the lab editor when comparing environment changes.

To obtain raw local file text without the formatting damage in the attachment:

```bash
cat -- "$HOME/.codex/config.toml"
```

Inspect and redact inline tokens before sharing any configuration. Never attach
`~/.codex/auth.json`. For the next troubleshooting step, the short diagnostic
report and exact redacted error are usually more useful than another full dump.
