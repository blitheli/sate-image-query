from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from sate_image_query.models import HealthResult, Modality, Scene, SearchQuery
from sate_image_query.sources.base import DataSource


def _iso_odata(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _bbox_polygon_wkt(bbox: tuple[float, float, float, float]) -> str:
    min_lon, min_lat, max_lon, max_lat = bbox
    return (
        f"POLYGON (({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )


def _geometry_bbox(q: SearchQuery) -> tuple[float, float, float, float]:
    if q.bbox is not None:
        return q.bbox
    if q.point is not None:
        lon, lat = q.point
        d = 0.02
        return (lon - d, lat - d, lon + d, lat + d)
    raise ValueError("SearchQuery requires bbox or point")


class CDSESource(DataSource):
    def _token(self) -> str:
        import os

        user = os.environ.get("COPERNICUS_USERNAME")
        pwd = os.environ.get("COPERNICUS_PASSWORD")
        if not user or not pwd:
            raise RuntimeError("Set COPERNICUS_USERNAME and COPERNICUS_PASSWORD in environment or .env")
        token_url = self.config.get(
            "token_url",
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        )
        client_id = self.config.get("client_id", "cdse-public")
        data = {
            "grant_type": "password",
            "username": user,
            "password": pwd,
            "client_id": client_id,
        }
        r = httpx.post(token_url, data=data, timeout=60.0)
        r.raise_for_status()
        js = r.json()
        tok = js.get("access_token")
        if not tok:
            raise RuntimeError(f"No access_token in response: {js}")
        return str(tok)

    def _product_type(self, modality: Modality) -> str:
        if modality == Modality.SAR:
            return str(self.config.get("product_type_sar", "S1GRD"))
        if modality == Modality.OPTICAL:
            return str(self.config.get("product_type_optical", "S2MSI2A"))
        return str(self.config.get("product_type_optical", "S2MSI2A"))

    def health_check(self, smoke_search: bool = False) -> HealthResult:
        try:
            _ = self._token()
        except Exception as e:
            return HealthResult(False, str(e), self.source_id)
        if not smoke_search:
            return HealthResult(True, "OAuth token obtained", self.source_id)
        base = self.config["base_url"].rstrip("/")
        try:
            token = self._token()
            bbox = (-1.0, 50.0, 0.0, 51.0)
            wkt = _bbox_polygon_wkt(bbox)
            pt = self._product_type(Modality.OPTICAL)
            start = _iso_odata(datetime(2020, 6, 1, tzinfo=timezone.utc))
            end = _iso_odata(datetime(2020, 6, 15, tzinfo=timezone.utc))
            filt = (
                f"Collection/Name eq 'SENTINEL-2' and "
                f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and "
                f"att/OData.CSC.StringAttribute/Value eq '{pt}') and "
                f"ContentDate/Start lt {end} and ContentDate/End gt {start} and "
                f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')"
            )
            url = f"{base}/Products?$filter={urllib.parse.quote(filt)}&$top=1&$orderby=ContentDate/Start desc"
            r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60.0)
            r.raise_for_status()
            data = r.json()
            n = len(data.get("value", []))
            return HealthResult(True, f"Smoke OData returned {n} product(s)", self.source_id)
        except Exception as e:
            return HealthResult(False, str(e), self.source_id)

    def search(self, query: SearchQuery) -> list[Scene]:
        token = self._token()
        base = self.config["base_url"].rstrip("/")
        bbox = _geometry_bbox(query)
        wkt = _bbox_polygon_wkt(bbox)
        pt = self._product_type(query.modality)
        coll = "SENTINEL-2" if query.modality != Modality.SAR else "SENTINEL-1"
        start = _iso_odata(query.start)
        end = _iso_odata(query.end)
        filt = (
            f"Collection/Name eq '{coll}' and "
            f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and "
            f"att/OData.CSC.StringAttribute/Value eq '{pt}') and "
            f"ContentDate/Start lt {end} and ContentDate/End gt {start} and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')"
        )
        url = (
            f"{base}/Products?$filter={urllib.parse.quote(filt)}"
            f"&$top={query.limit}&$orderby=ContentDate/Start desc"
        )
        r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=120.0)
        r.raise_for_status()
        data = r.json()
        scenes: list[Scene] = []
        for row in data.get("value", []):
            pid = str(row.get("Id", ""))
            name = str(row.get("Name", pid))
            dl = f"{base}/Products({pid})/$value"
            cd_start = row.get("ContentDate", {}).get("Start")
            dt_parsed: datetime | None = None
            if isinstance(cd_start, str):
                try:
                    dt_parsed = datetime.fromisoformat(cd_start.replace("Z", "+00:00"))
                except Exception:
                    dt_parsed = None
            scenes.append(
                Scene(
                    id=name,
                    source_id=self.source_id,
                    collection=coll,
                    datetime=dt_parsed,
                    geometry=None,
                    assets={"product": dl},
                    extra={"odata_id": pid, "raw": row},
                )
            )
        return scenes

    def download(
        self,
        scene: Scene,
        dest_dir: Path,
        asset_keys: list[str] | None = None,
    ) -> list[Path]:
        token = self._token()
        dest_dir.mkdir(parents=True, exist_ok=True)
        href = scene.assets.get("product")
        if not href:
            raise ValueError("Scene has no product download URL")
        name = f"{scene.id}.zip" if not scene.id.endswith(".zip") else scene.id
        out = dest_dir / name.replace("/", "_")
        with httpx.stream(
            "GET",
            href,
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=True,
            timeout=600.0,
        ) as r:
            r.raise_for_status()
            with open(out, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return [out]
