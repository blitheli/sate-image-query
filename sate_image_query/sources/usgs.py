from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from sate_image_query.models import HealthResult, Modality, Scene, SearchQuery
from sate_image_query.sources.base import DataSource


def _iso_date(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _mbr(q: SearchQuery) -> dict[str, Any]:
    if q.bbox is not None:
        min_lon, min_lat, max_lon, max_lat = q.bbox
        return {
            "filterType": "mbr",
            "lowerLeft": {"latitude": min_lat, "longitude": min_lon},
            "upperRight": {"latitude": max_lat, "longitude": max_lon},
        }
    if q.point is not None:
        lon, lat = q.point
        d = 0.05
        return {
            "filterType": "mbr",
            "lowerLeft": {"latitude": lat - d, "longitude": lon - d},
            "upperRight": {"latitude": lat + d, "longitude": lon + d},
        }
    raise ValueError("SearchQuery requires bbox or point")


class USGSSource(DataSource):
    def __init__(self, source_id: str, config: dict[str, Any]) -> None:
        super().__init__(source_id, config)
        self._base = config["base_url"].rstrip("/")

    def _login(self) -> str:
        import os

        user = os.environ.get("USGS_M2M_USERNAME")
        pwd = os.environ.get("USGS_M2M_PASSWORD")
        if not user or not pwd:
            raise RuntimeError("Set USGS_M2M_USERNAME and USGS_M2M_PASSWORD")
        url = f"{self._base}/login"
        r = httpx.post(url, json={"username": user, "password": pwd}, timeout=60.0)
        r.raise_for_status()
        data = r.json()
        if data.get("errorCode") and data.get("errorCode") != "NONE":
            raise RuntimeError(data.get("errorMessage") or str(data))
        key = data.get("data")
        if not key:
            raise RuntimeError(f"Login failed: {data}")
        return str(key)

    def _post(self, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
        api_key = self._login()
        payload = {"apiKey": api_key, **body}
        url = f"{self._base}/{endpoint}"
        r = httpx.post(url, json=payload, timeout=120.0)
        r.raise_for_status()
        data = r.json()
        if data.get("errorCode") and data.get("errorCode") != "NONE":
            raise RuntimeError(data.get("errorMessage") or str(data))
        return data

    def list_datasets(self) -> dict[str, list[str]]:
        """Query dataset-search and classify ids into optical / sar buckets."""
        data = self._post("dataset-search", {})
        rows = data.get("data") or []
        optical: list[str] = []
        sar: list[str] = []
        for row in rows:
            ds_id = str(row.get("datasetName") or row.get("datasetAlias") or "").strip()
            if not ds_id:
                continue
            text = " ".join(
                str(row.get(k, "")).lower()
                for k in ("datasetName", "datasetAlias", "datasetFullName")
            )
            # Heuristic classifier for M2M dataset metadata strings.
            if any(k in text for k in ("sentinel-1", "radar", "sar", "alos", "palsar")):
                sar.append(ds_id)
            if any(
                k in text
                for k in (
                    "landsat",
                    "sentinel-2",
                    "modis",
                    "viirs",
                    "optical",
                    "multispectral",
                )
            ):
                optical.append(ds_id)
        return {"optical": sorted(set(optical)), "sar": sorted(set(sar))}

    def _dataset_for_query(self, query: SearchQuery) -> str:
        if query.collections and query.collections[0]:
            return query.collections[0]
        if query.modality == Modality.SAR:
            return str(self.config.get("default_dataset_sar") or self.config.get("default_dataset") or "sentinel_1a")
        if query.modality == Modality.OPTICAL:
            return str(
                self.config.get("default_dataset_optical")
                or self.config.get("default_dataset")
                or "landsat_ot_c2_l2"
            )
        return str(
            self.config.get("default_dataset_optical")
            or self.config.get("default_dataset")
            or "landsat_ot_c2_l2"
        )

    def health_check(self, smoke_search: bool = False) -> HealthResult:
        try:
            _ = self._login()
        except Exception as e:
            return HealthResult(False, str(e), self.source_id)
        if not smoke_search:
            return HealthResult(True, "M2M login OK", self.source_id)
        try:
            ds = (
                self.config.get("default_dataset_optical")
                or self.config.get("default_dataset")
                or "landsat_ot_c2_l2"
            )
            body = {
                "datasetName": ds,
                "spatialFilter": _mbr(
                    SearchQuery(
                        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
                        end=datetime(2020, 2, 1, tzinfo=timezone.utc),
                        bbox=(-112.5, 44.5, -112.0, 45.0),
                    )
                ),
                "temporalFilter": {"start": "2020-06-01", "end": "2020-06-15"},
                "maxResults": 1,
                "startingNumber": 1,
            }
            data = self._post("scene-search", body)
            res = data.get("data") or {}
            n = len(res.get("results") or [])
            return HealthResult(True, f"Smoke scene-search: {n} scene(s)", self.source_id)
        except Exception as e:
            return HealthResult(False, str(e), self.source_id)

    def search(self, query: SearchQuery) -> list[Scene]:
        ds = self._dataset_for_query(query)
        body = {
            "datasetName": ds,
            "spatialFilter": _mbr(query),
            "temporalFilter": {
                "start": _iso_date(query.start),
                "end": _iso_date(query.end),
            },
            "maxResults": query.limit,
            "startingNumber": 1,
        }
        if query.cloud_cover_max is not None:
            body["cloudCoverFilter"] = {"min": 0, "max": int(query.cloud_cover_max)}
        data = self._post("scene-search", body)
        res = data.get("data") or {}
        rows = res.get("results") or []
        scenes: list[Scene] = []
        for row in rows:
            eid = str(row.get("entityId", ""))
            sid = str(row.get("displayId", eid))
            scenes.append(
                Scene(
                    id=sid,
                    source_id=self.source_id,
                    collection=str(ds),
                    datetime=None,
                    geometry=None,
                    assets={},
                    extra={"entity_id": eid, "raw": row},
                )
            )
        return scenes

    def download(
        self,
        scene: Scene,
        dest_dir: Path,
        asset_keys: list[str] | None = None,
    ) -> list[Path]:
        entity_id = scene.extra.get("entity_id")
        if not entity_id:
            raise ValueError("Scene missing entity_id; run search from this adapter")
        dataset = (
            scene.collection
            or self.config.get("default_dataset_optical")
            or self.config.get("default_dataset")
            or "landsat_ot_c2_l2"
        )
        api_key = self._login()
        opt_body = {
            "apiKey": api_key,
            "datasetName": dataset,
            "entityIds": [entity_id],
            "products": ["STANDARD"],
        }
        url = f"{self._base}/download-options"
        r = httpx.post(url, json=opt_body, timeout=120.0)
        r.raise_for_status()
        opt_data = r.json()
        if opt_data.get("errorCode") and opt_data.get("errorCode") != "NONE":
            raise RuntimeError(opt_data.get("errorMessage") or str(opt_data))
        products = opt_data.get("data") or []
        if not products:
            raise RuntimeError("No download options returned")
        pid = products[0].get("id")
        if pid is None:
            raise RuntimeError(f"Unexpected download-options payload: {products[0]}")
        req_body = {
            "apiKey": api_key,
            "downloads": [
                {
                    "entityId": entity_id,
                    "productId": pid,
                }
            ],
            "label": f"sate-image-query-{entity_id}",
        }
        dr = httpx.post(f"{self._base}/download-request", json=req_body, timeout=120.0)
        dr.raise_for_status()
        dr_js = dr.json()
        if dr_js.get("errorCode") and dr_js.get("errorCode") != "NONE":
            raise RuntimeError(dr_js.get("errorMessage") or str(dr_js))
        dlist = dr_js.get("data") or []
        if not dlist:
            raise RuntimeError("download-request returned empty data")
        download_id = dlist[0].get("downloadId")
        if not download_id:
            raise RuntimeError(f"No downloadId: {dlist[0]}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_path: Path | None = None
        for _ in range(60):
            time.sleep(2)
            rr = httpx.post(
                f"{self._base}/download-retrieve",
                json={"apiKey": api_key, "downloadId": download_id},
                timeout=120.0,
            )
            rr.raise_for_status()
            rj = rr.json()
            if rj.get("errorCode") and rj.get("errorCode") != "NONE":
                raise RuntimeError(rj.get("errorMessage") or str(rj))
            arr = rj.get("data") or []
            if not arr:
                continue
            rec = arr[0]
            if rec.get("status") == "complete" and rec.get("url"):
                u = rec["url"]
                name = f"{scene.id}.tar.gz"
                out_path = dest_dir / name.replace("/", "_")
                with httpx.stream("GET", u, follow_redirects=True, timeout=600.0) as resp:
                    resp.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in resp.iter_bytes():
                            f.write(chunk)
                break
            if rec.get("status") == "failed":
                raise RuntimeError(json.dumps(rec))
        if out_path is None:
            raise TimeoutError("download-retrieve did not complete in time")
        return [out_path]
