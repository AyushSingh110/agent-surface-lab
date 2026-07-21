"""Run configuration — a single dataclass that every experiment logs.

Reproducibility rule (CLAUDE.md §4): every run must set and log its seed, the
backbone model/tag, and the sampling parameters. This module is the one place
those live, loaded from `.env` (via python-dotenv) with optional YAML override,
so nothing is scattered as hardcoded constants.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Immutable run configuration.

    Attributes:
        ollama_host: Base URL of the local Ollama server.
        model_tag: The pinned backbone model tag (e.g. "qwen2.5:7b"). Logged on
            every trace and every replay so results are attributable to a model.
        seed: Global random seed, logged with every run and every replay.
        temperature: Sampling temperature. 0.0 gives near-deterministic single
            samples; >0 is used when we deliberately want a recovery distribution.
        n_replays: Default number of replays per (intervention, trace) cell.
            Per §8 item 10 this is a FLOOR of 3 for real runs; N=1 is allowed for
            fast iteration. The metrics layer may request a higher N per cell.
        max_turns: Hard cap on agent steps per run, so a looping agent terminates.
    """

    ollama_host: str = "http://localhost:11434"
    model_tag: str = "qwen2.5:7b"
    seed: int = 20260721
    temperature: float = 0.0
    n_replays: int = 3
    max_turns: int = 12

    def sampling_options(self, replay_index: int = 0) -> dict[str, Any]:
        """Return Ollama sampling options for one (re)play.

        The seed is offset by ``replay_index`` so that the N replays in a cell are
        distinct-but-reproducible samples rather than N identical draws. With
        temperature 0 the model is near-deterministic and the offset mostly serves
        as an audit trail; with temperature > 0 it makes the N draws genuinely
        independent while remaining exactly reproducible from (seed, replay_index).

        Args:
            replay_index: Which replay in the cell this is (0-based).

        Returns:
            A dict suitable for the Ollama client's ``options`` argument.
        """
        if replay_index < 0:
            raise ValueError(f"replay_index must be >= 0, got {replay_index}")
        return {"temperature": self.temperature, "seed": self.seed + replay_index}

    def to_log_dict(self) -> dict[str, Any]:
        """Config as a plain dict for embedding in trace/replay records."""
        return asdict(self)


def load_config(yaml_path: str | Path | None = None) -> Config:
    """Build a Config from `.env` values, optionally overridden by a YAML file.

    Precedence (lowest to highest): dataclass defaults < `.env` < YAML file.
    We fail loudly on an unreadable YAML rather than silently ignoring it, because
    a silently-dropped config is a reproducibility hole (CLAUDE.md §4).

    Args:
        yaml_path: Optional path to a YAML file whose keys override env/defaults.

    Returns:
        A frozen Config.
    """
    load_dotenv()

    values: dict[str, Any] = {}
    if (host := os.getenv("OLLAMA_HOST")) is not None:
        values["ollama_host"] = host
    if (model := os.getenv("OLLAMA_MODEL")) is not None:
        values["model_tag"] = model
    if (seed := os.getenv("SEED")) is not None:
        values["seed"] = int(seed)

    if yaml_path is not None:
        path = Path(yaml_path)
        if not path.is_file():
            raise FileNotFoundError(f"config YAML not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            overrides = yaml.safe_load(fh) or {}
        if not isinstance(overrides, dict):
            raise ValueError(f"config YAML must be a mapping, got {type(overrides).__name__}")
        allowed = set(Config().__dataclass_fields__.keys())  # type: ignore[attr-defined]
        unknown = set(overrides) - allowed
        if unknown:
            raise ValueError(f"unknown config keys in {path}: {sorted(unknown)}")
        values.update(overrides)

    return Config(**values)
