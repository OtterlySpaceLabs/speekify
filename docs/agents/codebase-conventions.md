# Codebase Conventions

- Use `GenerationRequest`/`GenerationResult` dataclasses when changing generation flow rather than passing loose dictionaries through the workflow.
- Validate user-facing CLI values in `__main__.py` with Typer callbacks or option bounds, then keep duplicated runtime guards in `workflow.py`/`tts.py` where direct calls need protection.
- When adding a generation status, update both the status callbacks in `workflow.py` and the display label map in `_format_status()`.
- French synthesis has a special behavior: when `target_language == "fr"`, `workflow.translate_content_if_needed()` calls `HuggingFaceTranslator.maybe_translate_to_french()` and only English input is translated.
- `SupertonicSynthesizer.prepare_text()` is intentionally permissive: it preprocesses via Supertonic, removes unsupported characters when possible, and reports cleanup through `PreparedText.summary_notes()`.
- Output files should continue to be `.wav` files named by `build_output_path()`, using a slug plus timestamp and collision suffixes.
- User-facing terminal output should stay concise Rich panels/tables; technical diagnostics belong in `logs/speekify.log` and are shown to users only with `--verbose`.
- URL extraction should return readable body text, not raw HTML; Medium-specific blocked-article fallback lives in `extract.py`.