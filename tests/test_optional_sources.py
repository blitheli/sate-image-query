import os
from pathlib import Path

import pytest

from sate_image_query.catalog import get_source_by_id, load_sources_config
from sate_image_query.sources import create_source


@pytest.mark.requires_credentials
@pytest.mark.integration
def test_cdse_health_when_configured() -> None:
    if not os.environ.get("COPERNICUS_USERNAME") or not os.environ.get("COPERNICUS_PASSWORD"):
        pytest.skip("COPERNICUS_USERNAME / COPERNICUS_PASSWORD not set")
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    cfg = get_source_by_id(data, "cdse-odata")
    src = create_source("cdse-odata", cfg)
    hr = src.health_check(smoke_search=False)
    assert hr.ok, hr.message


@pytest.mark.requires_credentials
@pytest.mark.integration
def test_usgs_health_when_configured() -> None:
    if not os.environ.get("USGS_M2M_USERNAME") or not os.environ.get("USGS_M2M_PASSWORD"):
        pytest.skip("USGS_M2M_USERNAME / USGS_M2M_PASSWORD not set")
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    cfg = get_source_by_id(data, "usgs-m2m")
    src = create_source("usgs-m2m", cfg)
    hr = src.health_check(smoke_search=False)
    assert hr.ok, hr.message


def test_web_manual_search_not_implemented() -> None:
    from datetime import datetime, timezone

    from sate_image_query.models import SearchQuery

    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    cfg = get_source_by_id(data, "gscloud-web")
    src = create_source("gscloud-web", cfg)
    q = SearchQuery(
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        end=datetime(2020, 2, 1, tzinfo=timezone.utc),
        bbox=(0, 0, 1, 1),
    )
    with pytest.raises(NotImplementedError):
        src.search(q)
