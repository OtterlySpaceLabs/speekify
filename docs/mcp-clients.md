# Speekify MCP Client Setup

Speekify ships an MCP server so AI clients can generate local WAV files from
text, URLs, or local files. Once Speekify is installed (Homebrew, pip, pipx, or
`uv tool install` — see the [README](../README.md#install)), the `speekify`
command is on your `PATH`, and you connect clients with a single command:

```bash
speekify mcp                              # stdio — for local desktop clients (Claude, Codex)
speekify mcp --transport streamable-http  # HTTP endpoint at http://127.0.0.1:8000/mcp
```

> From a source checkout (no install), use `uv run speekify mcp` instead of
> `speekify mcp` everywhere below. The committed `.mcp.json`,
> `.vscode/mcp.json`, and `.codex/config.toml.example` use that `uv run` form.

**Tools exposed:** `speekify_generate_wav` (text/URL/file → WAV),
`speekify_generation_defaults` (supported voices, languages, ranges), and the
`news_recap_to_audio` prompt template.

## Connect to Claude Code

Add the installed Speekify as a local stdio server (run from anywhere):

```bash
claude mcp add --transport stdio speekify -- speekify mcp
```

Verify with `claude mcp list` / `claude mcp get speekify`, or `/mcp` inside
Claude Code.

Prefer a shared, project-scoped config? Create `.mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "speekify": { "command": "speekify", "args": ["mcp"] }
  }
}
```

## Connect to Codex

Add the installed Speekify from the Codex CLI:

```bash
codex mcp add speekify -- speekify mcp
```

Or configure it explicitly in `.codex/config.toml` (project) or
`~/.codex/config.toml` (user):

```toml
[mcp_servers.speekify]
command = "speekify"
args = ["mcp"]

# Audio generation is slower than text tools — raise the timeout.
startup_timeout_sec = 20
tool_timeout_sec = 600
```

Inspect active servers with `/mcp` in the Codex TUI.

## Other clients

### GitHub Copilot (VS Code)

Create `.vscode/mcp.json` — note the `servers` shape, not Claude's `mcpServers`:

```json
{
  "servers": {
    "speekify": { "command": "speekify", "args": ["mcp"] }
  }
}
```

Start the server from the editor action above the config, open Copilot Chat in
**Agent** mode, and confirm with `MCP: List Servers`.

### ChatGPT / OpenAI

OpenAI products attach **remote** MCP servers, not local `stdio` ones — so
Speekify can't plug into the ChatGPT UI the way Claude Code or Codex do. Run it
in HTTP mode and expose it one of two ways:

```bash
speekify mcp --transport streamable-http   # serves http://127.0.0.1:8000/mcp
```

**Option A — reachable HTTPS endpoint.** Put a reverse proxy in front of the
local HTTP server and publish a stable HTTPS URL such as
`https://speekify.example.com/mcp`. Ready examples ship in the repo:
[`examples/speekify.nginx.conf`](examples/speekify.nginx.conf) and
[`examples/Caddyfile`](examples/Caddyfile).

```caddy
speekify.example.com {
  reverse_proxy /mcp 127.0.0.1:8000
}
```

Point DNS at the proxy host and install a valid TLS certificate (Caddy
provisions TLS automatically once DNS resolves and ports 80/443 are reachable).
Then connect from the OpenAI Responses API:

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="gpt-5",
    input="Generate a short French audio recap of this text.",
    tools=[{
        "type": "mcp",
        "server_label": "speekify",
        "server_url": "https://speekify.example.com/mcp",
        "require_approval": "never",
        "allowed_tools": ["speekify_generation_defaults", "speekify_generate_wav"],
    }],
)
print(response.output_text)
```

**Option B — OpenAI Secure MCP Tunnel (keep Speekify private).** Keep Speekify
on your laptop/VM and let `tunnel-client` bridge it to OpenAI:

```bash
export CONTROL_PLANE_API_KEY="sk-..."

tunnel-client init \
  --profile speekify-http \
  --tunnel-id tunnel_0123456789abcdef0123456789abcdef \
  --mcp-server-url http://127.0.0.1:8000/mcp

tunnel-client doctor --profile speekify-http --explain   # validate
tunnel-client run --profile speekify-http                # keep running
```

For a stdio target instead of HTTP, swap `--mcp-server-url …` for
`--mcp-command "speekify mcp"`.

Then in ChatGPT: open connector settings → create a custom connector → choose
**Tunnel** → select the Speekify tunnel (or paste the `tunnel_id`) → let ChatGPT
discover `speekify_generate_wav` and `speekify_generation_defaults`. Test with a
low-risk prompt:

```text
Use the Speekify MCP tools to inspect the available defaults, then generate a short French WAV saying: Bonjour, ceci est un test audio.
```

If discovery fails: confirm `tunnel-client run` is active, `tunnel-client doctor
… --explain` is healthy, and the ChatGPT workspace is allowed to use the tunnel.

## Verify any client

Ask the assistant to call `speekify_generation_defaults` first, then a small
generation:

```json
{
  "source": "Bonjour, ceci est un test audio.",
  "title": "test-speekify-mcp",
  "language_code": "fr"
}
```

A successful call returns `output_path`, `output_uri`, and details (duration,
title, warnings, log path).

## Troubleshooting

- **Server doesn't appear:** re-run the client's add command in the same project scope; for Copilot, use the `servers` shape and start it from the editor; for Codex, ensure the project is trusted.
- **Tools discovered but calls hang or fail on long inputs:** raise client-side tool timeouts — audio generation is slower than text tools (Codex: `tool_timeout_sec = 600`).
- **Copilot tools unused in chat:** switch to **Agent** mode.
- **HTTP `404`:** the proxy is forwarding `/` instead of `/mcp`, or the public URL is missing the `/mcp` suffix.
- **HTTP `502`:** Speekify isn't running in `streamable-http` mode, or the proxy target is wrong.
- **`Connection refused`:** nothing on `127.0.0.1:8000` — restart `speekify mcp --transport streamable-http`.
- **ChatGPT can't see the tunnel:** confirm it's attached to the right workspace and `tunnel-client run` is active.
