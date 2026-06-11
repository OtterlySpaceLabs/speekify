# Speekify

Speekify turns CLI text, stdin, YouTube video transcripts, X/Twitter posts, or the readable content of a URL into a local WAV file generated with Supertonic v3.

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

`speekify setup` downloads and warms the Supertonic model, the CardiffNLP emotion/sentiment model used by default speech tagging, and, by default, the English to French translation model too.

### From source with uv

```bash
uv sync
uv run speekify setup
```

If you skip setup, the models can still download automatically on first use.

## Run

Speekify is a CLI. Provide inline text, a URL, or piped stdin. URL mode supports readable articles, YouTube video transcripts (English captions/transcripts when available), and public X/Twitter post text (via the public oEmbed endpoint). X articles (`x.com/<user>/article/...`), protected posts, and very short posts cannot be extracted without a logged-in session and fail with a clear error instead:

```bash
speekify "Hello world"
speekify https://example.com/article
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

# Generate a feed for a synced/static HTTPS podcast directory
speekify --output-dir ~/Speekify/audio \
  --feed-base-url https://audio.example.com/speekify \
  https://example.com/article

# Preview extraction, translation, tags, and planned paths without synthesis
speekify --dry-run https://example.com/article
uv run speekify inspect "Hello world"

# Rebuild or validate the podcast RSS feed from existing sidecars
speekify feed rebuild --output-dir ~/Speekify/audio
uv run speekify feed validate --output-dir ~/Speekify/audio

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

# Control sparse inline speech tags and emotion tagging
speekify --no-tags "Hello world"
uv run speekify --no-tag-sentiment --no-tag-sigh --lang fr https://example.com/article

# Download and warm up models
speekify setup
uv run speekify setup

speekify setup --skip-translation   # skip the EN→FR translation model
uv run speekify setup --skip-translation

speekify setup --skip-sentiment     # skip the emotion/sentiment model
uv run speekify setup --skip-sentiment

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
feed_base_url = "https://audio.example.com/speekify"
tags = true
tag_sentiment = true
tag_sigh = true
english_islands = true
# english_lexicon_path = "~/Speekify/english-terms.txt"
```

### CLI options reference

| Option | Default | Description |
|---|---|---|
| `source` | *(stdin if piped)* | Text to synthesize or a URL to extract. Required unless stdin is piped. |
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
| `--feed-base-url URL` | `SPEEKIFY_FEED_BASE_URL` or local file URLs | Public `http://` or `https://` directory URL used for RSS enclosure URLs, for example after syncing the output directory to static hosting. |
| `--dry-run` | disabled | Preview extraction, translation, tags, and planned output paths without generating audio. |
| `--tags / --no-tags` | `--tags` | Add sparse Supertonic inline speech tags, mainly `<breath>`. |
| `--tag-sentiment / --no-tag-sentiment` | `--tag-sentiment` | Use CardiffNLP sentiment signals when placing speech tags. Falls back to rules if unavailable. |
| `--tag-sigh / --no-tag-sigh` | `--tag-sigh` | Allow very rare `<sigh>` tags when sentiment and rules strongly agree. |
| `--verbose` | disabled | Show technical diagnostics such as the log file path when a command fails. |
| `--version`, `-v` | — | Print the installed Speekify version and exit. |

Additional commands:

| Command | Description |
|---|---|
| `speekify setup` | Download and warm up the local models. |
| `speekify inspect` | Preview the generation plan without synthesis. |
| `speekify feed rebuild` | Rebuild `speekify-feed.xml` from existing JSON sidecars. |
| `speekify feed validate` | Check JSON sidecars and referenced WAV files. |
| `speekify --doctor` | Verify runtime dependencies, actively load the AI models, and suggest `speekify setup` if a check fails. |

The main help output also includes a maintenance section with `speekify --version`, `speekify -v`, `speekify --doctor`, and `speekify setup` so the operational commands stay discoverable from `speekify --help`.

Installed distributions also ship a manual page. After installation through Homebrew, or from a packaged distribution that installs `share/man/man1/speekify.1`, you can use `man speekify` for a full command reference and software overview.

By default, direct CLI generation writes the WAV file into the current working directory, with names like:

```text
./article-title-20260528-183000.wav
```

