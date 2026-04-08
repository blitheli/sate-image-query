from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def load_sources_config(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def get_source_by_id(sources_data: dict[str, Any], source_id: str) -> dict[str, Any]:
    for s in sources_data.get("sources", []):
        if s.get("id") == source_id:
            return s
    raise KeyError(f"Unknown source id: {source_id}")


def env_or_none(key: str) -> str | None:
    v = os.environ.get(key)
    return v if v else None
