# Speekify MCP Client Setup

Speekify ships an MCP server so AI clients can generate local WAV files from inline text or readable URLs. Start it with the `mcp` subcommand:

- `speekify mcp` — any installed binary (Homebrew, pip, or uv).
- `uv run speekify mcp` — from a source checkout.

Add `--transport streamable-http` for clients that need an HTTP endpoint instead of `stdio`.

## What Speekify exposes

- `speekify_generate_wav`: generate a WAV file from inline text or URL content.
- `speekify_generation_defaults`: inspect supported voices, languages, and default generation settings.
- `news_recap_to_audio`: prompt template for summarizing sources and generating audio recaps.

## Prerequisites

- Install the project dependencies with `uv sync --group dev` when working from source.
- Verify the MCP server starts locally with `uv run speekify mcp`.
- Use `speekify mcp` directly once Speekify is installed on your `PATH`.

By default Speekify uses the `stdio` transport, which is the correct choice for local desktop clients. Use `--transport streamable-http` only for clients that require a remote or HTTP MCP endpoint.

Ready-to-use examples are included in this repository:

- `.mcp.json` for Claude Code project scope.
- `.vscode/mcp.json` for GitHub Copilot in VS Code.
- `.codex/config.toml.example` for Codex project or user config.

## Which file for which client?

| Client | File to use | Scope | Notes |
| --- | --- | --- | --- |
| Claude Code | `.mcp.json` | Project | Shared repo config for Claude Code MCP servers. |
| GitHub Copilot | `.vscode/mcp.json` | Project | VS Code MCP config consumed by Copilot Chat in Agent mode. |
| Codex | `.codex/config.toml.example` | Project or user template | Copy to `.codex/config.toml` or `~/.codex/config.toml`. |
| ChatGPT / OpenAI | No local config file in this repo | Remote or tunnel | Use a remote HTTPS MCP endpoint or OpenAI Secure MCP Tunnel. |

## Claude Code

Claude Code supports both local `stdio` servers and remote HTTP MCP servers. For Speekify, the simplest setup is a local `stdio` server.

Add Speekify from the repository root:

```bash
claude mcp add --transport stdio speekify -- uv run speekify mcp
```

If Speekify is installed globally (Homebrew/standalone binary):

```bash
claude mcp add --transport stdio speekify -- speekify mcp
```

Useful follow-ups:

```bash
claude mcp list
claude mcp get speekify
```

Inside Claude Code, use `/mcp` to confirm the server is connected.

Project-scoped JSON example:

```json
{
  "mcpServers": {
    "speekify": {
      "command": "uv",
      "args": ["run", "speekify", "mcp"]
    }
  }
}
```

Save that as `.mcp.json` at the repository root if you want a shared project configuration.

This repository already includes a ready-to-use example at `.mcp.json`.

## GitHub Copilot

GitHub Copilot in VS Code supports MCP servers through `.vscode/mcp.json` or your user settings. For a repo-local setup, create `.vscode/mcp.json`:

```json
{
  "servers": {
    "speekify": {
      "command": "uv",
      "args": ["run", "speekify", "mcp"]
    }
  }
}
```

If Speekify is installed on your `PATH` (Homebrew, pip, or uv), you can skip `uv run`:

```json
{
  "servers": {
    "speekify": {
      "command": "speekify",
      "args": ["mcp"]
    }
  }
}
```

Then:

1. Open the MCP config in VS Code.
2. Start the server from the editor action shown above the config.
3. Open Copilot Chat in `Agent` mode.
4. Use the tools panel or `MCP: List Servers` to verify that `speekify` is running.

This repository already includes a ready-to-use example at `.vscode/mcp.json`.

## Codex

Codex supports both local `stdio` servers and remote streamable HTTP servers. For local development, use `stdio`.

CLI setup:

```bash
codex mcp add speekify -- uv run speekify mcp
```

If Speekify is installed globally (Homebrew/standalone binary):

```bash
codex mcp add speekify -- speekify mcp
```

You can also configure Codex explicitly in `.codex/config.toml` or `~/.codex/config.toml`:

```toml
[mcp_servers.speekify]
command = "uv"
args = ["run", "speekify", "mcp"]
```

In the Codex TUI, use `/mcp` to inspect active servers.

This repository includes `.codex/config.toml.example` as a starting point for either `.codex/config.toml` in the repo or `~/.codex/config.toml` in your user profile.

## ChatGPT and OpenAI products

There is an important limitation here: the OpenAI MCP documentation currently describes remote MCP servers and connectors for OpenAI products, not direct local `stdio` attachment from the ChatGPT UI.

That means Speekify cannot be plugged into ChatGPT as a local `stdio` server in the same way as Claude Code, Codex, or GitHub Copilot.

You have two viable options:

1. Expose Speekify as a remote MCP endpoint.
2. Keep Speekify private and place a tunnel or proxy in front of it.

