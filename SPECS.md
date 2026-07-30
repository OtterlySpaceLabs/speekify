# Speekify Implementation Specs

## Goal

Speekify is a Python 3.11+ CLI that converts inline text, piped stdin, a local
`.txt`/`.md`/`.text`/`.pdf` file, or readable URL content into a local WAV file
generated with Supertonic v3. User-facing generation is synchronous while a
strictly local Temporal runtime provides durable orchestration.

## Architecture

- `src/speekify/__main__.py`: CLI parser, command routing, and stdin handling.
- `src/speekify/cli_rendering.py`: Rich status, success, warning, error, doctor, and inspection output.
- `src/speekify/setup.py`: setup command model warmup/progress implementation.
- `src/speekify/workflow.py`: source resolution, optional translation, validation, inspection, synthesis orchestration, file saving.
- `src/speekify/extract.py`: public extraction facade.
- `src/speekify/extractors/`: provider-specific extraction for generic HTML, YouTube, and Medium fallbacks.
- `src/speekify/user_config.py`: optional TOML generation defaults from `~/.config/speekify/config.toml` or `SPEEKIFY_CONFIG`.
- `src/speekify/naming.py`: deterministic, filesystem-safe output path creation.
- `src/speekify/tts.py`: Supertonic adapter and permissive text preparation.
- `src/speekify/multilingual.py`: French-English island segmentation and optional English lexicon loading.
- `src/speekify/translation.py`: English-to-French translation support when French synthesis is requested.
- `src/speekify/mcp_server.py`: local MCP server exposing the generation tools.
- `src/speekify/batch.py`: recursive directory expansion, source validation,
  deterministic ordering, deduplication, and batch limits.
- `src/speekify/temporal_client.py`: blocking client bridge for durable
  generation/batches, progress polling, and direct-generation reattachment.
- `src/speekify/temporal_workflows.py`: versioned generation and batch workflows,
  retries, timeouts, progress queries, and diagnostic-report decisions.
- `src/speekify/temporal_activities.py`: idempotent preparation, synthesis,
  atomic output persistence, and diagnostic activities.
- `src/speekify/temporal_runtime.py`: loopback Temporal server/worker daemon,
  five-minute idle shutdown, activity leases, and verified CLI provisioning.
- `src/speekify/job_store.py`: private local data layout, atomic JSON/text writes,
  receipts, hashes, URL/secret redaction, and reports.

## Runtime Decisions

- Use `uv` for environment, dependency, script, and test commands.
- Generate `.wav` files.
- Default output directory is the current working directory; `--output-dir` can override it.
- Keep synthesis local through the Supertonic Python package.
- Default model: `supertonic-3`.
- Default voice: `M5`.
- Default synthesis language: auto-detect the source language and synthesize in it (no translation); fall back to language-agnostic `na` when detection fails.
- Default speed: `0.98`.
- Default synthesis steps: `10`.
- Default Supertonic chunk silence: `0.25` seconds.
- Supported language values come from Supertonic ISO 639-1 codes plus `na` for language-agnostic synthesis.
- When `--lang fr` is selected, English input is translated to French with `Helsinki-NLP/opus-mt-en-fr` before synthesis. This is the only path from English source to French audio: English produces French audio if and only if `--lang fr` (or equivalent `fr` config) is given.
- `speekify setup` warms Supertonic and English-to-French translation by default. Use `--skip-translation` to skip the optional translation download.
- Supertonic handles normal long-text chunking internally via `max_chunk_length` and `silence_duration`; Speekify only splits external batches above the SDK text limit.
- URL extraction produces readable article/body text, not raw HTML.
- `--english-islands` (default on) pronounces known English tech terms as English islands during French synthesis; `--english-lexicon-path` extends the lexicon.
- A single URL source is auto-detected; `--url` can force URL extraction mode.
- A source resolving to an existing `.txt`/`.md`/`.text`/`.pdf` file is read automatically (PDF text via `pypdf`) and the file name becomes the default title; `--url` skips file detection.
- `--dry-run` and `speekify inspect` preview extraction, translation, and planned output paths without synthesis.
- MCP generation exposes CLI-equivalent generation controls including English-island options and optional user-config defaults.
- Running without a source and without piped stdin is an invalid CLI invocation.
- CLI and MCP generation use the local Temporal workflow path; `inspect` and
  `--dry-run` do not synthesize and do not start Temporal.
- Temporal binds to `127.0.0.1:7233`, runs headless with telemetry/newsfeed and
  inherited `OTEL_*` exporters disabled, and persists SQLite state locally.
- The daemon holds the service open for every client generation/batch and for
  every running Temporal workflow. It stops only after five minutes with no
  lease and no active workflow; the next generation restarts it on the same
  database.
- Homebrew owns the `temporal` dependency. pip/pipx/uv provision the pinned
  official Temporal CLI 1.8.1 on first generation, verify its SHA-256, publish
  it atomically, then reuse it offline. This path supports macOS/Linux on
  `arm64`/`amd64`; Windows is not supported.
- Batch input is limited to 1,000 unique items and 50 MiB per file. Directories
  are recursive and stable-sorted; unsupported entries and symlinks are skipped,
  while explicitly supplied symlinks or unsupported files are rejected.
- There is no public Temporal administration, job-listing, job-status, or
  manual-resume command. Repeating an unacknowledged direct request reattaches
  by request fingerprint; durable batch workflows resume internally when the
  runtime restarts, but the CLI has no batch lookup command. Client cancellation
  (including `Ctrl+C`) is propagated to the workflow; process loss without a
  cancellation signal is the reattachment case.

## Commands

```bash
speekify "Hello world"
speekify --lang fr "Hello world"
speekify https://example.com/article
printf 'Hello from stdin' | speekify
speekify --title my-article --output-dir ~/Desktop "Hello world"
speekify --custom-style-path ~/voices/my-voice.json "Hello world"
speekify --dry-run https://example.com/article
speekify inspect "Hello world"
speekify batch article.pdf https://example.com ./notes
speekify setup
speekify setup --skip-translation
speekify --doctor
speekify mcp
```

## Validation

```bash
uv run pytest
uv run ruff check .
```
