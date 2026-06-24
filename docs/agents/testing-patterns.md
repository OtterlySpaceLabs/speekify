# Testing Patterns

- CLI generation and inspection tests should prefer monkeypatching `speekify.application.run_generation()` or `speekify.application.run_inspection()` rather than private helpers in `speekify.__main__`.
- Tests avoid loading real models by monkeypatching the remaining CLI builders only for setup/doctor paths, or by injecting fake synthesizers/translators into `workflow.generate_audio()`.
- Use `tmp_path`, `monkeypatch.chdir()`, and fake stdin objects for CLI tests that touch files or input streams.
- For async URL/workflow behavior, prefer `pytest.mark.asyncio` or `asyncio.run()` as the nearby tests already do.
- Preserve existing fake backend style in `tests/test_tts.py` and `tests/test_translation.py` when covering Supertonic, torch, or transformers behavior.