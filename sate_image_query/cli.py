from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv

from sate_image_query.catalog import get_source_by_id, load_sources_config
from sate_image_query.models import Modality, SearchQuery
from sate_image_query.sources import create_source


def _parse_dt(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@click.group()
def main() -> None:
    load_dotenv()


@main.command("sources-list")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def sources_list(config_path: Path | None) -> None:
    data = load_sources_config(config_path)
    for s in data.get("sources", []):
        click.echo(f"{s.get('id')}\t{s.get('api_kind')}\t{s.get('display_name')}")


@main.command("sources-test")
@click.option("--id", "source_id", required=True, help="Source id from sources.yaml")
@click.option("--smoke-search", is_flag=True, help="Run a minimal search where supported")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def sources_test(source_id: str, smoke_search: bool, config_path: Path | None) -> None:
    data = load_sources_config(config_path)
    cfg = get_source_by_id(data, source_id)
    src = create_source(source_id, cfg)
    hr = src.health_check(smoke_search=smoke_search)
    click.echo(f"ok={hr.ok}\t{hr.message}")
    sys.exit(0 if hr.ok else 1)


@main.command("search")
@click.option("--source", "source_id", required=True)
@click.option("--start", required=True, help="ISO8601 start time")
@click.option("--end", required=True, help="ISO8601 end time")
@click.option("--bbox", nargs=4, type=float, help="min_lon min_lat max_lon max_lat")
@click.option("--point", nargs=2, type=float, help="lon lat")
@click.option(
    "--modality",
    type=click.Choice(["optical", "sar", "dem", "any"], case_sensitive=False),
    default="any",
)
@click.option("--collections", help="Comma-separated collection names (STAC or USGS dataset)")
@click.option("--cloud-max", type=float, default=None)
@click.option("--limit", type=int, default=20)
@click.option("--json-out", type=click.Path(path_type=Path), default=None)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def search_cmd(
    source_id: str,
    start: str,
    end: str,
    bbox: tuple[float, float, float, float] | None,
    point: tuple[float, float] | None,
    modality: str,
    collections: str | None,
    cloud_max: float | None,
    limit: int,
    json_out: Path | None,
    config_path: Path | None,
) -> None:
    data = load_sources_config(config_path)
    cfg = get_source_by_id(data, source_id)
    src = create_source(source_id, cfg)
    cols = [c.strip() for c in collections.split(",")] if collections else None
    q = SearchQuery(
        start=_parse_dt(start),
        end=_parse_dt(end),
        modality=Modality(modality.lower()),
        bbox=bbox,
        point=point,
        collections=cols,
        cloud_cover_max=cloud_max,
        limit=limit,
    )
    scenes = src.search(q)
    payload = []
    for sc in scenes:
        ex = {k: v for k, v in sc.extra.items() if k != "raw"}
        row: dict[str, Any] = {
            "id": sc.id,
            "collection": sc.collection,
            "datetime": sc.datetime.isoformat() if sc.datetime else None,
            "cloud_cover_pct": ex.pop("cloud_cover_pct", None),
            "spatial_resolution": ex.pop("spatial_resolution", None),
            "geometry": sc.geometry,
            "assets": sc.assets,
            "extra": ex,
        }
        payload.append(row)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if json_out:
        json_out.write_text(text, encoding="utf-8")
        click.echo(str(json_out))
    else:
        click.echo(text)


@main.command("download")
@click.option("--source", "source_id", required=True)
@click.option("--scene-json", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--dest", type=click.Path(path_type=Path), required=True)
@click.option("--assets", help="Comma-separated STAC asset keys")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def download_cmd(
    source_id: str,
    scene_json: Path,
    dest: Path,
    assets: str | None,
    config_path: Path | None,
) -> None:
    data = load_sources_config(config_path)
    cfg = get_source_by_id(data, source_id)
    src = create_source(source_id, cfg)
    raw = json.loads(scene_json.read_text(encoding="utf-8"))
    from sate_image_query.models import Scene

    sc = Scene(
        id=raw["id"],
        source_id=source_id,
        collection=raw.get("collection"),
        datetime=_parse_dt(raw["datetime"]) if raw.get("datetime") else None,
        geometry=raw.get("geometry"),
        assets=raw.get("assets") or {},
        extra=raw.get("extra") or {},
    )
    keys = [a.strip() for a in assets.split(",")] if assets else None
    paths = src.download(sc, dest, asset_keys=keys)
    for p in paths:
        click.echo(str(p))


if __name__ == "__main__":
    main()
