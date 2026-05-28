# Testing Patterns

- Tests avoid loading real models by monkeypatching builders in `speekify.__main__` or injecting fake synthesizers/translators/taggers into `workflow.generate_audio()`.
- Use `tmp_path`, `monkeypatch.chdir()`, and fake stdin objects for CLI tests that touch files or input streams.
- For async URL/workflow behavior, prefer `pytest.mark.asyncio` or `asyncio.run()` as the nearby tests already do.
- Preserve existing fake backend style in `tests/test_tts.py`, `tests/test_translation.py`, and tagging tests when covering Supertonic, torch, transformers, or CardiffNLP behavior.