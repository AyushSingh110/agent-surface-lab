"""Config tests: seed offset for replays, YAML override, and loud failure on bad keys."""
from __future__ import annotations

from pathlib import Path

import pytest

from harness.config import Config, load_config


def test_sampling_options_offsets_seed() -> None:
    c = Config(seed=100, temperature=0.7)
    assert c.sampling_options(0) == {"temperature": 0.7, "seed": 100}
    assert c.sampling_options(3) == {"temperature": 0.7, "seed": 103}


def test_sampling_options_negative_raises() -> None:
    with pytest.raises(ValueError):
        Config().sampling_options(-1)


def test_load_config_yaml_override(tmp_path: Path) -> None:
    yaml_path = tmp_path / "cfg.yaml"
    yaml_path.write_text("n_replays: 5\nmax_turns: 20\ntemperature: 0.9\n", encoding="utf-8")
    cfg = load_config(yaml_path)
    assert cfg.n_replays == 5
    assert cfg.max_turns == 20
    assert cfg.temperature == 0.9


def test_load_config_unknown_key_raises(tmp_path: Path) -> None:
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text("not_a_real_key: 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(yaml_path)


def test_load_config_missing_yaml_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")
