# Speekify Implementation Specs

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this spec task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python TUI that converts either pasted text or the readable content of a pasted URL into a correctly named `.wav` file in `output/`.

**Architecture:** The app is split into a Textual TUI, source ingestion services, deterministic output naming, and a thin Supertonic synthesis adapter. Supertonic v3 is used through the official Python package with `TTS(model="supertonic-3")`, built-in voice styles, and local WAV output.

**Tech Stack:** Python 3.11+, UV, Textual, Supertonic Python package, httpx, trafilatura, pytest.

---

## Decisions

- Use `uv` for all environment, dependency, script, and test commands.
- Generate `.wav`, not `.waw`; WAV is the audio format and the Supertonic API writes WAV files.
- Use `output/` as the canonical folder name; create it automatically if missing.
- Keep synthesis local. Supertonic runs via ONNX Runtime and should not call a hosted TTS API.
- Default model: `supertonic-3`.
- Default voice: `M1`.
- Target language: French only.
- Default synthesis language: `fr`.
- Do not expose a language selector in the first version; every synthesis call uses `lang="fr"`.
- Default speed: `1.05`.
- Default synthesis steps: `8`.
- Default silence between chunks: `0.3`.
- URL extraction should produce readable article/body text, not raw HTML.
- No language detection is required; pasted text and extracted URL content are treated as French.
- File naming must be deterministic, filesystem-safe, and collision-resistant.

## External References Checked

- Supertonic main repo: https://github.com/supertone-inc/supertonic
- Supertonic Python docs: https://supertone-inc.github.io/supertonic-py/
- Supertonic PyPI package: https://pypi.org/project/supertonic/

Relevant verified API surface:

```python
from supertonic import TTS

tts = TTS(model="supertonic-3")
style = tts.get_voice_style("M1")
wav, duration = tts.synthesize(
    "Bonjour !",
    voice_style=style,
    lang="fr",
    total_steps=8,
    speed=1.05,
    silence_duration=0.3,
)
tts.save_audio(wav, "output/example.wav")
```

## User Experience

The first screen is the usable app, not a landing page.

The TUI must contain:

- A source mode selector with two options: `Text` and `URL`.
- A multiline input area for pasted text or URL.
- Settings panel:
  - Voice select: `M1`, `M2`, `M3`, `M4`, `M5`, `F1`, `F2`, `F3`, `F4`, `F5`.
  - Speed input constrained to `0.7..2.0`.
  - Steps input constrained to `1..16`.
  - Output title input, optional.
- Primary action: `Generate`.
- Status area showing: idle, extracting URL, loading model, synthesizing, saving, done, error.
- Result area showing the final output path and approximate generated duration.

Keyboard shortcuts:

- `Ctrl+V`: paste into focused input.
- `Ctrl+Enter`: generate.
- `Ctrl+Q`: quit.
- `Tab` / `Shift+Tab`: move focus.

## Project Structure

Create these files:

```text
pyproject.toml
README.md
src/speekify/__init__.py
src/speekify/__main__.py
src/speekify/app.py
src/speekify/config.py
src/speekify/extract.py
src/speekify/naming.py
src/speekify/tts.py
tests/test_extract.py
tests/test_naming.py
tests/test_tts.py
```

Responsibilities:

- `pyproject.toml`: UV project metadata, dependencies, console script.
- `src/speekify/__main__.py`: runs the TUI with `python -m speekify`.
- `src/speekify/app.py`: Textual widgets, events, validation, async orchestration.
- `src/speekify/config.py`: constants for output directory, default model, French language, and synthesis defaults.
- `src/speekify/extract.py`: text normalization and URL-to-readable-text extraction.
- `src/speekify/naming.py`: slug generation and collision-safe output path creation.
- `src/speekify/tts.py`: Supertonic adapter.
- `tests/*`: focused unit tests with Supertonic mocked where needed.

## UV Environment

Initialize:

```bash
uv init --package --python 3.11
```

Add runtime dependencies:

```bash
uv add "supertonic>=1.3.1" "textual>=0.89" "httpx>=0.27" "trafilatura>=1.9"
```

Add dev dependencies:

```bash
uv add --dev "pytest>=8.0" "pytest-asyncio>=0.23" "ruff>=0.6"
```

