from datetime import datetime, timezone
from pathlib import Path

import pytest

from sate_image_query.catalog import get_source_by_id, load_sources_config
from sate_image_query.models import Modality, SearchQuery
from sate_image_query.sources import create_source


@pytest.mark.integration
def test_mpc_stac_health() -> None:
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    cfg = get_source_by_id(data, "mpc-stac")
    src = create_source("mpc-stac", cfg)
    hr = src.health_check(smoke_search=False)
    assert hr.ok, hr.message


@pytest.mark.integration
def test_mpc_stac_smoke_search() -> None:
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    cfg = get_source_by_id(data, "mpc-stac")
    src = create_source("mpc-stac", cfg)
    hr = src.health_check(smoke_search=True)
    assert hr.ok, hr.message


@pytest.mark.integration
def test_mpc_stac_search_limited() -> None:
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    cfg = get_source_by_id(data, "mpc-stac")
    src = create_source("mpc-stac", cfg)
    q = SearchQuery(
        start=datetime(2020, 6, 1, tzinfo=timezone.utc),
        end=datetime(2020, 6, 15, tzinfo=timezone.utc),
        modality=Modality.OPTICAL,
        bbox=(-122.5, 37.7, -122.3, 37.9),
        collections=["sentinel-2-l2a"],
        limit=2,
    )
    scenes = src.search(q)
    assert len(scenes) <= 2
    assert all(s.assets for s in scenes)
