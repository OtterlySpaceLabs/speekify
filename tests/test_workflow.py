from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from speekify.extract import ExtractedContent
from speekify.translation import TranslationResult
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationRequest, generate_audio, inspect_generation, resolve_content


class NoopTranslator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def maybe_translate_to_french(self, text: str) -> TranslationResult:
        self.calls.append(text)
        return TranslationResult(
            text=text,
            translated=False,
            source_language="fr",
            target_language="fr",
            original_text=text,
        )


class FrenchTranslator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def maybe_translate_to_french(self, text: str) -> TranslationResult:
        self.calls.append(text)
        return TranslationResult(
            text="Bonjour tout le monde.",
            translated=True,
            source_language="en",
            target_language="fr",
            original_text=text,
        )


class PermissiveSuccessSynthesizer:
    def __init__(self) -> None:
        self.synthesis_calls: list[dict[str, object]] = []

    @property
    def engine(self) -> str:
        return "ready"

    def prepare_text(self, text: str) -> PreparedText:
        return PreparedText(
            original_text=text,
            text="Bonjour monde.",
            reformatted=True,
            removed_characters=("😀",),
            removed_character_count=1,
        )

    def synthesize_prepared_text(
        self,
        *,
        prepared_text: PreparedText,
        voice: str,
        voice_style_path: Path | None,
        lang: str,
        steps: int,
        speed: float,
        silence_duration: float,
        max_chunk_length: int | None,
        detect_english_islands: bool,
        english_lexicon_terms: tuple[str, ...] | None,
    ) -> SynthesisArtifact:
        self.synthesis_calls.append(
            {
                "prepared_text": prepared_text.text,
                "voice": voice,
                "voice_style_path": voice_style_path,
                "lang": lang,
                "steps": steps,
                "speed": speed,
                "silence_duration": silence_duration,
                "max_chunk_length": max_chunk_length,
                "detect_english_islands": detect_english_islands,
                "english_lexicon_terms": english_lexicon_terms,
            }
        )
        assert voice == "M1"
        assert lang == "fr"
        assert steps == 8
        assert speed == 1.05
        return SynthesisArtifact(
            wav="wav",
            duration_seconds=2.5,
            batch_count=3,
            prepared_text=prepared_text,
        )

    def save_audio(self, wav: object, output_path: Path) -> None:
        output_path.write_text(str(wav), encoding="utf-8")


