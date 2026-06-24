# Development Commands

- Run focused tests while iterating, for example `uv run pytest tests/test_workflow.py` or `uv run pytest tests/test_cli.py`.
- Exercise the CLI from source with `uv run speekify "Hello world"`, `uv run speekify --lang fr "Hello world"`, or `printf 'Hello' | uv run speekify`.
- Quote URLs that contain shell-special characters such as `?` or `&`, for example `uv run speekify "https://www.youtube.com/watch?v=eSP7PLTXNy8"`, because `zsh` can reject the command before Speekify starts.
- Model warmup is `uv run speekify setup`; by default it warms Supertonic, CardiffNLP sentiment, and English-to-French translation. Use `--skip-translation` when validating Supertonic plus sentiment, or `--skip-translation --skip-sentiment` for Supertonic-only setup.
- Release validation and packaging are documented in `docs/release-procedure.md`; releases are built locally only (no GitHub Actions) via `./scripts/build_standalone_macos.sh`.
