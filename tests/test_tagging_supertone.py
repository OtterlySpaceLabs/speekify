from speekify.tagging import SentimentResult, SupertoneTagger, TaggingConfig


class NegativeSentimentAnalyzer:
    def analyze(self, document):
        return tuple(
            SentimentResult(
                sentence_index=sentence.index,
                label="negative",
                confidence=0.99,
            )
            for sentence in document.sentences
        )


class FailingSentimentAnalyzer:
    def analyze(self, document):
        raise RuntimeError("sentiment unavailable")


def test_rules_only_tagger_keeps_short_text_untagged() -> None:
    result = SupertoneTagger().tag("Bonjour tout le monde.", language_code="fr")

    assert result.changed is False
    assert result.text == "Bonjour tout le monde."
    assert result.tag_counts == {}


def test_rules_only_tagger_adds_sparse_breaths_without_rewriting_paragraphs() -> None:
    text = (
        "Cette première phrase installe un contexte éditorial dense avec plusieurs détails "
        "successifs, afin de créer un point de respiration naturel après une unité complète. "
        "La suite du paragraphe reste sobre et informative pour garder de la matière après le tag.\n\n"
        "Cette deuxième phrase reprend le fil avec une analyse longue et structurée, suffisamment "
        "développée pour justifier une respiration sans changer le texte original. "
        "Un dernier segment maintient la cadence journalistique."
    )
    config = TaggingConfig(
        min_text_chars_for_tags=100,
        min_sentence_chars_for_breath=120,
        min_paragraph_chars_for_breath=160,
        min_chars_between_tags=80,
        min_chars_after_tag=20,
        breath_chars_per_tag=220,
    )

    result = SupertoneTagger(config=config).tag(text, language_code="fr")

    assert result.text.count("<breath>") == 2
    assert all(insertion.tag == "<breath>" for insertion in result.insertions)
    assert len({insertion.sentence_index for insertion in result.insertions}) == 2
    assert result.text.replace(" <breath>", "") == text
    assert "\n\n" in result.text
    assert "<sigh>" not in result.text


def test_sentiment_errors_fail_open_to_rules_only() -> None:
    text = (
        "Cette phrase assez longue contient beaucoup de contexte pour autoriser une respiration "
        "naturelle à cet endroit précis de la narration. "
        "Une phrase finale conserve un peu de texte après le point choisi."
    )
    config = TaggingConfig(
        use_sentiment=True,
        min_text_chars_for_tags=100,
        min_sentence_chars_for_breath=100,
        min_chars_after_tag=20,
        breath_chars_per_tag=120,
    )

    result = SupertoneTagger(
        config=config,
        sentiment_analyzer=FailingSentimentAnalyzer(),
    ).tag(text, language_code="fr")

    assert "<breath>" in result.text
    assert result.sentiment_used is False


def test_sigh_stays_exceptional_even_with_negative_sentiment() -> None:
    text = (
        "Cette tragédie a provoqué une crise profonde dans la ville, avec un récit long et grave "
        "qui appelle une pause émotionnelle mesurée après cette phrase. "
        "La suite revient aux faits avec une formulation sobre et informative.\n\n"
        "Une autre crise est mentionnée dans un second paragraphe, mais la narration doit rester "
        "contenue et ne pas multiplier les soupirs artificiels. "
        "La conclusion garde une distance journalistique."
    )
    config = TaggingConfig(
        use_sentiment=True,
        enable_sigh=True,
        min_text_chars_for_tags=100,
        min_sentence_chars_for_breath=100,
        min_chars_between_tags=80,
        min_chars_after_tag=20,
        breath_chars_per_tag=180,
        max_sighs=1,
        negative_sigh_threshold=0.9,
    )

    result = SupertoneTagger(
        config=config,
        sentiment_analyzer=NegativeSentimentAnalyzer(),
    ).tag(text, language_code="fr")

    assert result.text.count("<sigh>") == 1
    assert result.tag_counts["<sigh>"] == 1