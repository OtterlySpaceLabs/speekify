# Speekify

Speekify turns text into a local WAV file you can listen to — from inline CLI
text, stdin, local `.txt`/`.md`/`.text`/`.pdf` files, YouTube transcripts, or the
readable content of a URL. Audio is generated locally with Supertonic v3.
Temporal runs only on your machine behind the CLI to retry and resume work
without changing the usual synchronous command experience.

## Features

| Capability | What you get |
|---|---|
| **Many input sources** | Inline text, piped stdin, local `.txt`/`.md`/`.text`/`.pdf` files, readable URLs, and YouTube transcripts — auto-detected. |
| **Local TTS** | WAV files synthesized on your machine with Supertonic v3 — no audio leaves your computer. |
| **Multilingual** | `en`, `fr`, `de`, `es`, `it`, `pt`, `ja`, `ko`, and more, plus `na` for language-agnostic synthesis. |
| **Auto-translation** | By default Speekify auto-detects the source language and synthesizes in it — no translation. English is detected and translated to French before TTS only when you pass `--lang fr`. |
| **Voice control** | 10 built-in voices (`M1`–`M5`, `F1`–`F5`), custom Voice Builder JSON styles, plus speed and synthesis-step tuning. |
| **MCP server** | Expose Speekify as a tool so AI assistants can generate audio during automations. |
| **Reliable local execution** | A loopback-only Temporal service and worker retry interrupted steps and preserve progress on local disk. |
| **Batch generation** | Generate one WAV per file, URL, text item, or supported document found recursively in a directory. |

## Install

`speekify setup` (run once after installing) downloads and warms the Supertonic
model and, by default, the English→French translation model. If you skip it, the
models download automatically on first use.

### macOS with Homebrew

Once a release is published:

```bash
brew tap otterlyspacelabs/speekify https://github.com/OtterlySpaceLabs/speekify
brew install speekify
speekify setup
```

The formula declares Temporal as a Homebrew dependency, so `brew install
speekify` installs and maintains it automatically. The current Homebrew payload
is built for Apple Silicon (`arm64`) only.

### With pip / pipx / uv

Once released on PyPI:

```bash
pip install speekify        # or: pipx install speekify  (recommended for CLIs)
speekify setup

uv tool install speekify    # uv users
speekify setup
```

No separate Temporal installation is needed for pip, pipx or uv. On the first
audio generation, Speekify downloads the pinned official Temporal CLI into its
user data directory, verifies the published SHA-256, and reuses it offline
afterward. A failed or unavailable download leaves no executable installed and
produces an actionable error. Automatic provisioning supports macOS and Linux
on `arm64` and `amd64`; Windows is not supported by the local runtime.

Run without installing:

```bash
uvx speekify "Hello world"
pipx run speekify "Hello world"
```

### From source with uv

```bash
uv sync
uv run speekify setup
```

## Quick start

Speekify is a CLI. Give it inline text, a URL, a local file path, or piped
stdin:

```bash
speekify "Hello world"                                        # inline text
speekify https://example.com/article                          # readable URL
speekify ~/Documents/article.pdf                              # local PDF
speekify --lang fr "https://www.youtube.com/watch?v=eSP7PLTXNy8"   # YouTube
printf 'Hello from stdin' | speekify                          # stdin
speekify --voice F2 --output-dir ~/Desktop "Hello world"      # pick voice + dir
speekify batch article.pdf https://example.com ./notes         # one WAV per item
```

Wrap URLs in quotes when they contain `?` or `&` (common with YouTube), or the
shell may reject the command. From a source checkout, prefix any command with
`uv run` (e.g. `uv run speekify "Hello world"`).

**→ Full command list, every option, and the config file: [docs/usage.md](docs/usage.md).**

## Transparent local runtime

Normal generation and `speekify batch` start or reconnect to the local Temporal
service automatically. It binds to `127.0.0.1`, runs headless with telemetry
disabled, and stores its SQLite state plus Speekify job receipts in the
platform user data directory. The service stays alive while a generation or
batch is active, then stops after five minutes with no client and no running
workflow. The next generation starts it again against the same data.

If a client process disappears without sending a cancellation and before its
result is acknowledged, repeating the same direct request reconnects to that
local job or reuses its completed receipt. Temporal workflows and
prepared/output artifacts also survive service restarts. `Ctrl+C` is an
explicit cancellation request, not a detach operation. There is currently no
public command for listing, inspecting, or manually administering stored jobs.

URL extraction and first-time model/runtime downloads use the network. Text,
local files, prepared content, Temporal state, and audio synthesis remain local;
Speekify does not send them to a hosted TTS or Temporal service.

## MCP automation server

Speekify ships a local Model Context Protocol (MCP) server so AI assistants can
call it as a tool. It exposes `speekify_generate_wav` (text/URL/file → WAV),
`speekify_generate_batch` (multiple sources/directories → WAV files),
`speekify_generation_defaults` (supported voices, languages, and ranges), and
a `news_recap_to_audio` prompt template.

```bash
speekify mcp                              # stdio transport for desktop AI clients
speekify mcp --transport streamable-http  # HTTP endpoint for local experiments
```

Per-client setup (Claude Code, GitHub Copilot, Codex, OpenAI remote MCP):
[docs/mcp-clients.md](docs/mcp-clients.md).

## Documentation

| Doc | Contents |
|---|---|
| [docs/usage.md](docs/usage.md) | Full CLI reference — every command, option, the config file, and output naming. |
| [docs/sources.md](docs/sources.md) | Supported input sources, extraction rules and limits, translation, storage, diagnostics, and network behavior. |
| [docs/mcp-clients.md](docs/mcp-clients.md) | MCP server setup for Claude Code, GitHub Copilot, Codex, and remote MCP. |
| [docs/release-procedure.md](docs/release-procedure.md) | Maintainer release checklist. |

## Usage and content

Speekify only fetches content you explicitly point it at, for your own personal
use. You are responsible for respecting the terms of service and copyright of any
source you extract from, including YouTube transcripts. The
maintainers provide no rights over third-party content.

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 Otterly Space SARL.
