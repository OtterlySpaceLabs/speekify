from pathlib import Path

import pytest

from speekify.batch import expand_batch_sources


def test_expand_batch_sources_recurses_sorts_and_deduplicates(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    nested = docs / "nested"
    nested.mkdir(parents=True)
    (docs / "b.md").write_text("B", encoding="utf-8")
    (nested / "a.txt").write_text("A", encoding="utf-8")
    (docs / "ignored.json").write_text("{}", encoding="utf-8")

    expanded = expand_batch_sources([str(docs), str(docs / "b.md")])

    assert [item.relative_path for item in expanded.items] == ["b.md", "nested/a.txt"]
    assert any("unsupported" in warning for warning in expanded.warnings)
    assert any("Duplicate" in warning for warning in expanded.warnings)


def test_expand_batch_sources_rejects_explicit_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(source)

    with pytest.raises(ValueError, match="Symbolic"):
        expand_batch_sources([str(link)])


def test_expand_batch_sources_rejects_empty_directory(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(ValueError, match="No supported"):
        expand_batch_sources([str(empty)])
