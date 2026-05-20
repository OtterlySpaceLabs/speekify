# Speekify

Speekify is a Python TUI that turns pasted text or the readable content of a pasted URL into a local WAV file generated with Supertonic v3.

## Setup

```bash
uv sync
uv run supertonic download
```

At first run, Supertonic can also download the model automatically into `~/.cache/supertonic3/`.
The first English to French translation also downloads the Hugging Face model `Helsinki-NLP/opus-mt-en-fr`.

## Run

```bash
uv run speekify
```

You can also start the app with:

```bash
uv run python -m speekify
```

Generated files are written to `output/` with names like:

```text
output/article-title-20260519-183000.wav
```

## Notes

- The app uses `supertonic-3` by default.
- The synthesis language is always French (`fr`).
- English inputs are auto-detected and translated to French before TTS with `Helsinki-NLP/opus-mt-en-fr`.
- The output directory is created automatically.
- URL mode extracts readable body text rather than raw HTML.
- A single pasted URL is auto-detected and extracted even if Text mode is still selected.
- Input text is cleaned permissively before synthesis: Supertonic preprocessing is reused, unsupported characters are removed automatically, and the app summarizes the cleanup after generation.
- Very large inputs are split into external batches automatically and merged into one final WAV file.
- The steps control follows the SDK range `1..100`, with `8` as the default.
- If generation fails, detailed logs are written to `logs/speekify.log`.
