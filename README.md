# Speekify

Speekify turns pasted text or the readable content of a URL into a local French WAV file generated with Supertonic v3.

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

Without arguments, Speekify opens the TUI:

```bash
speekify
```

From source:

```bash
uv run speekify
```

You can also generate directly from the terminal:

```bash
speekify "Bonjour tout le monde"
speekify --lang fr "Bonjour tout le monde"
speekify --help
speekify https://example.com/article
printf 'Hello from stdin' | speekify
```

Use `--lang` with a Supertonic-supported ISO 639-1 code like `en`, `fr`, `ja` or `ko` to choose the synthesis language. The direct CLI defaults to `en`. `speekify --help` lists the currently supported codes, including `na` for language-agnostic synthesis. Use `--url` to force URL extraction, `--title` to override the output name, and `--output-dir` if you do not want the current directory.

By default, direct CLI generation writes the WAV file into the current working directory, with names like:

```text
./article-title-20260528-183000.wav
```

The TUI keeps writing files into `output/`.

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
- The TUI keeps using French synthesis (`fr`).
- English inputs are auto-detected and translated to French before TTS with `Helsinki-NLP/opus-mt-en-fr`.
- URL mode extracts readable body text rather than raw HTML.
- A single pasted URL is auto-detected and extracted even if Text mode is still selected.
- Input text is cleaned permissively before synthesis: Supertonic preprocessing is reused, unsupported characters are removed automatically, and the app summarizes the cleanup after generation.
- Very large inputs are split into external batches automatically and merged into one final WAV file.
- The steps control follows the SDK range `1..100`, with `8` as the default.
- If generation fails, detailed logs are written to `logs/speekify.log`.