def test_resolve_content_autodetects_single_url_input(monkeypatch) -> None:
    captured: dict[str, str] = {}
    statuses: list[str] = []

    async def fake_extract_url(url: str) -> ExtractedContent:
        captured["url"] = url
        return ExtractedContent(
            text=(
                "# Contenu extrait\n\n"
                "![Graphique](chart.png)\n\n"
                "| Sujet | État |\n"
                "| --- | --- |\n"
                "| Pipeline | Prêt |"
            ),
            title="Article",
        )

    monkeypatch.setattr("speekify.workflow.extract_url", fake_extract_url)

    resolved = asyncio.run(
        resolve_content(
            " https://www.faketech.fr/p/le-gros-mytho-danthropic ",
            is_url_mode=False,
            requested_language="fr",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert captured["url"] == " https://www.faketech.fr/p/le-gros-mytho-danthropic "
    assert resolved.content == ExtractedContent(
        text="Contenu extrait\n\nSujet : Pipeline ; État : Prêt.",
        title="Article",
    )
    assert resolved.language_code == "fr"
    assert statuses == ["extracting URL", "preparing content", "checking language"]


@pytest.mark.parametrize("suffix", [".txt", ".md", ".text"])
def test_resolve_content_reads_and_prepares_text_files(tmp_path, suffix) -> None:
    doc = tmp_path / f"Mon Article{suffix}"
    doc.write_text(
        "# Bonjour depuis un fichier\n\n![Illustration](image.png)\n",
        encoding="utf-8",
    )
    statuses: list[str] = []

    resolved = asyncio.run(
        resolve_content(
            str(doc),
            is_url_mode=False,
            requested_language="fr",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert resolved.content == ExtractedContent(
        text="Bonjour depuis un fichier", title="Mon Article"
    )
    assert resolved.language_code == "fr"
    assert statuses == ["reading file", "preparing content", "checking language"]


def test_resolve_content_reads_and_prepares_pdf_file(tmp_path) -> None:
    pdf = tmp_path / "rapport.pdf"
    pdf.write_bytes(_minimal_pdf_bytes("Texte du PDF. ![Graphique](ventes.png)"))

    resolved = asyncio.run(
        resolve_content(
            str(pdf),
            is_url_mode=False,
            requested_language="fr",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert resolved.content.text == "Texte du PDF."
    assert resolved.content.title == "rapport"


def _minimal_pdf_bytes(text: str) -> bytes:
    # Hand-built single-page PDF with a real text-showing content stream so the
    # pypdf reader path is exercised end to end (no reportlab dependency).
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f'BT /F1 12 Tf 10 100 Td ({escaped_text}) Tj ET'.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1,
        xref_pos,
    )
    return bytes(out)


def test_resolve_content_prepares_transcript_content(monkeypatch) -> None:
    async def fake_extract_url(url: str) -> ExtractedContent:
        assert url == "https://www.youtube.com/watch?v=example"
        return ExtractedContent(
            text=(
                "Transcript introduction.\n\n"
                "![Video frame](frame.jpg)\n\n"
                "Transcript conclusion."
            ),
            title="Video title",
        )

    monkeypatch.setattr("speekify.workflow.extract_url", fake_extract_url)

    resolved = asyncio.run(
        resolve_content(
            "https://www.youtube.com/watch?v=example",
            is_url_mode=False,
            requested_language="en",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert resolved.content == ExtractedContent(
        text="Transcript introduction.\n\nTranscript conclusion.",
        title="Video title",
    )


def test_resolve_content_prepares_inline_or_stdin_text_before_detection(monkeypatch) -> None:
    detected_inputs: list[str] = []

    def fake_detect_language_code(text: str) -> str:
        detected_inputs.append(text)
        return "en"

    monkeypatch.setattr("speekify.workflow.detect_language_code", fake_detect_language_code)

    resolved = asyncio.run(
        resolve_content(
            "# Spoken title\n\n![Decoration](image.png)\n\nSpoken paragraph.",
            is_url_mode=False,
            requested_language="auto",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert detected_inputs == ["Spoken title\n\nSpoken paragraph."]
    assert resolved.content.text == "Spoken title\n\nSpoken paragraph."


def test_resolve_content_translates_english_text_to_french() -> None:
    translator = FrenchTranslator()
    statuses: list[str] = []

    resolved = asyncio.run(
        resolve_content(
            "![Chart](chart.png)\n\nHello [everyone](https://example.com).\n\n```py\nx = 1\n```",
            is_url_mode=False,
            requested_language="fr",
            translator=translator,
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert resolved.content == ExtractedContent(text="Bonjour tout le monde.")
    assert resolved.language_code == "fr"
    assert translator.calls == ["Hello everyone."]
    assert statuses == ["preparing content", "checking language", "translating to French"]


def test_resolve_content_auto_uses_detected_language_without_translation() -> None:
    translator = FrenchTranslator()
    statuses: list[str] = []

    resolved = asyncio.run(
        resolve_content(
            "Cet article est écrit dans un français clair avec le plus grand soin possible.",
            is_url_mode=False,
            requested_language="auto",
            translator=translator,
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert resolved.language_code == "fr"
    assert resolved.content.text.startswith("Cet article")
    assert translator.calls == []  # auto mode never translates
    assert statuses == ["preparing content", "checking language"]


def test_resolve_content_auto_keeps_english_source_untranslated() -> None:
    translator = FrenchTranslator()
    statuses: list[str] = []

    resolved = asyncio.run(
        resolve_content(
            "This article is written in plain, careful English from start to finish.",
            is_url_mode=False,
            requested_language="auto",
            translator=translator,
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    # iff rule: English source stays English in auto mode; French only with --lang fr.
    assert resolved.language_code == "en"
    assert resolved.content.text.startswith("This article")
    assert translator.calls == []
    assert statuses == ["preparing content", "checking language"]


def test_resolve_content_auto_falls_back_to_language_agnostic_when_undetected() -> None:
    translator = FrenchTranslator()
    statuses: list[str] = []

    resolved = asyncio.run(
        resolve_content(
            "Hi there.",  # too short to detect → "na", never French
            is_url_mode=False,
            requested_language="auto",
            translator=translator,
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert resolved.language_code == "na"
    assert translator.calls == []
    assert statuses == ["preparing content", "checking language"]


def test_generate_audio_returns_cleanup_summary(tmp_path) -> None:
    statuses: list[str] = []

    result = asyncio.run(
        generate_audio(
            GenerationRequest(
                source_text="Bonjour 😀 monde",
                voice="M1",
                language_code="fr",
                speed=1.05,
                steps=8,
                output_dir=tmp_path,
            ),
            synthesizer=PermissiveSuccessSynthesizer(),
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert result.output_path.read_text(encoding="utf-8") == "wav"
    assert result.artifact.duration_seconds == 2.5
    assert result.artifact.summary_notes() == [
        "1 character(s) removed: '😀'",
    ]
    assert statuses == [
        "preparing content",
        "checking language",
        "preparing text",
        "loading model",
        "synthesizing",
        "saving",
    ]


def test_generate_audio_passes_supertonic_options(tmp_path) -> None:
    voice_style_path = tmp_path / "voice.json"
    voice_style_path.write_text("{}", encoding="utf-8")
    synthesizer = PermissiveSuccessSynthesizer()

    asyncio.run(
        generate_audio(
            GenerationRequest(
                source_text="Bonjour 😀 monde",
                voice="M1",
                voice_style_path=voice_style_path,
                language_code="fr",
                speed=1.05,
                steps=8,
                max_chunk_length=240,
                silence_duration=0.2,
                output_dir=tmp_path,
            ),
            synthesizer=synthesizer,
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert synthesizer.synthesis_calls == [
        {
            "prepared_text": "Bonjour monde.",
            "voice": "M1",
            "voice_style_path": voice_style_path,
            "lang": "fr",
            "steps": 8,
            "speed": 1.05,
            "silence_duration": 0.2,
            "max_chunk_length": 240,
            "detect_english_islands": True,
            "english_lexicon_terms": None,
        }
    ]


def test_generate_audio_loads_custom_english_lexicon(tmp_path) -> None:
    lexicon_path = tmp_path / "english.txt"
    lexicon_path.write_text("# comment\nretrieval\n\n", encoding="utf-8")
    synthesizer = PermissiveSuccessSynthesizer()

    asyncio.run(
        generate_audio(
            GenerationRequest(
                source_text="Bonjour 😀 monde",
                voice="M1",
                language_code="fr",
                speed=1.05,
                steps=8,
                english_lexicon_path=lexicon_path,
                output_dir=tmp_path,
            ),
            synthesizer=synthesizer,
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert synthesizer.synthesis_calls[0]["english_lexicon_terms"] == ("retrieval",)


def test_inspect_generation_previews_without_synthesizer(tmp_path) -> None:
    inspection = asyncio.run(
        inspect_generation(
            GenerationRequest(
                source_text="Bonjour monde",
                voice="M1",
                language_code="fr",
                speed=1.05,
                steps=8,
                title="Preview",
                output_dir=tmp_path,
            ),
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert inspection.title == "Preview"
    assert inspection.source_mode == "text"
    assert inspection.output_path.parent == tmp_path
    assert inspection.prepared_text.text == "Bonjour monde"
