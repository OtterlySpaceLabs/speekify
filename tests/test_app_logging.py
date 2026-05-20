import pytest
from textual.widgets import Label

from speekify.app import SpeekifyApp
from speekify.extract import ExtractedContent
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.translation import TranslationResult


class FailingSynthesizer:
    @property
    def engine(self) -> str:
        return "ready"

    def prepare_text(self, text: str) -> PreparedText:
        return PreparedText(
            original_text=text,
            text=text,
            reformatted=False,
            removed_characters=(),
            removed_character_count=0,
        )

    def synthesize_prepared_text(self, **_: object) -> SynthesisArtifact:
        raise RuntimeError("synthèse impossible")

    def save_audio(self, wav: object, output_path: object) -> None:
        raise AssertionError("save_audio should not be called when synthesize fails")


class UnsupportedCharactersSynthesizer:
    @property
    def engine(self) -> str:
        return "ready"

    def prepare_text(self, text: str) -> PreparedText:
        return PreparedText(
            original_text=text,
            text=text,
            reformatted=False,
            removed_characters=(),
            removed_character_count=0,
        )

    def synthesize_prepared_text(self, **_: object) -> SynthesisArtifact:
        raise ValueError(
            "Le texte contient des caracteres non supportes par Supertonic: '世', '界'"
        )

    def save_audio(self, wav: object, output_path: object) -> None:
        raise AssertionError("save_audio should not be called when synthesize fails")


class PermissiveSuccessSynthesizer:
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
        lang: str,
        steps: int,
        speed: float,
        silence_duration: float,
    ) -> SynthesisArtifact:
        return SynthesisArtifact(
            wav="wav",
            duration_seconds=2.5,
            batch_count=3,
            prepared_text=prepared_text,
        )

    def save_audio(self, wav: object, output_path: object) -> None:
        return None


class FakeTranslator:
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


@pytest.mark.asyncio
async def test_generation_error_is_logged(tmp_path) -> None:
    log_path = tmp_path / "speekify.log"
    app = SpeekifyApp(log_path=log_path)
    app.synthesizer = FailingSynthesizer()

    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#content").text = "Bonjour tout le monde."
        app.action_generate()
        await pilot.pause()

    log_content = log_path.read_text(encoding="utf-8")
    assert "Generation failed" in log_content
    assert "RuntimeError: synthèse impossible" in log_content


@pytest.mark.asyncio
async def test_generation_error_shows_unsupported_characters_hint(tmp_path) -> None:
    app = SpeekifyApp(log_path=tmp_path / "speekify.log")
    app.synthesizer = UnsupportedCharactersSynthesizer()

    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#content").text = "Bonjour 世界"
        app.action_generate()
        await pilot.pause()
        result = app.query_one("#result", Label).render().plain

    assert "'世', '界'" in result
    assert "Supprime ou remplace" in result


@pytest.mark.asyncio
async def test_generation_success_shows_cleanup_and_batch_summary(tmp_path) -> None:
    app = SpeekifyApp(log_path=tmp_path / "speekify.log")
    app.synthesizer = PermissiveSuccessSynthesizer()

    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#content").text = "Bonjour 😀 monde"
        app.action_generate()
        await pilot.pause()
        result = app.query_one("#result", Label).render().plain

    assert "2.50s" in result
    assert "batch" in result.lower()
    assert "caractere" in result.lower()
    assert "reformate" in result.lower()


@pytest.mark.asyncio
async def test_resolve_content_autodetects_single_url_input(tmp_path, monkeypatch) -> None:
    captured: dict[str, str] = {}

    async def fake_extract_url(url: str) -> ExtractedContent:
        captured["url"] = url
        return ExtractedContent(text="Contenu extrait", title="Article")

    monkeypatch.setattr("speekify.app.extract_url", fake_extract_url)
    app = SpeekifyApp(log_path=tmp_path / "speekify.log")

    async with app.run_test() as pilot:
        await pilot.pause()
        content = await app._resolve_content(
            " https://www.faketech.fr/p/le-gros-mytho-danthropic ",
            is_url_mode=False,
        )
        status = app.query_one("#status", Label).render().plain

    assert captured["url"] == " https://www.faketech.fr/p/le-gros-mytho-danthropic "
    assert content == ExtractedContent(text="Contenu extrait", title="Article")
    assert status == "checking language"


@pytest.mark.asyncio
async def test_resolve_content_translates_english_text_to_french(tmp_path) -> None:
    app = SpeekifyApp(log_path=tmp_path / "speekify.log")
    app.translator = FakeTranslator()

    async with app.run_test() as pilot:
        await pilot.pause()
        content = await app._resolve_content("Hello everyone.", is_url_mode=False)
        status = app.query_one("#status", Label).render().plain

    assert content == ExtractedContent(text="Bonjour tout le monde.")
    assert app.translator.calls == ["Hello everyone."]
    assert status == "translating to French"
