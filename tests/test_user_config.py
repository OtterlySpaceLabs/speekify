from __future__ import annotations

import pytest

from speekify.user_config import default_config_path, load_user_config


def test_load_user_config_reads_generation_defaults(tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    output_dir = tmp_path / "audio"
    config_path.write_text(
        "\n".join(
            [
                "[generation]",
                'voice = "f2"',
                'lang = "EN"',
                "speed = 1.1",
                "steps = 12",
                "max_chunk_length = 220",
                "silence_duration = 0.3",
                "english_islands = false",
                f'output_dir = "{output_dir}"',
            ]
        ),
        encoding="utf-8",
    )

    config = load_user_config(config_path)

    assert config.voice == "F2"
    assert config.language_code == "en"
    assert config.speed == 1.1
    assert config.steps == 12
    assert config.max_chunk_length == 220
    assert config.silence_duration == 0.3
    assert config.english_islands is False
    assert config.output_dir == output_dir


def test_default_config_path_honors_environment(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "speekify.toml"
    monkeypatch.setenv("SPEEKIFY_CONFIG", str(config_path))

    assert default_config_path() == config_path


def test_load_user_config_rejects_wrong_value_types(tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[generation]\nsteps = true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="steps"):
        load_user_config(config_path)