# Development Commands

- Run focused tests while iterating, for example `uv run pytest tests/test_workflow.py` or `uv run pytest tests/test_cli.py`.
- Exercise the CLI from source with `uv run speekify "Hello world"`, `uv run speekify --lang fr "Hello world"`, or `printf 'Hello' | uv run speekify`.
- Model warmup is `uv run speekify setup`; by default it warms Supertonic, CardiffNLP sentiment, and English-to-French translation. Use `--skip-translation` when validating Supertonic plus sentiment, or `--skip-translation --skip-sentiment` for Supertonic-only setup.
- Release validation and packaging are documented in `docs/release-procedure.md`; the tag workflow is `.github/workflows/release.yml` and calls `./scripts/build_standalone_macos.sh`.