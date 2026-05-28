# Speekify Implementation Specs

## Goal

Speekify is a Python CLI that converts inline text, piped stdin, or readable URL content into a local WAV file generated with Supertonic v3.

## Architecture

- `src/speekify/__main__.py`: CLI parser, setup command, stdin handling, output messages.
- `src/speekify/workflow.py`: source resolution, optional translation, validation, synthesis orchestration, file saving.
- `src/speekify/extract.py`: text normalization and URL-to-readable-text extraction.
- `src/speekify/naming.py`: deterministic, filesystem-safe output path creation.
- `src/speekify/tts.py`: Supertonic adapter and permissive text preparation.
- `src/speekify/tagging/`: sparse Supertonic inline tag placement with rules, CardiffNLP sentiment, and capped emotion tags.
- `src/speekify/translation.py`: English-to-French translation support when French synthesis is requested.

## Runtime Decisions

- Use `uv` for environment, dependency, script, and test commands.
- Generate `.wav` files.
- Default output directory is the current working directory; `--output-dir` can override it.
- Keep synthesis local through the Supertonic Python package.
- Default model: `supertonic-3`.
- Default voice: `M5`.
- Default synthesis language: `fr`.
- Default speed: `0.98`.
- Default synthesis steps: `10`.
- Default Supertonic chunk silence: `0.25` seconds.
- Speech tagging is enabled by default and combines rules-based `<breath>` placement with CardiffNLP sentiment and rare capped `<sigh>` tags.
- `--no-tag-sentiment --no-tag-sigh` keeps rules-only tagging; `--no-tags` disables all inline tags.
- Supported language values come from Supertonic ISO 639-1 codes plus `na` for language-agnostic synthesis.
- When `--lang fr` is selected, English input is translated to French with `Helsinki-NLP/opus-mt-en-fr` before synthesis.
- `speekify setup` warms Supertonic, CardiffNLP sentiment, and English-to-French translation by default. Use `--skip-sentiment` or `--skip-translation` to skip optional setup downloads.
- Supertonic handles normal long-text chunking internally via `max_chunk_length` and `silence_duration`; Speekify only splits external batches above the SDK text limit.
- URL extraction produces readable article/body text, not raw HTML.
- A single URL source is auto-detected; `--url` can force URL extraction mode.
- Running without a source and without piped stdin is an invalid CLI invocation.

## Commands

```bash
speekify "Hello world"
speekify --lang fr "Hello world"
speekify https://example.com/article
printf 'Hello from stdin' | speekify
speekify --title my-article --output-dir ~/Desktop "Hello world"
speekify --no-tag-sentiment --no-tag-sigh "Hello world"
speekify --custom-style-path ~/voices/my-voice.json "Hello world"
speekify setup
speekify setup --skip-sentiment
```

## Validation

```bash
uv run pytest
uv run ruff check .
```