# Speekify

Speekify turns CLI text, stdin, local `.txt`/`.md`/`.pdf` files, YouTube video transcripts, X/Twitter posts, or the readable content of a URL into a local WAV file generated with Supertonic v3.

## Install

### macOS without Python or uv

Once a release has been published, you can install the standalone binary with Homebrew or by downloading the archive directly.

Homebrew tap flow:

```bash
brew tap OtterlySpaceLabs/speekify
brew install speekify
speekify setup
```

Direct download flow:

```bash
curl -L -o speekify.tar.gz https://github.com/OtterlySpaceLabs/homebrew-speekify/releases/latest/download/speekify-macos-arm64.tar.gz
tar -xzf speekify.tar.gz
mv speekify /usr/local/bin/speekify
speekify setup
```

`speekify setup` downloads and warms the Supertonic model and, by default, the English to French translation model too.

### From source with uv

```bash
uv sync
uv run speekify setup
```

If you skip setup, the models can still download automatically on first use.

## Run

Speekify is a CLI. Provide inline text, a URL, a path to a local `.txt`/`.md`/`.pdf` file, or piped stdin. A source that points at an existing `.txt`, `.md`, `.text`, or `.pdf` file is read automatically (PDF text is extracted with `pypdf`), and the file name becomes the default output title. URL mode supports readable articles, YouTube video transcripts (English captions/transcripts when available), and public X/Twitter post text (via the public oEmbed endpoint). X articles (`x.com/<user>/article/...`), protected posts, and very short posts cannot be extracted without a logged-in session and fail with a clear error instead:

```bash
speekify "Hello world"
speekify https://example.com/article
speekify ~/Documents/article.pdf
speekify --lang fr "https://www.youtube.com/watch?v=eSP7PLTXNy8"
speekify --lang fr https://x.com/w1nklerr/status/2060057563991884060
printf 'Hello from stdin' | speekify
```

When passing a URL that contains shell-special characters such as `?` or `&` (common with YouTube URLs), wrap it in quotes. This is required in shells like `zsh`, otherwise the shell can reject the command before Speekify starts.

The CLI uses concise Rich output: progress/status indicators during longer work, a result panel when the WAV file is ready, and readable error messages. Technical log paths are shown only with `--verbose`.

### CLI commands

All examples below work with the installed binary (`speekify …`) or directly from the source tree (`uv run speekify …`). The `uv run` form is shown alongside each group.

```bash
# Generate from inline text
speekify "Hello world"
uv run speekify "Hello world"

speekify --lang fr "Hello world"
uv run speekify --lang fr "Hello world"

# Generate from a local text or PDF file (auto-detected by extension)
speekify ~/Documents/article.pdf
uv run speekify ~/Documents/notes.txt

# Generate from a URL (auto-detected or forced)
speekify https://example.com/article
uv run speekify https://example.com/article

speekify --lang fr "https://www.youtube.com/watch?v=eSP7PLTXNy8"
uv run speekify --lang fr "https://www.youtube.com/watch?v=eSP7PLTXNy8"

speekify --lang fr "https://x.com/w1nklerr/status/2060057563991884060"
uv run speekify --lang fr "https://x.com/w1nklerr/status/2060057563991884060"

speekify --url https://example.com/article
uv run speekify --url https://example.com/article

# Pipe text from stdin
printf 'Hello from stdin' | speekify
printf 'Hello from stdin' | uv run speekify

# Override output name and directory
speekify --title my-article --output-dir ~/Desktop "Hello world"
uv run speekify --title my-article --output-dir ~/Desktop "Hello world"

# Preview extraction, translation, tags, and planned paths without synthesis
speekify --dry-run https://example.com/article
uv run speekify inspect "Hello world"

# Choose a voice
speekify --voice F2 "Hello world"
uv run speekify --voice F2 "Hello world"

# Use a Supertonic Voice Builder JSON style
speekify --custom-style-path ~/voices/my-voice.json "Hello world"
uv run speekify --custom-style-path ~/voices/my-voice.json "Hello world"

# Adjust speed and synthesis steps
speekify --speed 1.2 --steps 20 "Hello world"
uv run speekify --speed 1.2 --steps 20 "Hello world"

# Tune natural narration pauses and internal chunking
speekify --lang fr --voice M5 --speed 0.98 --steps 10 --silence-duration 0.25 https://example.com/article
uv run speekify --max-chunk-length 240 --silence-duration 0.25 "Hello world"

# Download and warm up models
speekify setup
uv run speekify setup

speekify setup --skip-translation   # skip the EN→FR translation model
uv run speekify setup --skip-translation

# Show technical diagnostics when needed
speekify --verbose "Hello world"
uv run speekify --verbose "Hello world"

# Show the installed Speekify version
speekify --version
uv run speekify --version

speekify -v
uv run speekify -v

# Inspect the local runtime and dependency health
speekify --doctor
uv run speekify --doctor

# Read the manual page after installation
man speekify

# Show help
speekify --help
uv run speekify --help

speekify setup --help
uv run speekify setup --help
```