Required `pyproject.toml` entries:

```toml
[project]
name = "speekify"
version = "0.1.0"
description = "TUI URL/text to WAV converter powered by Supertonic v3"
requires-python = ">=3.11"
dependencies = [
  "supertonic>=1.3.1",
  "textual>=0.89",
  "httpx>=0.27",
  "trafilatura>=1.9",
]

[project.scripts]
speekify = "speekify.__main__:main"

[dependency-groups]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "ruff>=0.6",
]

[tool.ruff]
line-length = 100
target-version = "py311"
```

Run commands:

```bash
uv run speekify
uv run python -m speekify
uv run pytest
uv run ruff check .
```

Optional first model download/warmup:

```bash
uv run supertonic download
```

## Domain Rules

Input validation:

- Text mode rejects empty or whitespace-only input.
- URL mode accepts only `http://` and `https://`.
- URL mode rejects extracted content shorter than 80 characters with a clear error.
- Text and URL content are synthesized as French without language auto-detection.
- Any text passed to Supertonic is stripped and normalized to single blank lines.
- The app does not silently truncate user input. If Supertonic raises a max-length error, surface it and ask the user to shorten the content.

Output naming:

- If user supplies an output title, use it as the base name.
- Else for URL mode, prefer the page title from extraction.
- Else derive from the first meaningful sentence.
- Slug rules:
  - lowercase
  - ASCII transliteration when possible
  - replace non-alphanumeric groups with `-`
  - trim leading/trailing `-`
  - maximum 72 characters
  - fallback to `speech`
- Append a timestamp: `YYYYMMDD-HHMMSS`.
- Final pattern: `output/<slug>-<timestamp>.wav`.
- If the path already exists, append `-2`, `-3`, etc.

## Implementation Plan

### Task 1: Bootstrap UV Project

**Files:**
- Create/modify: `pyproject.toml`
- Create: `src/speekify/__init__.py`
- Create: `src/speekify/__main__.py`

- [ ] **Step 1: Initialize the package**

Run:

```bash
uv init --package --python 3.11
```

Expected: `pyproject.toml` and `src/` package scaffold exist.

- [ ] **Step 2: Add dependencies**

Run:

```bash
uv add "supertonic>=1.3.1" "textual>=0.89" "httpx>=0.27" "trafilatura>=1.9"
uv add --dev "pytest>=8.0" "pytest-asyncio>=0.23" "ruff>=0.6"
```

Expected: `uv.lock` is created or updated.

- [ ] **Step 3: Add the app entry point**

`src/speekify/__main__.py`:

```python
from speekify.app import SpeekifyApp


def main() -> None:
    SpeekifyApp().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify the entry point imports**

Run:

```bash
uv run python -m speekify --help
```

Expected: the command imports the package. It may open the TUI once `app.py` exists; before Task 5 it can fail only because `speekify.app` has not been created yet.

### Task 2: Configuration Constants

**Files:**
- Create: `src/speekify/config.py`

- [ ] **Step 1: Add configuration**

`src/speekify/config.py`:

```python
from pathlib import Path

OUTPUT_DIR = Path("output")
MODEL_NAME = "supertonic-3"
DEFAULT_VOICE = "M1"
DEFAULT_LANG = "fr"
DEFAULT_SPEED = 1.05
DEFAULT_STEPS = 8
DEFAULT_SILENCE_DURATION = 0.3

VOICE_NAMES = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
```

- [ ] **Step 2: Verify syntax**

Run:

```bash
uv run python -m py_compile src/speekify/config.py
```

Expected: no output and exit code `0`.

### Task 3: Output Naming

**Files:**
- Create: `src/speekify/naming.py`
- Test: `tests/test_naming.py`

- [ ] **Step 1: Write tests**

`tests/test_naming.py`:

```python
from datetime import datetime

from speekify.naming import build_output_path, slugify_title


def test_slugify_title_keeps_safe_words() -> None:
    assert slugify_title("Bonjour le monde ! Ça marche.") == "bonjour-le-monde-ca-marche"


def test_slugify_title_fallback() -> None:
    assert slugify_title("!!!") == "speech"


