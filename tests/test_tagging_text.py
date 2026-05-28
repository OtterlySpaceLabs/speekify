from speekify.tagging.text import TextPreprocessor


def test_text_preprocessor_preserves_paragraph_spans() -> None:
    text = "Premier paragraphe. Encore une phrase.\n\nDeuxième paragraphe plus court."

    document = TextPreprocessor().process(text, language_code="FR")

    assert document.language_code == "fr"
    assert [paragraph.slice(text) for paragraph in document.paragraphs] == [
        "Premier paragraphe. Encore une phrase.",
        "Deuxième paragraphe plus court.",
    ]
    assert text[document.paragraphs[0].end : document.paragraphs[1].start] == "\n\n"
    assert [sentence.slice(text) for sentence in document.sentences] == [
        "Premier paragraphe.",
        "Encore une phrase.",
        "Deuxième paragraphe plus court.",
    ]