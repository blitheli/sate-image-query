from pathlib import Path

import pytest

from sate_image_query.catalog import get_source_by_id, load_sources_config


def test_load_sources_yaml() -> None:
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    assert "sources" in data
    ids = {s["id"] for s in data["sources"]}
    assert "mpc-stac" in ids
    assert "aws-earth-search" in ids


def test_get_source_by_id() -> None:
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    s = get_source_by_id(data, "mpc-stac")
    assert s["api_kind"] == "stac"


def test_aws_earth_search_source() -> None:
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    s = get_source_by_id(data, "aws-earth-search")
    assert s["api_kind"] == "stac"
    assert "earth-search.aws.element84.com" in s["base_url"]


def test_unknown_source() -> None:
    root = Path(__file__).resolve().parent.parent
    data = load_sources_config(root / "config" / "sources.yaml")
    with pytest.raises(KeyError):
        get_source_by_id(data, "nonexistent")
