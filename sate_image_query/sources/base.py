from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from sate_image_query.models import HealthResult, Scene, SearchQuery


class DataSource(ABC):
    """Pluggable backend for search and download."""

    def __init__(self, source_id: str, config: dict[str, Any]) -> None:
        self.source_id = source_id
        self.config = config

    @abstractmethod
    def health_check(self, smoke_search: bool = False) -> HealthResult:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: SearchQuery) -> list[Scene]:
        raise NotImplementedError

    def download(
        self,
        scene: Scene,
        dest_dir: Path,
        asset_keys: list[str] | None = None,
    ) -> list[Path]:
        """Default: no-op for sources that do not support programmatic download."""
        raise NotImplementedError
