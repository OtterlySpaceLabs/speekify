from pathlib import Path

import pytest
import numpy as np

from speekify.multilingual import FrenchEnglishIslandSegmenter, LanguageSegment
from speekify.tts import PreparedText, SynthesisArtifact, SupertonicSynthesizer


class FakeTTS:
    def __init__(self, model: str) -> None:
        self.model = model
        self.saved: tuple[object, str] | None = None
        self.sample_rate = 10
        self.custom_style_path: str | None = None

    def get_voice_style(self, voice: str) -> str:
        return f"style:{voice}"

    def get_voice_style_from_path(self, voice_style_path: str) -> str:
        self.custom_style_path = voice_style_path
        return "style:custom"

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
        assert voice_style in {"style:M1", "style:custom"}
        assert lang == "fr"
        assert total_steps == 8
        assert speed == 1.05
        assert silence_duration == 0.3
        return np.array([[0.0, 0.1]], dtype=np.float32), np.array([1.23], dtype=np.float32)

    def save_audio(self, wav: list[float], output_path: str) -> None:
        self.saved = (wav, output_path)
        Path(output_path).write_bytes(b"wav")


class FakeTextProcessor:
    def __init__(self, is_valid: bool, unsupported: list[str]) -> None:
        self._is_valid = is_valid
        self._unsupported = unsupported

    def validate_text(self, text: str) -> tuple[bool, list[str]]:
        if self._is_valid:
            return True, []
        remaining = [char for char in self._unsupported if char in text]
        return len(remaining) == 0, remaining

    def _preprocess_text(self, text: str, lang: str | None = None) -> str:
        return text


class FakeModel:
    def __init__(self, processor: FakeTextProcessor) -> None:
        self.text_processor = processor


class FakeTTSWithValidation(FakeTTS):
    def __init__(self, model: str, *, is_valid: bool, unsupported: list[str]) -> None:
        super().__init__(model=model)
        self.model = FakeModel(FakeTextProcessor(is_valid=is_valid, unsupported=unsupported))


def _synthesize_and_save(
    synth: SupertonicSynthesizer,
    *,
    text: str,
    output_path: Path,
    voice: str,
    voice_style_path: Path | None = None,
    lang: str,
    steps: int,
    speed: float,
    silence_duration: float,
    max_batch_length: int = 1200,
) -> SynthesisArtifact:
    artifact = synth.synthesize_prepared_text(
        prepared_text=synth.prepare_text(text),
        voice=voice,
        voice_style_path=voice_style_path,
        lang=lang,
        steps=steps,
        speed=speed,
        silence_duration=silence_duration,
        max_batch_length=max_batch_length,
    )
    synth.save_audio(artifact.wav, output_path)
    return artifact


def test_synthesizer_saves_audio(tmp_path) -> None:
    fake = FakeTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    output = tmp_path / "test.wav"

    artifact = _synthesize_and_save(
        synth,
        text="Bonjour",
        output_path=output,
        voice="M1",
        lang="fr",
        steps=8,
        speed=1.05,
        silence_duration=0.3,
    )

    assert isinstance(artifact, SynthesisArtifact)
    assert artifact.duration_seconds == pytest.approx(1.23)
    assert artifact.batch_count == 1
    assert output.read_bytes() == b"wav"
    assert fake.saved is not None
    wav, saved_path = fake.saved
    assert saved_path == str(output)
    assert wav.shape == (1, 2)


def test_synthesizer_loads_custom_voice_style_path(tmp_path) -> None:
    fake = FakeTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    output = tmp_path / "custom.wav"
    voice_style_path = tmp_path / "voice.json"
    voice_style_path.write_text("{}", encoding="utf-8")

    artifact = _synthesize_and_save(
        synth,
        text="Bonjour",
        output_path=output,
        voice="M1",
        voice_style_path=voice_style_path,
        lang="fr",
        steps=8,
        speed=1.05,
        silence_duration=0.3,
    )

    assert artifact.batch_count == 1
    assert fake.custom_style_path == str(voice_style_path)
    assert output.read_bytes() == b"wav"