### User config

Speekify can read default generation settings from `~/.config/speekify/config.toml`. Set `SPEEKIFY_CONFIG=/path/to/config.toml` to use another file. CLI options still win over config values.

```toml
[generation]
voice = "M5"
language_code = "fr"
speed = 0.98
steps = 10
silence_duration = 0.25
output_dir = "~/Speekify/audio"
english_islands = true
# english_lexicon_path = "~/Speekify/english-terms.txt"
```

### CLI options reference

| Option | Default | Description |
|---|---|---|
| `source` | *(stdin if piped)* | Text to synthesize, a URL to extract, or a path to a local `.txt`/`.md`/`.text`/`.pdf` file. Required unless stdin is piped. |
| `--lang CODE` | `fr` | Supertonic ISO 639-1 language code. Supported: `en`, `fr`, `de`, `es`, `it`, `pt`, `nl`, `pl`, `ru`, `ja`, `ko`, `ar`, `hi`, `tr`, `uk`, `vi`, and more. Use `na` for language-agnostic synthesis. |
| `--voice NAME` | `M5` | Supertonic voice. Male: `M1`–`M5`. Female: `F1`–`F5`. |
| `--custom-style-path PATH` | — | Load a Supertonic voice-style JSON file, such as a Voice Builder export. Overrides `--voice`. |
| `--speed VALUE` | `0.98` | Playback speed multiplier (`0.7`–`2.0`). |
| `--steps N` | `10` | Number of synthesis steps (`1`–`100`). Higher values may improve quality. |
| `--max-chunk-length N` | *(auto)* | Maximum characters per internal Supertonic chunk. Leave unset for Supertonic's language-aware default. |
| `--silence-duration SECONDS` | `0.25` | Silence between Supertonic chunks. Smaller values can make long-form narration feel tighter. |
| `--english-islands / --no-english-islands` | `--english-islands` | When `--lang fr`, pronounce known English tech terms (AI, API, machine learning, ...) as English islands instead of French. |
| `--english-lexicon-path PATH` | — | Newline-delimited file of extra English terms to treat as English islands during French synthesis. Lines starting with `#` are ignored. |
| `--url` | — | Force URL extraction mode even if the source looks like plain text. |
| `--title TEXT` | *(auto)* | Override the output file name (without extension). |
| `--output-dir PATH` | `.` (current directory) | Directory where the WAV file is written. |
| `--dry-run` | disabled | Preview extraction, translation, and planned output paths without generating audio. |
| `--verbose` | disabled | Show technical diagnostics such as the log file path when a command fails. |
| `--version`, `-v` | — | Print the installed Speekify version and exit. |

Additional commands:

| Command | Description |
|---|---|
| `speekify setup` | Download and warm up the local models. |
| `speekify inspect` | Preview the generation plan without synthesis. |
| `speekify --doctor` | Verify runtime dependencies, actively load the AI models, and suggest `speekify setup` if a check fails. |

The main help output also includes a maintenance section with `speekify --version`, `speekify -v`, `speekify --doctor`, and `speekify setup` so the operational commands stay discoverable from `speekify --help`.

Installed distributions also ship a manual page. After installation through Homebrew, or from a packaged distribution that installs `share/man/man1/speekify.1`, you can use `man speekify` for a full command reference and software overview.