def test_build_output_path_uses_timestamp(tmp_path) -> None:
    path = build_output_path(
        output_dir=tmp_path,
        title="Article de test",
        created_at=datetime(2026, 5, 19, 18, 30, 0),
    )

    assert path == tmp_path / "article-de-test-20260519-183000.wav"


def test_build_output_path_avoids_collision(tmp_path) -> None:
    existing = tmp_path / "speech-20260519-183000.wav"
    existing.write_bytes(b"already here")

    path = build_output_path(
        output_dir=tmp_path,
        title="",
        created_at=datetime(2026, 5, 19, 18, 30, 0),
    )

    assert path == tmp_path / "speech-20260519-183000-2.wav"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_naming.py -v
```

Expected: fail because `speekify.naming` does not exist.

- [ ] **Step 3: Implement naming**

`src/speekify/naming.py`:

```python
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path


def slugify_title(title: str, max_length: int = 72) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug:
        return "speech"
    return slug[:max_length].rstrip("-") or "speech"


def build_output_path(
    output_dir: Path,
    title: str,
    created_at: datetime | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (created_at or datetime.now()).strftime("%Y%m%d-%H%M%S")
    stem = f"{slugify_title(title)}-{timestamp}"
    candidate = output_dir / f"{stem}.wav"
    index = 2

    while candidate.exists():
        candidate = output_dir / f"{stem}-{index}.wav"
        index += 1

    return candidate
```

- [ ] **Step 4: Run tests and verify success**

Run:

```bash
uv run pytest tests/test_naming.py -v
```

Expected: all tests pass.

### Task 4: Text and URL Extraction

**Files:**
- Create: `src/speekify/extract.py`
- Test: `tests/test_extract.py`

- [ ] **Step 1: Write tests**

`tests/test_extract.py`:

```python
import pytest

from speekify.extract import ExtractedContent, normalize_text, validate_url


def test_normalize_text_strips_repeated_blank_lines() -> None:
    raw = "  Bonjour   le monde\\n\\n\\nCeci est   un test.  "
    assert normalize_text(raw) == "Bonjour le monde\\n\\nCeci est un test."


def test_validate_url_accepts_http_and_https() -> None:
    assert validate_url("https://example.com/article") == "https://example.com/article"
    assert validate_url("http://example.com/article") == "http://example.com/article"


def test_validate_url_rejects_other_schemes() -> None:
    with pytest.raises(ValueError, match="http"):
        validate_url("file:///tmp/a.html")


def test_extracted_content_title_fallback() -> None:
    content = ExtractedContent(text="Bonjour le monde. Ceci est un texte long.", title="")
    assert content.best_title() == "Bonjour le monde"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_extract.py -v
```

Expected: fail because `speekify.extract` does not exist.

- [ ] **Step 3: Implement extraction helpers**

`src/speekify/extract.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
import trafilatura


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    title: str = ""

    def best_title(self) -> str:
        if self.title.strip():
            return self.title.strip()
        first_sentence = re.split(r"[.!?\\n]", self.text.strip(), maxsplit=1)[0]
        return first_sentence.strip() or "speech"


def normalize_text(text: str) -> str:
    lines = [re.sub(r"[ \\t]+", " ", line).strip() for line in text.strip().splitlines()]
    normalized_lines: list[str] = []
    previous_blank = False

    for line in lines:
        is_blank = not line
        if is_blank and previous_blank:
            continue
        normalized_lines.append(line)
        previous_blank = is_blank

    return "\\n".join(normalized_lines).strip()


def validate_url(url: str) -> str:
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("L'URL doit commencer par http:// ou https://.")
    return candidate


async def extract_url(url: str, min_chars: int = 80) -> ExtractedContent:
    validated_url = validate_url(url)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(
            validated_url,
            headers={"User-Agent": "speekify/0.1 (+https://github.com/supertone-inc/supertonic)"},
        )
        response.raise_for_status()

    metadata = trafilatura.extract_metadata(response.text)
    extracted = trafilatura.extract(
        response.text,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    text = normalize_text(extracted or "")
    if len(text) < min_chars:
        raise ValueError("Le contenu lisible extrait de cette URL est trop court.")

    title = metadata.title if metadata and metadata.title else ""
    return ExtractedContent(text=text, title=title)
```

- [ ] **Step 4: Run tests and verify success**

Run:

```bash
uv run pytest tests/test_extract.py -v
```

Expected: all tests pass.

### Task 5: Supertonic Adapter

**Files:**
- Create: `src/speekify/tts.py`
- Test: `tests/test_tts.py`

- [ ] **Step 1: Write tests with a fake engine**

`tests/test_tts.py`:

```python
from pathlib import Path

from speekify.tts import SupertonicSynthesizer


class FakeTTS:
    def __init__(self, model: str) -> None:
        self.model = model
        self.saved: tuple[object, str] | None = None

    def get_voice_style(self, voice: str) -> str:
        return f"style:{voice}"

    def synthesize(
        self,
        text: str,
        *,
        voice_style: str,
        lang: str,
        total_steps: int,
        speed: float,
        silence_duration: float,
    ) -> tuple[list[float], list[float]]:
        assert text == "Bonjour"
        assert voice_style == "style:M1"
        assert lang == "fr"
        assert total_steps == 8
        assert speed == 1.05
        assert silence_duration == 0.3
        return [0.0, 0.1], [1.23]

    def save_audio(self, wav: list[float], output_path: str) -> None:
        self.saved = (wav, output_path)
        Path(output_path).write_bytes(b"wav")


def test_synthesizer_saves_audio(tmp_path) -> None:
    fake = FakeTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    output = tmp_path / "test.wav"

    duration = synth.synthesize_to_file(
        text="Bonjour",
        output_path=output,
        voice="M1",
        lang="fr",
        steps=8,
        speed=1.05,
        silence_duration=0.3,
    )

    assert duration == 1.23
    assert output.read_bytes() == b"wav"
    assert fake.saved == ([0.0, 0.1], str(output))
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_tts.py -v
```

Expected: fail because `speekify.tts` does not exist.

- [ ] **Step 3: Implement Supertonic adapter**

`src/speekify/tts.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from supertonic import TTS

from speekify.config import MODEL_NAME


class SupertonicSynthesizer:
    def __init__(self, engine: Any | None = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> Any:
        if self._engine is None:
            self._engine = TTS(model=MODEL_NAME)
        return self._engine

    def synthesize_to_file(
        self,
        *,
        text: str,
        output_path: Path,
        voice: str,
        lang: str,
        steps: int,
        speed: float,
        silence_duration: float,
    ) -> float:
        style = self.engine.get_voice_style(voice)
        wav, duration = self.engine.synthesize(
            text,
            voice_style=style,
            lang=lang,
            total_steps=steps,
            speed=speed,
            silence_duration=silence_duration,
        )
        self.engine.save_audio(wav, str(output_path))
        return float(duration[0])
```

- [ ] **Step 4: Run tests and verify success**

Run:

```bash
uv run pytest tests/test_tts.py -v
```

Expected: all tests pass.

### Task 6: Textual TUI

**Files:**
- Create: `src/speekify/app.py`
- Modify: `src/speekify/__main__.py`

- [ ] **Step 1: Implement TUI**

`src/speekify/app.py`:

```python
from __future__ import annotations

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Select, TextArea

from speekify.config import (
    DEFAULT_LANG,
    DEFAULT_SILENCE_DURATION,
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_VOICE,
    OUTPUT_DIR,
    VOICE_NAMES,
)
from speekify.extract import ExtractedContent, extract_url, normalize_text
from speekify.naming import build_output_path
from speekify.tts import SupertonicSynthesizer


class SpeekifyApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        height: 1fr;
        padding: 1 2;
    }

    #source {
        height: 3;
    }

    #content {
        height: 1fr;
        min-height: 10;
    }

    #settings {
        height: auto;
        margin-top: 1;
    }

    .setting {
        width: 1fr;
        margin-right: 1;
    }

    #status {
        height: 3;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+enter", "generate", "Generate"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.synthesizer = SupertonicSynthesizer()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main"):
            yield Label("Source")
            with RadioSet(id="source"):
                yield RadioButton("Text", value=True, id="mode-text")
                yield RadioButton("URL", id="mode-url")
            yield TextArea(id="content")
            with Horizontal(id="settings"):
                yield Input(placeholder="Output title optional", id="title", classes="setting")
                yield Select.from_values(VOICE_NAMES, value=DEFAULT_VOICE, id="voice", classes="setting")
                yield Input(value=str(DEFAULT_SPEED), placeholder="Speed", id="speed", classes="setting")
                yield Input(value=str(DEFAULT_STEPS), placeholder="Steps", id="steps", classes="setting")
            yield Button("Generate", id="generate", variant="primary")
            yield Label("Idle", id="status")
        yield Footer()

    def action_generate(self) -> None:
        self.generate()

    @on(Button.Pressed, "#generate")
    def generate(self) -> None:
        self._generate()

    @work(exclusive=True, thread=False)
    async def _generate(self) -> None:
        status = self.query_one("#status", Label)
        status.update("Preparing input...")

        try:
            source_text = self.query_one("#content", TextArea).text
            is_url_mode = self.query_one("#mode-url", RadioButton).value
            voice = str(self.query_one("#voice", Select).value)
            title_input = self.query_one("#title", Input).value.strip()
            speed = float(self.query_one("#speed", Input).value)
            steps = int(self.query_one("#steps", Input).value)

            if not 0.7 <= speed <= 2.0:
                raise ValueError("La vitesse doit etre entre 0.7 et 2.0.")
            if not 1 <= steps <= 16:
                raise ValueError("Le nombre de steps doit etre entre 1 et 16.")

            if is_url_mode:
                status.update("Extracting URL...")
                content = await extract_url(source_text)
            else:
                text = normalize_text(source_text)
                if not text:
                    raise ValueError("Le texte ne peut pas etre vide.")
                content = ExtractedContent(text=text, title="")

            output_title = title_input or content.best_title()
            output_path = build_output_path(OUTPUT_DIR, output_title)

            status.update("Synthesizing with Supertonic v3...")
            duration = await self.run_worker(
                lambda: self.synthesizer.synthesize_to_file(
                    text=content.text,
                    output_path=output_path,
                    voice=voice,
                    lang=DEFAULT_LANG,
                    steps=steps,
                    speed=speed,
                    silence_duration=DEFAULT_SILENCE_DURATION,
                ),
                thread=True,
                exclusive=True,
            ).wait()

            status.update(f"Done: {output_path} ({duration:.2f}s)")
        except Exception as exc:
            status.update(f"Error: {exc}")
