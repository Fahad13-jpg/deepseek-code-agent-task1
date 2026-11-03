"""Runtime settings with a small JSON override path.

The game works with built-in defaults, so no configuration file is required.
If a ``config.json`` exists next to the project, values in it replace the
defaults. See ``config.example.json`` for the available keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "question_count": 10,
    "starting_lives": 3,
    "seconds_per_question": 30,
    "base_points": 10,
    "difficulty_bonus": 5,
    "streak_bonus": 2,
    "max_streak_bonus": 5,
    "feedback_delay_ms": 1700,
}

ALLOWED_KEYS = set(DEFAULT_SETTINGS)


def _coerce_settings(raw: dict[str, Any]) -> dict[str, Any]:
    result = dict(DEFAULT_SETTINGS)
    for key, value in raw.items():
        if key not in ALLOWED_KEYS:
            continue
        try:
            result[key] = int(value)
        except (TypeError, ValueError):
            # Ignore invalid values and keep the safe default.
            continue
    result["question_count"] = max(1, result["question_count"])
    result["starting_lives"] = max(1, result["starting_lives"])
    result["seconds_per_question"] = max(5, result["seconds_per_question"])
    result["feedback_delay_ms"] = max(200, result["feedback_delay_ms"])
    return result


def load_settings(path: str | Path = "config.json") -> dict[str, Any]:
    """Load settings, falling back to defaults if the file is absent/invalid."""
    config_path = Path(path)
    if not config_path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return dict(DEFAULT_SETTINGS)
    return _coerce_settings(raw)