def test_synthesizer_removes_unsupported_characters_permissively() -> None:
    fake = FakeTTSWithValidation(
        model="supertonic-3",
        is_valid=False,
        unsupported=["世", "界"],
    )
    synth = SupertonicSynthesizer(engine=fake)

    prepared = synth.prepare_text("Bonjour 世界")

    assert prepared.text == "Bonjour"
    assert prepared.removed_characters == ("世", "界")
    assert prepared.removed_character_count == 2
    assert prepared.changed is True


class FakePermissiveTextProcessor:
    def validate_text(self, text: str) -> tuple[bool, list[str]]:
        unsupported = sorted({char for char in text if char in {"😀", "🚀"}})
        return len(unsupported) == 0, unsupported

    def _preprocess_text(self, text: str, lang: str | None = None) -> str:
        return " ".join(text.split())


class FakePermissiveModel:
    def __init__(self) -> None:
        self.text_processor = FakePermissiveTextProcessor()


class FakeBatchingTTS:
    def __init__(self, model: str) -> None:
        self.model = FakePermissiveModel()
        self.sample_rate = 10
        self.calls: list[str] = []
        self.max_chunk_lengths: list[int | None] = []

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
        max_chunk_length: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        assert voice_style == "style:M1"
        assert lang == "fr"
        self.calls.append(text)
        self.max_chunk_lengths.append(max_chunk_length)
        wav = np.ones((1, len(text)), dtype=np.float32)
        duration = np.array([len(text) / 10], dtype=np.float32)
        return wav, duration

    def save_audio(self, wav: np.ndarray, output_path: str) -> None:
        Path(output_path).write_bytes(b"wav")


def test_synthesizer_batches_very_long_text_and_merges_audio(tmp_path) -> None:
    fake = FakeBatchingTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    output = tmp_path / "batched.wav"

    artifact = _synthesize_and_save(
        synth,
        text="Bonjour 😀 monde. Encore un peu de texte pour tester le batch auto.",
        output_path=output,
        voice="M1",
        lang="fr",
        steps=8,
        speed=1.05,
        silence_duration=0.3,
        max_batch_length=20,
    )

    assert artifact.batch_count > 1
    assert artifact.prepared_text.removed_characters == ("😀",)
    assert artifact.prepared_text.removed_character_count == 1
    assert len(fake.calls) == artifact.batch_count
    assert artifact.wav.shape[0] == 1
    assert output.read_bytes() == b"wav"


def test_split_text_into_batches_splits_single_overlong_sentence() -> None:
    fake = FakeBatchingTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    text = "mot" * 140

    batches = synth.split_text_into_batches(text, preferred_chunk_length=50)

    assert len(batches) > 1
    assert "".join(batch.replace(" ", "") for batch in batches) == text
    assert all(len(batch) <= 50 for batch in batches)


def test_synthesizer_uses_language_chunk_limit_for_single_long_sentence(tmp_path) -> None:
    fake = FakeBatchingTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    output = tmp_path / "single-sentence.wav"
    text = "mot" * 140

    artifact = _synthesize_and_save(
        synth,
        text=text,
        output_path=output,
        voice="M1",
        lang="fr",
        steps=8,
        speed=1.05,
        silence_duration=0.3,
    )

    assert artifact.batch_count > 1
    assert "".join(fake.calls) == text
    assert fake.max_chunk_lengths == [300] * artifact.batch_count
    assert all(len(call) <= 300 for call in fake.calls)
    assert output.read_bytes() == b"wav"


def test_french_english_segmenter_detects_lexicon_islands() -> None:
    segmenter = FrenchEnglishIslandSegmenter()

    segments = segmenter.segment(
        "Ce prompt améliore le workflow de ton LLM powered app.",
        default_lang="fr",
        english_lang="en",
    )

    assert segments == (
        LanguageSegment(text="Ce ", lang="fr"),
        LanguageSegment(text="prompt", lang="en"),
        LanguageSegment(text=" améliore le ", lang="fr"),
        LanguageSegment(text="workflow", lang="en"),
        LanguageSegment(text=" de ton ", lang="fr"),
        LanguageSegment(text="LLM powered app", lang="en"),
        LanguageSegment(text=".", lang="fr"),
    )