For local experiments, Speekify can start in HTTP mode with:

```bash
uv run speekify mcp --transport streamable-http
```

Once that server is reachable through a stable URL, you can connect it from OpenAI tooling that supports remote MCP by pointing the MCP tool at that URL. At the API level, the integration shape is a remote MCP server passed as an `mcp` tool with a `server_url`.

### Option A: expose Speekify as a reachable HTTP MCP server

Run Speekify in HTTP mode on a host that OpenAI products can reach:

```bash
uv run speekify mcp --transport streamable-http
```

With the current FastMCP defaults used by Speekify, that exposes the MCP endpoint on `http://127.0.0.1:8000/mcp`.

In practice, you would usually put a reverse proxy or edge tunnel in front of that local service and publish a stable HTTPS endpoint such as `https://speekify.example.com/mcp`.

Minimal Nginx reverse proxy example:

```nginx
server {
  listen 443 ssl http2;
  server_name speekify.example.com;

  ssl_certificate /etc/letsencrypt/live/speekify.example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/speekify.example.com/privkey.pem;

  location /mcp {
    proxy_pass http://127.0.0.1:8000/mcp;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
  }
}
```

The same example is included as `docs/examples/speekify.nginx.conf`.

TLS/DNS note: point the DNS record for `speekify.example.com` at the reverse proxy host, and install a valid TLS certificate there before exposing the endpoint publicly.

Shorter Caddy example:

```caddy
speekify.example.com {
  reverse_proxy /mcp 127.0.0.1:8000
}
```

The same example is included as `docs/examples/Caddyfile`.

TLS/DNS note: Caddy can provision TLS automatically once `speekify.example.com` resolves to the machine running Caddy and ports 80/443 are reachable.

OpenAI Responses API example:

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    input="Generate a short French audio recap of this text.",
    tools=[
        {
            "type": "mcp",
            "server_label": "speekify",
            "server_url": "https://speekify.example.com/mcp",
            "require_approval": "never",
            "allowed_tools": ["speekify_generation_defaults", "speekify_generate_wav"],
        }
    ],
)

print(response.output_text)
```

For ChatGPT custom connectors or other OpenAI surfaces that support remote MCP, the same requirement applies: the endpoint must be reachable as a remote MCP server.

### Option B: keep Speekify private with OpenAI Secure MCP Tunnel

If Speekify must stay on your laptop, VM, or private network, run it locally and let `tunnel-client` bridge outbound to OpenAI.

1. Start or prepare the local MCP server that `tunnel-client` can reach.
2. Create a tunnel in OpenAI Platform tunnel settings.
3. Run `tunnel-client` on the same machine or private network.

Concrete stdio profile example:

```bash
export CONTROL_PLANE_API_KEY="sk-..."

tunnel-client init \
  --sample sample_mcp_stdio_local \
  --profile speekify-local \
  --tunnel-id tunnel_0123456789abcdef0123456789abcdef \
  --mcp-command "uv run speekify mcp"

tunnel-client doctor --profile speekify-local --explain
tunnel-client run --profile speekify-local
```

If you prefer to run Speekify in HTTP mode behind the tunnel client instead, use an MCP server URL instead of a command:

```bash
export CONTROL_PLANE_API_KEY="sk-..."

tunnel-client init \
  --profile speekify-http \
  --tunnel-id tunnel_0123456789abcdef0123456789abcdef \
  --mcp-server-url http://127.0.0.1:8000/mcp

tunnel-client doctor --profile speekify-http --explain
tunnel-client run --profile speekify-http
```

With that setup, ChatGPT can use the tunnel-backed connector without the Speekify server being publicly exposed.

### ChatGPT connector setup, step by step

Use this path when you want ChatGPT to reach a private Speekify server through OpenAI Secure MCP Tunnel.

1. Start the local MCP server or confirm the tunnel client can start it itself.

For a local HTTP target, run:

```bash
uv run speekify mcp --transport streamable-http
```

2. In OpenAI Platform, open tunnel settings and create a tunnel. Copy the resulting `tunnel_id`.

3. On the machine that can reach Speekify, initialize the tunnel client profile:

```bash
export CONTROL_PLANE_API_KEY="sk-..."

tunnel-client init \
  --profile speekify-http \
  --tunnel-id tunnel_0123456789abcdef0123456789abcdef \
  --mcp-server-url http://127.0.0.1:8000/mcp