Each WAV now gets a parallel JSON sidecar with the same stem, for example
`./article-title-20260528-183000.json`. The sidecar records the source mode/URL,
extracted title, generated audio file, duration, byte size, language, voice, speed,
steps, chunk settings, and podcast enclosure metadata. Speekify also refreshes
`./speekify-feed.xml` in the output directory as a small personal podcast-style RSS
feed. By default the feed uses local `file://` enclosures for desktop tools and future
local interfaces. For a real podcast app on another device, put the output directory
somewhere reachable by HTTP(S) and run Speekify with `--feed-base-url` (or set
`SPEEKIFY_FEED_BASE_URL`) so the RSS `<enclosure>` URLs point at that synced/static
location.

Typical consultation/sync patterns:

1. **Same machine:** open the WAV files directly or index the JSON sidecars from a
   local UI.
2. **Same Wi-Fi or VPN:** run `python -m http.server 8000` inside the output
   directory and subscribe from a podcast app to
   `http://<computer-ip>:8000/speekify-feed.xml`. This only works while the computer
   is reachable.
3. **All devices:** sync/upload the output directory to static HTTPS hosting such as
   a small VPS, S3/R2-compatible bucket, Tailscale Serve/Funnel, or another web
   server, then pass the public directory as `--feed-base-url`. Subscribe to
   `<base-url>/speekify-feed.xml` in a podcast app.

Podcast apps generally need the RSS feed and every WAV enclosure URL to be reachable
from the device. A Dropbox/iCloud/Syncthing folder is useful for moving the files,
but it still needs an HTTP(S) serving layer if you want standard podcast apps to
stream episodes.

## MCP automation server

Speekify also ships a local Model Context Protocol (MCP) server so AI assistants can call Speekify as a tool during automations. The server exposes:

- `speekify_generate_wav`: convert inline text or readable URL content to a local WAV file and return structured metadata (`output_path`, `output_uri`, sidecar/feed paths, duration, title, warnings, and log path). It accepts the same generation controls as the CLI, including `feed_base_url`, `english_islands`, `english_lexicon_path`, and `use_user_config`.
- `speekify_generation_defaults`: inspect supported voices, languages, and generation ranges before calling the generator.
- `news_recap_to_audio`: a prompt template for the common workflow “check news sources, summarize them, then generate WAV files for each URL and for the final recap.”

Run it with stdio transport for desktop AI clients:

```bash
speekify-mcp
uv run speekify-mcp
```

For clients that support streamable HTTP during local experiments:

```bash
speekify-mcp --transport streamable-http
uv run speekify-mcp --transport streamable-http
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

The GitHub Actions workflow in `.github/workflows/release.yml` automates the same release packaging on tag pushes.

## Notes

- The app uses `supertonic-3` by default.
- The direct CLI defaults to French narration (`fr`) with voice `M5`, speed `0.98`, `10` synthesis steps, and `0.25 s` chunk silence. It accepts only Supertonic-supported ISO 639-1 language codes such as `en`, `fr`, `ja` or `ko`, plus `na` for language-agnostic synthesis.
- When French synthesis is used, including the default, English inputs are auto-detected and translated to French before TTS with `Helsinki-NLP/opus-mt-en-fr`.
- Speech tagging runs after optional translation and before synthesis, so tags apply to the final TTS text. By default it combines rules-based `<breath>` placement with CardiffNLP sentiment and rare `<sigh>` tags. Use `--no-tag-sentiment --no-tag-sigh` for rules-only tagging.
- `speekify setup` warms the CardiffNLP sentiment model used by the default emotion tagging. Use `setup --skip-sentiment` only if you want to skip that download during setup.
- `<breath>` is the primary inline tag. `<sigh>` is enabled by default but remains rare and capped.
- URL mode extracts readable body text rather than raw HTML.
- X/Twitter extraction only works for public posts exposed through the public oEmbed endpoint. X articles, protected accounts, and posts whose text is too short are reported as extraction errors because they would require a logged-in session.
- A single URL is auto-detected and extracted unless `--url` is needed to force URL mode.
- Input text is cleaned permissively before synthesis: Supertonic preprocessing is reused, unsupported characters are removed automatically, and the CLI summarizes the cleanup after generation.
- Supertonic handles normal long-text chunking internally. Very large inputs above the SDK text limit are split into external batches automatically and merged into one final WAV file.
- The steps control follows the SDK range `1..100`, with `10` as the default.
- If generation fails, the terminal shows a short user-focused error. Add `--verbose` to include the technical log path (`logs/speekify.log`).
- Each CLI run maintains `logs/speekify.log` automatically and prunes log entries older than 14 days at startup.