def test_french_english_segmenter_avoids_lowercase_acronym_false_positive() -> None:
    segmenter = FrenchEnglishIslandSegmenter()

    segments = segmenter.segment("J ai un prompt utile.", default_lang="fr", english_lang="en")

    assert segments == (
        LanguageSegment(text="J ai un ", lang="fr"),
        LanguageSegment(text="prompt", lang="en"),
        LanguageSegment(text=" utile.", lang="fr"),
    )


class FakeMultilingualTTS(FakeBatchingTTS):
    def synthesize(
        self,
        text: str,
        *,
        voice_style: str,
        lang: str,
        total_steps: int,
        speed: float,
        silence_duration: float,
        max_chunk_length: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        assert voice_style == "style:M1"
        self.calls.append(f"{lang}:{text}")
        self.max_chunk_lengths.append(max_chunk_length)
        wav = np.ones((1, len(text)), dtype=np.float32)
        duration = np.array([len(text) / 10], dtype=np.float32)
        return wav, duration


def test_synthesizer_uses_english_for_french_lexicon_segments() -> None:
    fake = FakeMultilingualTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    prepared_text = PreparedText(
        original_text="Ce prompt améliore le workflow.",
        text="Ce prompt améliore le workflow.",
        reformatted=False,
        removed_characters=(),
        removed_character_count=0,
    )

    artifact = synth.synthesize_prepared_text(
        prepared_text=prepared_text,
        voice="M1",
        lang="fr",
        steps=8,
        speed=1.0,
        silence_duration=0.3,
    )

    assert fake.calls == [
        "fr:Ce",
        "en:prompt",
        "fr:améliore le",
        "en:workflow.",
    ]
    assert artifact.language_segments == (
        LanguageSegment(text="Ce ", lang="fr"),
        LanguageSegment(text="prompt", lang="en"),
        LanguageSegment(text=" améliore le ", lang="fr"),
        LanguageSegment(text="workflow", lang="en"),
        LanguageSegment(text=".", lang="fr"),
    )
    assert artifact.summary_notes() == ["English pronunciation islands: 'prompt', 'workflow'"]
    assert artifact.duration_seconds == pytest.approx(len("Cepromptaméliore leworkflow.") / 10)


def test_synthesizer_accepts_custom_english_lexicon_terms() -> None:
    fake = FakeMultilingualTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    prepared_text = PreparedText(
        original_text="Ce retrieval augmente la qualité.",
        text="Ce retrieval augmente la qualité.",
        reformatted=False,
        removed_characters=(),
        removed_character_count=0,
    )

    artifact = synth.synthesize_prepared_text(
        prepared_text=prepared_text,
        voice="M1",
        lang="fr",
        steps=8,
        speed=1.0,
        silence_duration=0.3,
        english_lexicon_terms=("retrieval",),
    )

    assert fake.calls == ["fr:Ce", "en:retrieval", "fr:augmente la qualité."]
    assert artifact.summary_notes() == ["English pronunciation islands: 'retrieval'"]


def test_synthesizer_can_disable_english_island_detection() -> None:
    fake = FakeMultilingualTTS(model="supertonic-3")
    synth = SupertonicSynthesizer(engine=fake)
    prepared_text = PreparedText(
        original_text="Ce prompt reste français.",
        text="Ce prompt reste français.",
        reformatted=False,
        removed_characters=(),
        removed_character_count=0,
    )

    artifact = synth.synthesize_prepared_text(
        prepared_text=prepared_text,
        voice="M1",
        lang="fr",
        steps=8,
        speed=1.0,
        silence_duration=0.3,
        detect_english_islands=False,
    )

    assert fake.calls == ["fr:Ce prompt reste français."]
    assert artifact.summary_notes() == []
