# Speekify CLI Reference

Full reference for the `speekify` command: every example, every option, the
config file, the maintenance commands, and where output lands. For a quick
overview and install steps, see the [README](../README.md).

All examples work with the installed binary (`speekify …`) or directly from a
source checkout (`uv run speekify …`). The `uv run` form is shown alongside
each group.

> **Quoting URLs:** when a URL contains shell-special characters such as `?` or
> `&` (common with YouTube URLs), wrap it in quotes. This is required in shells
> like `zsh`, otherwise the shell can reject the command before Speekify starts.

The CLI uses concise Rich output: progress/status indicators during longer
work, a result panel when the WAV file is ready, and readable error messages.
Technical runtime log paths are shown with `--verbose`; redacted workflow
reports are also shown when one is created.

## Commands

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

speekify --url https://example.com/article
uv run speekify --url https://example.com/article

# Pipe text from stdin
printf 'Hello from stdin' | speekify
printf 'Hello from stdin' | uv run speekify

# Generate one WAV per item; directories are expanded recursively
speekify batch article.pdf https://example.com ~/Documents/notes
uv run speekify batch ./documents

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

## Options

| Option | Default | Description |
|---|---|---|
| `source` | *(stdin if piped)* | Text to synthesize, a URL to extract, or a path to a local `.txt`/`.md`/`.text`/`.pdf` file. Required unless stdin is piped. |
| `--lang CODE` | `auto` (auto-detect) | Supertonic ISO 639-1 language code. Omit to auto-detect the source language and synthesize in it with no translation; falls back to `na` (language-agnostic) when the language can't be detected. Pass `--lang fr` to translate English input to French before TTS. Supported: `en`, `ko`, `ja`, `ar`, `bg`, `cs`, `da`, `de`, `el`, `es`, `et`, `fi`, `fr`, `hi`, `hr`, `hu`, `id`, `it`, `lt`, `lv`, `nl`, `pl`, `pt`, `ro`, `ru`, `sk`, `sl`, `sv`, `tr`, `uk`, `vi`, and `na`. |
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

Temporal is intentionally not exposed as a CLI option. Normal generation
starts or reconnects to the local reliability runtime automatically, displays
Rich progress, waits for completion, then prints the final WAV path.
Homebrew owns the Temporal dependency through the formula. For pip/pipx/uv,
the first generation downloads a pinned official binary automatically into the
Speekify data directory and verifies its SHA-256. Later runs work offline; no
manual runtime installation is required. Automatic provisioning supports
macOS and Linux on `arm64` and `amd64`; Windows is not supported.

The local service binds only to `127.0.0.1:7233`, runs headless with Temporal
telemetry/newsfeed and inherited `OTEL_*` exporters disabled, and keeps its
SQLite state on disk. It stays running while a client generation/batch or a
Temporal workflow is active. When both are absent for five minutes, it stops
automatically. A later generation restarts it against the same database.

## Batch generation

`speekify batch SOURCE...` accepts files, URLs, inline text items and
directories. Directories are traversed recursively in stable path order.
Supported documents are `.txt`, `.md`, `.text` and `.pdf`; symlinks are not
followed. Explicit symlinks and explicitly supplied unsupported files are
rejected; unsupported or symbolic entries discovered inside a directory are
skipped with a warning. Duplicate sources are processed once. A batch accepts
at most 1,000 unique items and each file is limited to 50 MiB.

Up to four item workflows may be in flight; the preparation worker runs at most
two activities concurrently, and synthesis is serialized through one local
audio worker. The command waits for every item, keeps successful outputs when
another item fails, and returns a non-zero status if at least one item failed.

## Maintenance commands

| Command | Description |
|---|---|
| `speekify setup` | Download and warm up the local models. |
| `speekify inspect` | Preview the generation plan without synthesis. |
| `speekify --doctor` | Verify dependencies and runtime support, actively load the AI models, and suggest `speekify setup` if a check fails. It reports whether Temporal is installed or can be provisioned but does not download it. |

The main help output also includes a maintenance section with
`speekify --version`, `speekify -v`, `speekify --doctor`, and `speekify setup`
so the operational commands stay discoverable from `speekify --help`.

Installed distributions also ship a manual page. After installation through
Homebrew, or from a packaged distribution that installs
`share/man/man1/speekify.1`, run `man speekify` for a full command reference and
software overview.

## Config file

Speekify can read default generation settings from
`~/.config/speekify/config.toml`. Set `SPEEKIFY_CONFIG=/path/to/config.toml` to
use another file. CLI options still win over config values.

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

## Output location

By default, direct CLI generation writes the WAV file into the current working
directory. Durable generation uses the submission time plus a short internal
job suffix, for example:

```text
./article-title-20260730-183000-a1b2c3d4e5.wav
```

Use `--title` to override the file name and `--output-dir` to change the
destination.

Ordinary successful runs do not create or display a diagnostic log. On an
error, synthesis warning, reused prepared/audio artifact, or `--verbose` run, Speekify
creates a redacted report under the local Speekify data directory and prints
its exact path.

## Local storage, recovery, and network boundaries

The data directory is:

- macOS: `~/Library/Application Support/Speekify`
- Linux and other POSIX systems:
  `${XDG_DATA_HOME:-~/.local/share}/speekify`
- override: `SPEEKIFY_DATA_DIR=/path/to/data`

It contains the managed Temporal CLI for pip-family installs (`bin/`), the
Temporal SQLite database (`temporal/`), runtime logs and locks (`runtime/`),
generation receipts/prepared sources (`jobs/`), batch manifests/results
(`batches/`), and redacted reports (`reports/`). These are operational files;
there is currently no public CLI for listing or deleting jobs.

Prepared content, receipts, workflow history, and pending/final output hashes
let idempotent activities continue after a worker or service restart. If a
client process disappears without sending cancellation and before acknowledging
its result, repeating the same direct request reattaches to the unacknowledged
workflow or completed receipt. `Ctrl+C` explicitly requests workflow
cancellation. Existing batch workflows resume internally when the runtime
comes back, but there is no public command to look up an earlier batch by ID.

Inline text, local file contents, Temporal state, and audio synthesis are not
sent to a hosted TTS or Temporal service. Network access is still used when
Speekify fetches a URL/YouTube transcript, downloads AI models, or provisions
the pinned Temporal CLI for a pip/pipx/uv installation.
