from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_render_homebrew_formula_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "render_homebrew_formula.py"
    spec = importlib.util.spec_from_file_location("render_homebrew_formula", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load render_homebrew_formula.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manpage_mentions_doctor_and_setup() -> None:
    manpage_path = Path(__file__).resolve().parents[1] / "docs" / "man" / "speekify.1"
    content = manpage_path.read_text(encoding="utf-8")

    assert "speekify --doctor" in content
    assert "speekify setup" in content
    assert "Supertonic v3" in content


def test_render_formula_installs_manpage_and_checks_help() -> None:
    module = _load_render_homebrew_formula_module()

    formula = module.render_formula(
        version="0.0.3",
        url="https://example.com/speekify.tar.gz",
        sha256="deadbeef",
        homepage="https://example.com/speekify",
    )

    # onedir install: libexec dir + bin symlink, not a bare bin.install.
    assert 'libexec.install "speekify"' in formula
    assert 'bin.install_symlink libexec/"speekify/speekify"' in formula
    assert 'man1.install "share/man/man1/speekify.1"' in formula
    assert 'assert_match "speekify --doctor", shell_output("#{bin}/speekify --help")' in formula
    assert 'assert_match "0.0.3", shell_output("#{bin}/speekify --version")' in formula
    assert 'assert_predicate man1/"speekify.1", :exist?' in formula