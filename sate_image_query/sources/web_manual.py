from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from sate_image_query.models import HealthResult, Scene, SearchQuery
from sate_image_query.sources.base import DataSource


class WebManualSource(DataSource):
    """Placeholder for portals without a stable programmatic API."""

    def health_check(self, smoke_search: bool = False) -> HealthResult:
        url = self.config.get("base_url", "")
        if not url:
            return HealthResult(False, "No base_url", self.source_id)
        try:
            r = httpx.head(url, follow_redirects=True, timeout=15.0)
            if r.status_code < 400:
                return HealthResult(True, f"HTTP {r.status_code} (manual access only)", self.source_id)
            r2 = httpx.get(url, follow_redirects=True, timeout=15.0)
            ok = r2.status_code < 400
            return HealthResult(
                ok,
                f"HTTP {r2.status_code}; web_manual — no automated search",
                self.source_id,
            )
        except Exception as e:
            return HealthResult(False, str(e), self.source_id)

    def search(self, query: SearchQuery) -> list[Scene]:
        raise NotImplementedError(
            f"Source {self.source_id} requires manual web workflow; automated search is not implemented."
        )

    def download(self, scene: Scene, dest_dir: Path, asset_keys: list[str] | None = None) -> list[Path]:
        raise NotImplementedError(f"Source {self.source_id} does not support programmatic download.")