By default, direct CLI generation writes the WAV file into the current working directory, with names like:

```text
./article-title-20260528-183000.wav
```

## MCP automation server

Speekify also ships a local Model Context Protocol (MCP) server so AI assistants can call Speekify as a tool during automations. The server exposes:

- `speekify_generate_wav`: convert inline text, readable URL content, or a local `.txt`/`.md`/`.pdf` file (pass the file path as `source`) to a local WAV file and return structured details (`output_path`, `output_uri`, duration, title, warnings, and log path). It accepts the same generation controls as the CLI, including `english_islands`, `english_lexicon_path`, and `use_user_config`.
- `speekify_generation_defaults`: inspect supported voices, languages, and generation ranges before calling the generator.
- `news_recap_to_audio`: a prompt template for the common workflow “check news sources, summarize them, then generate WAV files for each URL and for the final recap.”

Run it with stdio transport for desktop AI clients:

```bash
speekify mcp          # installed binary (Homebrew, pip, uv)
uv run speekify mcp   # from a source checkout
```

For clients that support streamable HTTP during local experiments:

```bash
speekify mcp --transport streamable-http
uv run speekify mcp --transport streamable-http
```

Example MCP tool arguments for a recap generated by an assistant:

```json
{
  "source": "Voici le fil d'actu résumé avec les liens sources...",
  "title": "fil-actu-du-jour",
  "language_code": "fr",
  "output_dir": "./audio"
}
```

For client-specific setup instructions, including Claude Code, GitHub Copilot, Codex, and OpenAI remote MCP usage, see [docs/mcp-clients.md](docs/mcp-clients.md).

## Release for maintainers

See `docs/release-procedure.md` for the full step-by-step release checklist.

To build a standalone macOS archive and generate the Homebrew formula inputs:

```bash
./scripts/build_standalone_macos.sh
python scripts/render_homebrew_formula.py \
	--version 0.1.0 \
	--url https://github.com/OtterlySpaceLabs/homebrew-speekify/releases/download/speekify-v0.1.0/speekify-macos-arm64.tar.gz \
	--sha256 <sha256>
```

Releases are built and published entirely locally — there is no GitHub Actions build. See [docs/release-procedure.md](docs/release-procedure.md) for the full step-by-step procedure.

## Notes

- The app uses `supertonic-3` by default.
- The direct CLI defaults to French narration (`fr`) with voice `M5`, speed `0.98`, `10` synthesis steps, and `0.25 s` chunk silence. It accepts only Supertonic-supported ISO 639-1 language codes such as `en`, `fr`, `ja` or `ko`, plus `na` for language-agnostic synthesis.
- When French synthesis is used, including the default, English inputs are auto-detected and translated to French before TTS with `Helsinki-NLP/opus-mt-en-fr`.
- URL mode extracts readable body text rather than raw HTML.
- X/Twitter extraction only works for public posts exposed through the public oEmbed endpoint. X articles, protected accounts, and posts whose text is too short are reported as extraction errors because they would require a logged-in session.
- A single URL is auto-detected and extracted unless `--url` is needed to force URL mode.
- A source that resolves to an existing `.txt`, `.md`, `.text`, or `.pdf` file is read automatically; the file name becomes the default title. PDF text is extracted with `pypdf` (text-based PDFs only — scanned/image PDFs with no text layer yield nothing). `--url` skips file detection.
- Input text is cleaned permissively before synthesis: Supertonic preprocessing is reused, unsupported characters are removed automatically, and the CLI summarizes the cleanup after generation.
- Supertonic handles normal long-text chunking internally. Very large inputs above the SDK text limit are split into external batches automatically and merged into one final WAV file.
- The steps control follows the SDK range `1..100`, with `10` as the default.
- If generation fails, the terminal shows a short user-focused error. Add `--verbose` to include the technical log path (`logs/speekify.log`).
- Each CLI run maintains `logs/speekify.log` automatically and prunes log entries older than 14 days at startup.

## Usage and content

Speekify only fetches content you explicitly point it at, for your own personal use. You are responsible for respecting the terms of service and copyright of any source you extract from, including YouTube transcripts and X/Twitter posts. The maintainers provide no rights over third-party content.

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 Otterly Space SARL.
