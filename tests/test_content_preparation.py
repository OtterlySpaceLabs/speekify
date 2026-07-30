from __future__ import annotations

import pytest

from speekify.content_preparation import prepare_content_for_speech


def test_prepare_content_preserves_useful_markdown_and_removes_non_spoken_blocks() -> None:
    source = """---
title: "Guide"
source: "https://example.com/source"
created: 2026-07-29
tags:
  - clippings
---
# Guide Speekify

![Architecture](architecture.svg)
[![Badge](badge.png)](https://example.com/status)

Consultez [la documentation](https://example.com/docs) et utilisez `speekify`.

- Premier point
- Deuxième point

```python
print("ce code ne doit pas être prononcé")
```

~~~html
<img src="secret.png" alt="secret">
~~~
"""

    assert prepare_content_for_speech(source) == (
        "Guide Speekify\n\n"
        "Consultez la documentation et utilisez speekify.\n\n"
        "Premier point\n\n"
        "Deuxième point"
    )


def test_prepare_content_keeps_horizontal_rules_that_are_not_yaml_metadata() -> None:
    assert prepare_content_for_speech("---\n\nIntroduction\n\n---\n\nConclusion") == (
        "Introduction\n\nConclusion"
    )


def test_prepare_content_removes_emoji_but_keeps_ordinary_text_and_symbols() -> None:
    source = """Phase 2

~19 min de lecture

> ### 🔧 Pour le builder
> Une équipe 👨🏽‍💻 prête ✅.

> ### 🎯 Pour le stratège
> Étape 1️⃣: décider.
"""

    assert prepare_content_for_speech(source) == (
        "Phase 2\n\n"
        "~19 min de lecture\n\n"
        "Pour le builder\n\n"
        "Une équipe prête.\n\n"
        "Pour le stratège\n\n"
        "Étape 1: décider."
    )


def test_prepare_content_removes_html_media_code_and_hidden_decoration() -> None:
    source = """
<article>
  <h1>Compte rendu</h1>
  <img src="chart.png" alt="Graphique des ventes">
  <p>Une <a href="https://example.com">analyse utile</a>.</p>
  <svg><title>Logo</title><text>Texte vectoriel</text></svg>
  <audio><source src="intro.mp3">Lecteur audio</audio>
  <video><track src="captions.vtt">Lecteur vidéo</video>
  <canvas>Graphique de décoration</canvas>
  <pre><code>print("bloc technique")</code></pre>
  <p>Valeur <code>API</code> conservée.</p>
  <span aria-hidden="true">Étoile décorative</span>
</article>
"""

    assert prepare_content_for_speech(source) == (
        "Compte rendu\n\n"
        "Une analyse utile.\n\n"
        "Valeur API conservée."
    )


def test_prepare_content_makes_markdown_table_readable_for_speech() -> None:
    source = """| Produit | Prix | Stock |
| --- | ---: | :---: |
| Thé | 3 € | Oui |
| Café ⭐ | 4 € | Non |
"""

    assert prepare_content_for_speech(source) == (
        "Produit : Thé ; Prix : 3 € ; Stock : Oui.\n"
        "Produit : Café ; Prix : 4 € ; Stock : Non."
    )


def test_prepare_content_makes_html_table_readable_for_speech() -> None:
    source = """
<table>
  <thead><tr><th>Nom</th><th>Rôle</th></tr></thead>
  <tbody>
    <tr><td>Ada</td><td>Ingénieure</td></tr>
    <tr><td>Linus</td><td>Mainteneur</td></tr>
  </tbody>
</table>
"""

    assert prepare_content_for_speech(source) == (
        "Nom : Ada ; Rôle : Ingénieure.\n"
        "Nom : Linus ; Rôle : Mainteneur."
    )


def test_prepare_content_rejects_content_made_only_of_non_spoken_elements() -> None:
    with pytest.raises(ValueError, match="suitable for speech"):
        prepare_content_for_speech(
            "![Illustration](image.png)\n\n```python\nprint('silence')\n```"
        )
