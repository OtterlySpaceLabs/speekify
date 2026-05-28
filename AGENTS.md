# AGENTS.md

Speekify is a Python 3.11+ CLI that converts inline text, piped stdin, or readable URL content into a local WAV file using Supertonic v3.

Use `uv` for local work. Core checks are `uv sync --group dev`, `uv run pytest`, and `uv run ruff check .`.

The installed command is `speekify`, wired by `pyproject.toml` to `speekify.__main__:main`.

## More Guidance

- [Project architecture](docs/agents/project-architecture.md)
- [Development commands](docs/agents/development-commands.md)
- [Codebase conventions](docs/agents/codebase-conventions.md)
- [Testing patterns](docs/agents/testing-patterns.md)
- [Dependencies and integrations](docs/agents/dependencies-integrations.md)
- [Deletion candidates](docs/agents/deletion-candidates.md)