```

4. Validate the profile before exposing it to ChatGPT:

```bash
tunnel-client doctor --profile speekify-http --explain
```

5. Keep the tunnel client running:

```bash
tunnel-client run --profile speekify-http
```

6. Open ChatGPT connector settings and create a custom connector.

7. Choose `Tunnel` as the connection method.

8. Select the Speekify tunnel or paste the `tunnel_id`.

9. Let ChatGPT discover the tools. You should see `speekify_generate_wav` and `speekify_generation_defaults`.

10. Test with a low-risk prompt first, for example asking ChatGPT to inspect defaults before generating audio.

Suggested first prompt:

```text
Use the Speekify MCP tools to inspect the available defaults, then generate a short French WAV saying: Bonjour, ceci est un test audio.
```

If discovery fails, check three things first:

- `tunnel-client run` is still active.
- `tunnel-client doctor --profile speekify-http --explain` reports a healthy profile.
- The ChatGPT workspace has permission to use the selected tunnel.

Practical implication: document ChatGPT support as remote MCP support, not as direct local desktop MCP support.

## Quick verification prompt

After connecting Speekify in any supported client, ask the assistant to call `speekify_generation_defaults` first, then try a small generation request such as:

```json
{
  "source": "Bonjour, ceci est un test audio.",
  "title": "test-speekify-mcp",
  "language_code": "fr"
}
```

If the tool succeeds, it should return an `output_path`, an `output_uri`, and generation details (duration, title, warnings, and log path).

## Troubleshooting

### Common checks for any MCP client

- Verify the server starts locally with `uv run speekify mcp` for `stdio` clients.
- Verify HTTP mode is reachable with `uv run speekify mcp --transport streamable-http`, which exposes `http://127.0.0.1:8000/mcp` by default.
- Call `speekify_generation_defaults` before `speekify_generate_wav` to confirm tool discovery works before testing audio generation.
- If a client discovers the server but tool calls hang, increase client-side tool timeouts because audio generation is slower than simple text tools.

### Claude Code

- Symptom: `claude mcp list` does not show `speekify`.
  Check that the command was added with `claude mcp add --transport stdio speekify -- uv run speekify mcp` and that you are in the same project scope you used during setup.
- Symptom: the server appears as pending or rejected.
  Open Claude Code interactively and approve the project-scoped `.mcp.json` entry.
- Symptom: tool calls fail immediately.
  Run `claude mcp get speekify` and verify the configured command still resolves on your machine.

### GitHub Copilot

- Symptom: the server never appears in Copilot Chat.
  Open `.vscode/mcp.json`, click the `Start` action in the editor, then verify with `MCP: List Servers`.
- Symptom: the config exists but the server will not start.
  Confirm the repository uses `.vscode/mcp.json` with the `servers` shape, not Claude's `.mcp.json` `mcpServers` shape.
- Symptom: tools are available but not used in chat.
  Switch Copilot Chat to `Agent` mode, because MCP tools are not exposed the same way in non-agent chat modes.

### Codex

- Symptom: `/mcp` does not show `speekify`.
  Re-add the server with `codex mcp add speekify -- uv run speekify mcp` or move the example config into `.codex/config.toml` or `~/.codex/config.toml`.
- Symptom: the server is detected but generation fails on longer calls.
  Raise `tool_timeout_sec` in the Codex config. The example file already uses `600` seconds as a safer default for audio generation.
- Symptom: a project config is ignored.
  Make sure the project is trusted, since Codex only loads project-scoped config from trusted projects.

### ChatGPT and OpenAI

- Symptom: ChatGPT cannot see the connector or tunnel.
  Confirm the tunnel is attached to the correct workspace and that the workspace has permission to use it.
- Symptom: ChatGPT sees the tunnel but tool discovery fails.
  Keep `tunnel-client run --profile speekify-http` active and re-run `tunnel-client doctor --profile speekify-http --explain`.
- Symptom: remote MCP via HTTPS fails while local HTTP works.
  Check that your reverse proxy publishes the exact `/mcp` path and forwards to `http://127.0.0.1:8000/mcp`.
- Symptom: Responses API can reach the server but calls require repeated approvals.
  That is expected unless you set `require_approval` accordingly in the OpenAI MCP tool definition.

### HTTP and proxy errors

- `404 Not Found`: the proxy is usually forwarding `/` instead of `/mcp`, or the public URL is missing the `/mcp` suffix.
- `502 Bad Gateway`: Speekify is not running in `streamable-http` mode, or the proxy target is wrong.
- `Connection refused`: nothing is listening on `127.0.0.1:8000`; restart `uv run speekify mcp --transport streamable-http`.
- Long-running requests terminate early: increase proxy read timeouts and client tool timeouts to accommodate generation time.

## Client support summary

| Client | Local `stdio` | Remote HTTP MCP | Recommended Speekify setup |
| --- | --- | --- | --- |
| Claude Code | Yes | Yes | `uv run speekify mcp` |
| GitHub Copilot | Yes | Client-managed via MCP config | `.vscode/mcp.json` with `uv run speekify mcp` |
| Codex | Yes | Yes | `codex mcp add speekify -- uv run speekify mcp` |
| ChatGPT / OpenAI | No direct local UI flow documented | Yes | `speekify mcp --transport streamable-http` behind a reachable URL |