# Input Sources & Generation Behavior

How Speekify decides what to read, and the details of how it turns it into
audio. For the command list and options, see the [CLI reference](usage.md).

## What Speekify can read

Speekify accepts inline text, piped stdin, a local file path, or a URL as its
source, and auto-detects which one you gave it.

The `speekify batch` command also accepts directories and recursively expands
all supported documents into independent audio jobs. Expansion is stable-sorted,
deduplicated, limited to 1,000 items and 50 MiB per file, and does not follow
symlinks. Unsupported entries found inside a directory are skipped with a
warning; an explicitly supplied unsupported file or symlink is an error.

| Source | How it's detected | Notes |
|---|---|---|
| Inline text | Default when the source isn't a file or URL | Quote multi-word text. |
| stdin | Used when text is piped and no source is given | `printf '…' \| speekify` |
| `.txt` / `.md` / `.text` file | Source resolves to an existing file with that extension | File name becomes the default output title. |
| `.pdf` file | Source resolves to an existing `.pdf` | Text extracted with `pypdf`. Text-based PDFs only — scanned/image PDFs with no text layer yield nothing. |
| Readable URL | Source looks like a URL, or `--url` forces it | Extracts readable body text, not raw HTML. |
| YouTube video | URL is a YouTube watch link | Uses English captions/transcripts when available. |

A source that resolves to an existing file is read automatically. `--url` skips
file detection and forces URL extraction even when the source looks like plain
text.

## Language and translation

- Speekify accepts only Supertonic-supported ISO 639-1 language codes such as
  `en`, `fr`, `ja`, or `ko`, plus `na` for language-agnostic synthesis.
- The direct CLI defaults to auto-detecting the source language and
  synthesizing in that language without translation, with voice `M5`, speed
  `0.98`, `10` synthesis steps, and `0.25 s` chunk silence. When the language
  can't be detected, it falls back to language-agnostic synthesis (`na`), never
  to French.
- When French synthesis is explicitly requested (`--lang fr` or `fr` config),
  English inputs are auto-detected and translated to French before TTS with
  `Helsinki-NLP/opus-mt-en-fr`.

## Text handling

- Input text is cleaned permissively before synthesis: Supertonic preprocessing
  is reused, unsupported characters are removed automatically, and the CLI
  summarizes the cleanup after generation.
- Supertonic handles normal long-text chunking internally. Very large inputs
  above the SDK text limit are split into external batches automatically and
  merged into one final WAV file.
- The model used is `supertonic-3` by default.
- The `--steps` control follows the SDK range `1..100`, with `10` as the
  default.

## Errors and logs

- If generation fails, the terminal shows a short user-focused error and the
  path of a redacted diagnostic report when available.
- Runtime logs live in the platform Speekify data directory
  (`~/Library/Application Support/Speekify/runtime` on macOS or
  `${XDG_DATA_HOME:-~/.local/share}/speekify/runtime` on Linux), not in the
  current working directory. Entries older than 14 days are pruned when the
  logger is configured.
- Successful ordinary runs do not produce a final report. Failures,
  synthesis warnings, recovered prepared/audio artifacts and `--verbose` runs do.

## Local storage and network use

Speekify stores Temporal's SQLite database, workflow receipts, prepared text,
batch manifests, diagnostics and runtime locks under the platform data
directory. `SPEEKIFY_DATA_DIR` overrides that location. The local Temporal
service is headless, listens only on `127.0.0.1`, disables telemetry/newsfeed,
and stops after five minutes without a client or running workflow. Its on-disk
state is reused the next time generation starts it.

Text/file preparation and speech synthesis run locally. Network access happens
only when required by the selected input or installation path: fetching
web/YouTube content, downloading the Supertonic or translation models, and
provisioning the pinned Temporal CLI on the first pip/pipx/uv generation.
