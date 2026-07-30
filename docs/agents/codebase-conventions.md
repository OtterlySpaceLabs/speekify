# Codebase Conventions

- Use `GenerationRequest`/`GenerationResult` dataclasses when changing generation flow rather than passing loose dictionaries through the workflow.
- Validate user-facing CLI values in `__main__.py` with Typer callbacks or option bounds, then keep duplicated runtime guards in `workflow.py`/`tts.py` where direct calls need protection.
- When adding a generation status, update both the status callbacks in `workflow.py` and the display label map in `cli_rendering.format_status()`.
- French synthesis has a special behavior: when `target_language == "fr"`, `workflow.translate_content_if_needed()` calls `HuggingFaceTranslator.maybe_translate_to_french()` and only English input is translated.
- `SupertonicSynthesizer.prepare_text()` is intentionally permissive: it preprocesses via Supertonic, removes unsupported characters when possible, and reports cleanup through `PreparedText.summary_notes()`.
- Non-durable inspection/core paths use `build_output_path()`; durable output paths use `job_store.deterministic_output_path()` with a slug, submission timestamp, and short job suffix. Both remain `.wav` and must never overwrite an unrelated file.
- User-facing terminal output should stay concise Rich panels/tables. Temporal IDs and runtime administration stay hidden. A redacted final diagnostic report is shown only for failures, synthesis warnings, reused prepared/audio artifacts, or `--verbose`.
- Any durable generation or batch client path must hold `temporal_runtime.RuntimeLease` from before runtime startup until its result/cancellation handling finishes. The daemon must fail safe (stay alive) when workflow visibility cannot be checked.
- URL extraction should return readable body text, not raw HTML; provider-specific extraction belongs under `extractors/`, while `extract.py` stays a small facade.
