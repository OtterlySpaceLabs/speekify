# Speekify

Speekify turns text into a local WAV file you can listen to — from inline CLI
text, stdin, local `.txt`/`.md`/`.pdf` files, YouTube transcripts, X/Twitter
posts, or the readable content of a URL. Audio is generated locally with
Supertonic v3.

## Features

| Capability | What you get |
|---|---|
| **Many input sources** | Inline text, piped stdin, local `.txt`/`.md`/`.pdf` files, readable URLs, YouTube transcripts, and public X/Twitter posts — auto-detected. |
| **Local TTS** | WAV files synthesized on your machine with Supertonic v3 — no audio leaves your computer. |
| **Multilingual** | `en`, `fr`, `de`, `es`, `it`, `pt`, `ja`, `ko`, and more, plus `na` for language-agnostic synthesis. |
| **Auto-translation** | English input is detected and translated to French before TTS when synthesizing in French (the default). |
| **Voice control** | 10 built-in voices (`M1`–`M5`, `F1`–`F5`), custom Voice Builder JSON styles, plus speed and synthesis-step tuning. |
| **MCP server** | Expose Speekify as a tool so AI assistants can generate audio during automations. |

## Install

`speekify setup` (run once after installing) downloads and warms the Supertonic
model and, by default, the English→French translation model. If you skip it, the
models download automatically on first use.

### macOS — no Python or uv required

Once a release is published, install the standalone binary via Homebrew:

```bash
brew tap OtterlySpaceLabs/speekify
brew install speekify
speekify setup
```

Or download the archive directly:

```bash
curl -L -o speekify.tar.gz https://github.com/OtterlySpaceLabs/homebrew-speekify/releases/latest/download/speekify-macos-arm64.tar.gz
tar -xzf speekify.tar.gz
mv speekify /usr/local/bin/speekify
speekify setup
```

### With pip / pipx / uv

Once released on PyPI:

```bash
pip install speekify        # or: pipx install speekify  (recommended for CLIs)
speekify setup

uv tool install speekify    # uv users
speekify setup
```

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
```

Wrap URLs in quotes when they contain `?` or `&` (common with YouTube), or the
shell may reject the command. From a source checkout, prefix any command with
`uv run` (e.g. `uv run speekify "Hello world"`).

**→ Full command list, every option, and the config file: [docs/usage.md](docs/usage.md).**

## MCP automation server

Speekify ships a local Model Context Protocol (MCP) server so AI assistants can
call it as a tool. It exposes `speekify_generate_wav` (text/URL/file → WAV with
structured details), `speekify_generation_defaults` (supported voices, languages,
and ranges), and a `news_recap_to_audio` prompt template.

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
| [docs/sources.md](docs/sources.md) | Supported input sources, extraction rules and limits, translation, text handling, and logs. |
| [docs/mcp-clients.md](docs/mcp-clients.md) | MCP server setup for Claude Code, GitHub Copilot, Codex, and remote MCP. |
| [docs/release-procedure.md](docs/release-procedure.md) | Maintainer release checklist. |

## Usage and content

Speekify only fetches content you explicitly point it at, for your own personal
use. You are responsible for respecting the terms of service and copyright of any
source you extract from, including YouTube transcripts and X/Twitter posts. The
maintainers provide no rights over third-party content.

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 Otterly Space SARL.
