from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pystac_client import Client
from shapely.geometry import Point, box, mapping

from sate_image_query.models import HealthResult, Modality, Scene, SearchQuery
from sate_image_query.sources.base import DataSource

import planetary_computer as pc


def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _geometry_for_query(q: SearchQuery) -> dict[str, Any]:
    if q.bbox is not None:
        min_lon, min_lat, max_lon, max_lat = q.bbox
        return mapping(box(min_lon, min_lat, max_lon, max_lat))
    if q.point is not None:
        lon, lat = q.point
        b = Point(lon, lat).buffer(0.02)
        return mapping(b)
    raise ValueError("SearchQuery requires bbox or point")


def _spatial_resolution_note(collection_id: str | None) -> str:
    if not collection_id:
        return "见 STAC collection 与 item 元数据"
    c = collection_id.lower()
    if "sentinel-2" in c or "sentinel2" in c:
        return "MSI L2A: 10 m / 20 m / 60 m (依波段; 真彩色 TCI 为 10 m)"
    if "landsat" in c:
        return "OLI/TIRS C2 L2: 30 m (多光谱/热红外), 15 m (全色 Pan)"
    if "sentinel-1" in c:
        return "C-SAR GRD: 地面分辨率依条带模式与产品等级而异"
    return "见 STAC collection 与 item 元数据"


def _collections_for_modality(cfg: dict[str, Any], modality: Modality, override: list[str] | None) -> list[str]:
    if override:
        return override
    optical = cfg.get("default_collections_optical") or []
    sar = cfg.get("default_collections_sar") or []
    if modality == Modality.OPTICAL:
        return list(optical)
    if modality == Modality.SAR:
        return list(sar)
    if modality == Modality.DEM:
        return list(cfg.get("default_collections_dem") or [])
    return list(dict.fromkeys([*optical, *sar]))


class STACSource(DataSource):
    def health_check(self, smoke_search: bool = False) -> HealthResult:
        url = self.config.get("base_url", "")
        if not url:
            return HealthResult(False, "No base_url", self.source_id)
        try:
            client = Client.open(url)
            _ = client.get_collections()
            if not smoke_search:
                return HealthResult(True, "Catalog opened", self.source_id)
            cols = _collections_for_modality(self.config, Modality.ANY, None)
            if not cols:
                return HealthResult(True, "Catalog opened (no default collections for smoke)", self.source_id)
            geom = mapping(box(-122.5, 37.7, -122.3, 37.9))
            search = client.search(
                collections=[cols[0]],
                intersects=geom,
                datetime="2020-01-01T00:00:00Z/2020-02-01T00:00:00Z",
                max_items=1,
            )
            n = len(list(search.items()))
            return HealthResult(True, f"Smoke search returned {n} item(s)", self.source_id)
        except Exception as e:
            return HealthResult(False, str(e), self.source_id)

    def search(self, query: SearchQuery) -> list[Scene]:
        catalog_url = self.config["base_url"]
        client = Client.open(catalog_url)
        collections = _collections_for_modality(self.config, query.modality, query.collections)
        if not collections:
            raise ValueError("No collections to search; set modality or pass collections")
        geom = _geometry_for_query(query)
        dt = f"{_iso_z(query.start)}/{_iso_z(query.end)}"
        kwargs: dict[str, Any] = {
            "collections": collections,
            "intersects": geom,
            "datetime": dt,
            "max_items": query.limit,
        }
        qdict: dict[str, Any] = {}
        if query.cloud_cover_max is not None and query.modality != Modality.SAR:
            qdict["eo:cloud_cover"] = {"lt": query.cloud_cover_max}
        if qdict:
            kwargs["query"] = qdict
        search = client.search(**kwargs)
        scenes: list[Scene] = []
        for item in search.items():
            if "planetarycomputer.microsoft.com" in catalog_url:
                item = pc.sign(item)
            assets: dict[str, str] = {}
            for key, asset in item.assets.items():
                if asset.href:
                    assets[key] = asset.href
            dt_prop = item.datetime
            if dt_prop is None and item.properties.get("datetime"):
                try:
                    raw = item.properties["datetime"]
                    if isinstance(raw, str):
                        dt_prop = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except Exception:
                    dt_prop = None
            props = item.properties or {}
            cc = props.get("eo:cloud_cover")
            extra: dict[str, Any] = {
                "stac_href": item.self_href,
                "cloud_cover_pct": cc,
                "spatial_resolution": _spatial_resolution_note(item.collection_id),
            }
            scenes.append(
                Scene(
                    id=item.id,
                    source_id=self.source_id,
                    collection=item.collection_id,
                    datetime=dt_prop,
                    geometry=item.geometry,
                    assets=assets,
                    extra=extra,
                )
            )
        return scenes

    def download(
        self,
        scene: Scene,
        dest_dir: Path,
        asset_keys: list[str] | None = None,
    ) -> list[Path]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        keys = asset_keys
        if not keys:
            preferred = ["visual", "thumbnail", "B04", "VV"]
            keys = [k for k in preferred if k in scene.assets]
            if not keys and scene.assets:
                keys = [next(iter(scene.assets.keys()))]
        paths: list[Path] = []
        for k in keys:
            href = scene.assets.get(k)
            if not href:
                continue
            name = href.split("?")[0].rstrip("/").split("/")[-1] or f"{scene.id}_{k}"
            out = dest_dir / name
            with httpx.stream("GET", href, follow_redirects=True, timeout=120.0) as r:
                r.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            paths.append(out)
        return paths
