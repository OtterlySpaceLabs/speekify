import sys
from types import ModuleType, SimpleNamespace

from speekify.translation import (
    HuggingFaceTranslator,
    TranslationResult,
    _split_text_for_translation,
    detect_language_code,
    should_translate_to_french,
)


def test_detect_language_code_detects_english_text() -> None:
    text = "This article explains how a startup launched a product with careful experiments."
    assert detect_language_code(text) == "en"


def test_should_translate_to_french_only_for_english() -> None:
    assert should_translate_to_french("en") is True
    assert should_translate_to_french("fr") is False
    assert should_translate_to_french(None) is False


def test_translation_result_reports_change_when_text_changes() -> None:
    result = TranslationResult(
        text="Bonjour le monde",
        translated=True,
        source_language="en",
        target_language="fr",
        original_text="Hello world",
    )

    assert result.changed is True


def test_build_backend_disables_transformers_progress_bar(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    fake_torch = ModuleType("torch")
    fake_torch.backends = SimpleNamespace(
        mps=SimpleNamespace(is_available=lambda: False),
    )

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, model_name: str) -> str:
            calls.append(("tokenizer", model_name))
            return "tokenizer"

    class FakeModelInstance:
        def to(self, device: str) -> None:
            calls.append(("model.to", device))

    class FakeModel:
        @classmethod
        def from_pretrained(cls, model_name: str) -> FakeModelInstance:
            calls.append(("model", model_name))
            return FakeModelInstance()

    fake_transformers = ModuleType("transformers")
    fake_transformers.MarianTokenizer = FakeTokenizer
    fake_transformers.MarianMTModel = FakeModel

    fake_transformers_utils = ModuleType("transformers.utils")
    fake_transformers_utils.logging = SimpleNamespace(
        disable_progress_bar=lambda: calls.append(("disable_progress_bar", "called"))
    )

    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "transformers.utils", fake_transformers_utils)

    translator = HuggingFaceTranslator(model_name="Helsinki-NLP/test-model")
    _, tokenizer, model, device = translator._build_backend()

    assert calls == [
        ("disable_progress_bar", "called"),
        ("tokenizer", "Helsinki-NLP/test-model"),
        ("model", "Helsinki-NLP/test-model"),
        ("model.to", "cpu"),
    ]
    assert tokenizer == "tokenizer"
    assert model.__class__.__name__ == "FakeModelInstance"
    assert device == "cpu"


def test_translate_chunk_uses_max_length_without_max_new_tokens() -> None:
    calls: dict[str, object] = {}

    class FakeTensor:
        shape = (1, 3)

        def to(self, device: str) -> "FakeTensor":
            calls["device"] = device
            return self

    class FakeTorch:
        class _NoGrad:
            def __enter__(self) -> None:
                return None

            def __exit__(self, *_: object) -> None:
                return None

        @staticmethod
        def no_grad() -> "FakeTorch._NoGrad":
            return FakeTorch._NoGrad()

    class FakeTokenizer:
        def __call__(self, text: str, **kwargs: object) -> dict[str, FakeTensor]:
            calls["tokenizer"] = (text, kwargs)
            return {"input_ids": FakeTensor()}

        def decode(self, output_ids: object, *, skip_special_tokens: bool) -> str:
            calls["decode"] = (output_ids, skip_special_tokens)
            return "Bonjour"

    class FakeModel:
        def generate(self, **kwargs: object) -> list[list[int]]:
            calls["generate"] = kwargs
            return [[1, 2, 3]]

    translator = HuggingFaceTranslator()
    translator._backend = (FakeTorch, FakeTokenizer(), FakeModel(), "cpu")

    assert translator._translate_chunk("Hello") == "Bonjour"
    assert calls["device"] == "cpu"
    generate_kwargs = calls["generate"]
    assert isinstance(generate_kwargs, dict)
    assert "input_ids" in generate_kwargs
    assert generate_kwargs["max_length"] == 512
    assert "max_new_tokens" not in generate_kwargs


def test_split_text_for_translation_respects_token_budget() -> None:
    text = "alpha beta gamma. delta epsilon zeta. eta theta iota."

    chunks = _split_text_for_translation(
        text,
        max_chars=200,
        max_tokens=4,
        token_length=lambda value: len(value.split()),
    )

    assert len(chunks) == 3
    assert all(len(chunk.split()) <= 4 for chunk in chunks)


def test_split_text_for_translation_splits_single_overlong_sentence_on_spaces() -> None:
    text = "un deux trois quatre cinq six sept huit neuf dix"

    chunks = _split_text_for_translation(text, max_chars=12)

    assert len(chunks) > 1
    assert all(len(chunk) <= 12 for chunk in chunks)
    assert " ".join(chunks) == text
