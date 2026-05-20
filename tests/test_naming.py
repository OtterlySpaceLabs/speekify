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