```

- [ ] **Step 2: Run import check**

Run:

```bash
uv run python -m py_compile src/speekify/app.py
```

Expected: no output and exit code `0`.

- [ ] **Step 3: Launch the app**

Run:

```bash
uv run speekify
```

Expected: the TUI opens with source selector, input area, settings, and Generate button.

### Task 7: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Add usage docs**

`README.md`:

```markdown
# Speekify

Speekify is a Python TUI that turns pasted text or the readable content of a pasted URL into a local WAV file with Supertonic v3.

## Setup

```bash
uv sync
uv run supertonic download
```

## Run

```bash
uv run speekify
```

Generated files are written to `output/` with names like:

```text
output/article-title-20260519-183000.wav
```

## Notes

- The app uses `supertonic-3` by default.
- The synthesis language is French (`fr`).
- No hosted TTS API is used.
```

- [ ] **Step 2: Verify docs commands**

Run:

```bash
uv run python -m speekify
```

Expected: the TUI starts.

## Acceptance Criteria

- `uv run speekify` launches the TUI.
- Text mode can paste text and generate `output/<slug>-<timestamp>.wav`.
- URL mode can paste an `https://` URL, extract readable text, and generate a WAV file.
- The app uses Supertonic v3 by default.
- The TUI has no language selector; synthesis always passes `lang="fr"`.
- Output folder is created automatically.
- Generated filenames are lowercase, safe, meaningful, timestamped, and collision-safe.
- Empty text and invalid URL inputs show clear errors in the TUI.
- Supertonic dependency/model download errors are surfaced in the status area.
- `uv run pytest` passes.
- `uv run ruff check .` passes.

## Verification Checklist

- [ ] `uv sync`
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run speekify`
- [ ] Manual test: text input in French generates a playable `.wav`.
- [ ] Manual test: URL input from a readable article generates a playable `.wav`.
- [ ] Manual test: invalid URL shows an error and does not create a file.
- [ ] Manual test: repeated same title creates `-2.wav` instead of overwriting.
