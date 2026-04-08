from sate_image_query.sources.base import DataSource
from sate_image_query.sources.cdse import CDSESource
from sate_image_query.sources.stac import STACSource
from sate_image_query.sources.usgs import USGSSource
from sate_image_query.sources.web_manual import WebManualSource

__all__ = [
    "DataSource",
    "STACSource",
    "CDSESource",
    "USGSSource",
    "WebManualSource",
    "create_source",
]


def create_source(source_id: str, config: dict) -> DataSource:
    kind = config.get("api_kind", "")
    if kind == "stac":
        return STACSource(source_id, config)
    if kind == "cdse_odata":
        return CDSESource(source_id, config)
    if kind == "usgs_m2m":
        return USGSSource(source_id, config)
    if kind == "web_manual":
        return WebManualSource(source_id, config)
    raise ValueError(f"Unsupported api_kind: {kind}")
