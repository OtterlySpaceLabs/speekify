# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Shape

- Speekify is a Python 3.11+ CLI that converts inline text, piped stdin, or readable URL content into a local WAV file using Supertonic v3.
- The installed command is `speekify`, wired by `pyproject.toml` to `speekify.__main__:main`.
- Keep the CLI boundary in `src/speekify/__main__.py`: Typer/Click parsing, stdin handling, Rich status/progress/success/error rendering, and `setup` warmup live there.
- Keep orchestration in `src/speekify/workflow.py`: it resolves text vs URL input, optionally translates, prepares text, builds the output path, loads the model, synthesizes, and saves.
- Runtime adapters are separated: `extract.py` handles readable URL/text normalization, `translation.py` handles English-to-French Hugging Face translation, `tts.py` wraps Supertonic, `naming.py` creates safe timestamped WAV paths, and `logging_utils.py` owns `logs/speekify.log` retention.

## Development Commands

- Use `uv` for local work: `uv sync --group dev`, `uv run pytest`, and `uv run ruff check .`.
- Run focused tests while iterating, for example `uv run pytest tests/test_workflow.py` or `uv run pytest tests/test_cli.py`.
- Exercise the CLI from source with `uv run speekify "Hello world"`, `uv run speekify --lang fr "Hello world"`, or `printf 'Hello' | uv run speekify`.
- Model warmup is `uv run speekify setup`; use `--skip-translation` when validating only Supertonic setup.
- Release validation and packaging are documented in `docs/release-procedure.md`; the tag workflow is `.github/workflows/release.yml` and calls `./scripts/build_standalone_macos.sh`.

## Codebase Conventions

- Use `GenerationRequest`/`GenerationResult` dataclasses when changing generation flow rather than passing loose dictionaries through the workflow.
- Validate user-facing CLI values in `__main__.py` with Typer callbacks or option bounds, then keep duplicated runtime guards in `workflow.py`/`tts.py` where direct calls need protection.
- When adding a generation status, update both the status callbacks in `workflow.py` and the display label map in `_format_status()`.
- French synthesis has a special behavior: when `target_language == "fr"`, `workflow.translate_content_if_needed()` calls `HuggingFaceTranslator.maybe_translate_to_french()` and only English input is translated.
- `SupertonicSynthesizer.prepare_text()` is intentionally permissive: it preprocesses via Supertonic, removes unsupported characters when possible, and reports cleanup through `PreparedText.summary_notes()`.
- Output files should continue to be `.wav` files named by `build_output_path()`, using a slug plus timestamp and collision suffixes.
- User-facing terminal output should stay concise Rich panels/tables; technical diagnostics belong in `logs/speekify.log` and are shown to users only with `--verbose`.
- URL extraction should return readable body text, not raw HTML; Medium-specific blocked-article fallback lives in `extract.py`.

## Testing Patterns

- Tests avoid loading real models by monkeypatching builders in `speekify.__main__` or injecting fake synthesizers/translators into `workflow.generate_audio()`.
- Use `tmp_path`, `monkeypatch.chdir()`, and fake stdin objects for CLI tests that touch files or input streams.
- For async URL/workflow behavior, prefer `pytest.mark.asyncio` or `asyncio.run()` as the nearby tests already do.
- Preserve existing fake backend style in `tests/test_tts.py` and `tests/test_translation.py` when covering Supertonic, torch, or transformers behavior.

## Dependencies And Integration Points

- External runtime dependencies include `supertonic`, `httpx`, `trafilatura`, `langdetect`, `torch`, `transformers`, `rich`, and `typer`.
- `translation.py` chooses `mps` when available, otherwise CPU, and disables transformers progress output.
- `logging_utils.configure_logger()` quiets noisy Hugging Face/transformers loggers and prunes records older than 14 days.
- Standalone macOS packaging uses PyInstaller through `scripts/build_standalone_macos.sh`; Homebrew formula rendering is handled by `scripts/render_homebrew_formula.py`.