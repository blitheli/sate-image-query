import pytest
from click.testing import CliRunner

from sate_image_query.cli import main


def test_sources_list() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["sources-list"])
    assert r.exit_code == 0
    assert "mpc-stac" in r.output


def test_sources_sync_usgs_dry_run_no_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    # load_dotenv() would otherwise repopulate USGS_* from a local .env file.
    monkeypatch.setattr("sate_image_query.cli.load_dotenv", lambda *a, **k: None)
    for k in ("USGS_M2M_USERNAME", "USGS_M2M_PASSWORD", "USGS_M2M_APPLICATION_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    runner = CliRunner()
    r = runner.invoke(main, ["sources-sync-usgs", "--dry-run"])
    assert r.exit_code != 0
    assert isinstance(r.exception, RuntimeError)
    assert "USGS_M2M_USERNAME" in str(r.exception)
