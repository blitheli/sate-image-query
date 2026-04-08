from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal


class Modality(str, Enum):
    OPTICAL = "optical"
    SAR = "sar"
    DEM = "dem"
    ANY = "any"


@dataclass
class SearchQuery:
    """Unified search parameters across adapters."""

    start: datetime
    end: datetime
    modality: Modality = Modality.ANY
    bbox: tuple[float, float, float, float] | None = None
    """min_lon, min_lat, max_lon, max_lat in WGS84."""
    point: tuple[float, float] | None = None
    """lon, lat; if set without bbox, adapters may use a small buffer."""
    collections: list[str] | None = None
    cloud_cover_max: float | None = None
    limit: int = 50


@dataclass
class Scene:
    """One granule / scene / product."""

    id: str
    source_id: str
    collection: str | None
    datetime: datetime | None
    geometry: dict[str, Any] | None
    assets: dict[str, str] = field(default_factory=dict)
    """asset_key -> download href (may be signed)."""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthResult:
    ok: bool
    message: str
    source_id: str


@dataclass
class DownloadResult:
    paths: list[Path]
    errors: list[str] = field(default_factory=list)
