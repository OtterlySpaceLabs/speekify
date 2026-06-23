from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from speekify.extract import ExtractedContent
from speekify.tagging import TaggingResult
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


class InlineBreathTagger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def tag(self, text: str, *, language_code: str) -> TaggingResult:
        self.calls.append((text, language_code))
        return TaggingResult(original_text=text, text=f"{text} <breath>")


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
        return ExtractedContent(text="Contenu extrait", title="Article")

    monkeypatch.setattr("speekify.workflow.extract_url", fake_extract_url)

    content = asyncio.run(
        resolve_content(
            " https://www.faketech.fr/p/le-gros-mytho-danthropic ",
            is_url_mode=False,
            target_language="fr",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert captured["url"] == " https://www.faketech.fr/p/le-gros-mytho-danthropic "
    assert content == ExtractedContent(text="Contenu extrait", title="Article")
    assert statuses == ["extracting URL", "checking language"]


def test_resolve_content_reads_text_file(tmp_path) -> None:
    doc = tmp_path / "Mon Article.txt"
    doc.write_text("Bonjour depuis un fichier.\n", encoding="utf-8")
    statuses: list[str] = []

    content = asyncio.run(
        resolve_content(
            str(doc),
            is_url_mode=False,
            target_language="fr",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert content == ExtractedContent(text="Bonjour depuis un fichier.", title="Mon Article")
    assert statuses == ["reading file", "checking language"]


def test_resolve_content_reads_pdf_file(tmp_path) -> None:
    from speekify.extract_common import read_document

    pdf = tmp_path / "rapport.pdf"
    pdf.write_bytes(_minimal_pdf_bytes("Texte du PDF."))

    content = read_document(pdf)

    assert "Texte du PDF." in content.text
    assert content.title == "rapport"


def _minimal_pdf_bytes(text: str) -> bytes:
    # Hand-built single-page PDF with a real text-showing content stream so the
    # pypdf reader path is exercised end to end (no reportlab dependency).
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\nBT /F1 12 Tf 10 100 Td (%s) Tj ET\nendstream"
        % (len(text) + 28, text.encode("latin-1")),
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


def test_resolve_content_translates_english_text_to_french() -> None:
    translator = FrenchTranslator()
    statuses: list[str] = []

    content = asyncio.run(
        resolve_content(
            "Hello everyone.",
            is_url_mode=False,
            target_language="fr",
            translator=translator,
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert content == ExtractedContent(text="Bonjour tout le monde.")
    assert translator.calls == ["Hello everyone."]
    assert statuses == ["checking language", "translating to French"]


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
        "checking language",
        "preparing text",
        "annotating text",
        "loading model",
        "synthesizing",
        "saving",
        "writing metadata",
    ]


def test_generate_audio_applies_tags_after_preparing_text(tmp_path) -> None:
    tagger = InlineBreathTagger()
    synthesizer = PermissiveSuccessSynthesizer()

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
            synthesizer=synthesizer,
            translator=NoopTranslator(),
            tagger=tagger,
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert tagger.calls == [("Bonjour monde.", "fr")]
    assert result.artifact.prepared_text.text == "Bonjour monde. <breath>"
    assert synthesizer.synthesis_calls[0]["prepared_text"] == "Bonjour monde. <breath>"


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


def test_generate_audio_writes_json_metadata_and_podcast_feed(tmp_path, monkeypatch) -> None:
    async def fake_extract_url(url: str) -> ExtractedContent:
        assert url == "https://example.com/article"
        return ExtractedContent(text="Bonjour source.", title="Article source")

    monkeypatch.setattr("speekify.workflow.extract_url", fake_extract_url)

    result = asyncio.run(
        generate_audio(
            GenerationRequest(
                source_text="https://example.com/article",
                voice="M1",
                language_code="fr",
                speed=1.05,
                steps=8,
                title="Mon article",
                output_dir=tmp_path,
                feed_base_url="https://audio.example.com/speekify/",
            ),
            synthesizer=PermissiveSuccessSynthesizer(),
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    import json
    from xml.etree import ElementTree as ET

    assert result.metadata_path == result.output_path.with_suffix(".json")
    assert result.feed_path == tmp_path / "speekify-feed.xml"
    assert result.metadata_path is not None
    assert result.feed_path is not None

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["$schema"] == "https://otterly.space/speekify/metadata/v1"
    assert metadata["title"] == "Mon article"
    assert metadata["audio"]["file"] == result.output_path.name
    assert metadata["audio"]["mime_type"] == "audio/wav"
    assert metadata["audio"]["size_bytes"] == 3
    assert metadata["source"]["mode"] == "url"
    assert metadata["source"]["url"] == "https://example.com/article"
    assert metadata["synthesis"]["voice"] == "M1"
    assert metadata["synthesis"]["language_code"] == "fr"
    assert metadata["podcast"]["enclosure_url"] == (
        f"https://audio.example.com/speekify/{result.output_path.name}"
    )
    assert metadata["podcast"]["local_enclosure_uri"].startswith("file://")
    assert metadata["podcast"]["enclosure_type"] == "audio/wav"
    assert metadata["podcast"]["feed_url"] == "https://audio.example.com/speekify/speekify-feed.xml"

    root = ET.parse(result.feed_path).getroot()
    channel = root.find("channel")
    assert channel is not None
    assert channel.findtext("title") == "Speekify Personal Podcast"
    item = channel.find("item")
    assert item is not None
    assert item.findtext("title") == "Mon article"
    enclosure = item.find("enclosure")
    assert enclosure is not None
    assert enclosure.attrib["url"] == metadata["podcast"]["enclosure_url"]
    assert channel.findtext("link") == "https://audio.example.com/speekify"
    assert enclosure.attrib["length"] == "3"
    assert enclosure.attrib["type"] == "audio/wav"


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
    tagger = InlineBreathTagger()

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
            tagger=tagger,
            logger=logging.getLogger("speekify.tests.workflow"),
        )
    )

    assert inspection.title == "Preview"
    assert inspection.source_mode == "text"
    assert inspection.output_path.parent == tmp_path
    assert inspection.feed_path == tmp_path / "speekify-feed.xml"
    assert inspection.prepared_text.text == "Bonjour monde <breath>"
    assert tagger.calls == [("Bonjour monde", "fr")]
