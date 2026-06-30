# Input Sources & Generation Behavior

How Speekify decides what to read, and the details of how it turns it into
audio. For the command list and options, see the [CLI reference](usage.md).

## What Speekify can read

Speekify accepts inline text, piped stdin, a local file path, or a URL as its
source, and auto-detects which one you gave it.

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

- If generation fails, the terminal shows a short user-focused error. Add
  `--verbose` to include the technical log path (`logs/speekify.log`).
- Each CLI run maintains `logs/speekify.log` automatically and prunes log
  entries older than 14 days at startup.
