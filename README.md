# Speekify

Speekify turns CLI text, stdin, or the readable content of a URL into a local WAV file generated with Supertonic v3.

## Install

### macOS without Python or uv

Once a release has been published, you can install the standalone binary with Homebrew or by downloading the archive directly.

Homebrew tap flow:

```bash
brew tap hiboux/speekify
brew install speekify
speekify setup
```

Direct download flow:

```bash
curl -L -o speekify.tar.gz https://github.com/hiboux/speekify/releases/latest/download/speekify-macos-arm64.tar.gz
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

Speekify is a CLI. Provide inline text, a URL, or piped stdin:

```bash
speekify "Hello world"
speekify https://example.com/article
printf 'Hello from stdin' | speekify
```

### CLI commands

All examples below work with the installed binary (`speekify …`) or directly from the source tree (`uv run speekify …`). The `uv run` form is shown alongside each group.

```bash
# Generate from inline text
speekify "Hello world"
uv run speekify "Hello world"

speekify --lang fr "Bonjour tout le monde"
uv run speekify --lang fr "Bonjour tout le monde"

# Generate from a URL (auto-detected or forced)
speekify https://example.com/article
uv run speekify https://example.com/article

speekify --url https://example.com/article
uv run speekify --url https://example.com/article

# Pipe text from stdin
printf 'Hello from stdin' | speekify
printf 'Hello from stdin' | uv run speekify

# Override output name and directory
speekify --title my-article --output-dir ~/Desktop "Hello world"
uv run speekify --title my-article --output-dir ~/Desktop "Hello world"

# Choose a voice
speekify --voice F2 "Hello world"
uv run speekify --voice F2 "Hello world"

# Adjust speed and synthesis steps
speekify --speed 1.2 --steps 20 "Hello world"
uv run speekify --speed 1.2 --steps 20 "Hello world"

# Download and warm up models
speekify setup
uv run speekify setup

speekify setup --skip-translation   # skip the EN→FR translation model
uv run speekify setup --skip-translation

# Show help
speekify --help
uv run speekify --help

speekify setup --help
uv run speekify setup --help
```

### CLI options reference

| Option | Default | Description |
|---|---|---|
| `source` | *(stdin if piped)* | Text to synthesize or a URL to extract. Required unless stdin is piped. |
| `--lang CODE` | `en` | Supertonic ISO 639-1 language code. Supported: `en`, `fr`, `de`, `es`, `it`, `pt`, `nl`, `pl`, `ru`, `ja`, `ko`, `ar`, `hi`, `tr`, `uk`, `vi`, `zh`, and more. Use `na` for language-agnostic synthesis. |
| `--voice NAME` | `M1` | Supertonic voice. Male: `M1`–`M5`. Female: `F1`–`F5`. |
| `--speed VALUE` | `1.05` | Playback speed multiplier (`0.7`–`2.0`). |
| `--steps N` | `8` | Number of synthesis steps (`1`–`100`). Higher values may improve quality. |
| `--url` | — | Force URL extraction mode even if the source looks like plain text. |
| `--title TEXT` | *(auto)* | Override the output file name (without extension). |
| `--output-dir PATH` | `.` (current directory) | Directory where the WAV file is written. |

By default, direct CLI generation writes the WAV file into the current working directory, with names like:

```text
./article-title-20260528-183000.wav
```

## Release for maintainers

See `docs/release-procedure.md` for the full step-by-step release checklist.

To build a standalone macOS archive and generate the Homebrew formula inputs:

```bash
./scripts/build_standalone_macos.sh
python scripts/render_homebrew_formula.py \
	--version 0.1.0 \
	--url https://github.com/hiboux/speekify/releases/download/v0.1.0/speekify-macos-arm64.tar.gz \
	--sha256 <sha256>
```

The GitHub Actions workflow in `.github/workflows/release.yml` automates the same release packaging on tag pushes.

## Notes

- The app uses `supertonic-3` by default.
- The direct CLI defaults to English synthesis (`en`) and accepts only Supertonic-supported ISO 639-1 language codes such as `en`, `fr`, `ja` or `ko`, plus `na` for language-agnostic synthesis.
- When `--lang fr` is used, English inputs are auto-detected and translated to French before TTS with `Helsinki-NLP/opus-mt-en-fr`.
- URL mode extracts readable body text rather than raw HTML.
- A single URL is auto-detected and extracted unless `--url` is needed to force URL mode.
- Input text is cleaned permissively before synthesis: Supertonic preprocessing is reused, unsupported characters are removed automatically, and the CLI summarizes the cleanup after generation.
- Very large inputs are split into external batches automatically and merged into one final WAV file.
- The steps control follows the SDK range `1..100`, with `8` as the default.
- If generation fails, detailed logs are written to `logs/speekify.log`.
