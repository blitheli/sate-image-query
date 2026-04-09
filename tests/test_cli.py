from click.testing import CliRunner

from sate_image_query.cli import main


def test_sources_list() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["sources-list"])
    assert r.exit_code == 0
    assert "mpc-stac" in r.output


def test_sources_sync_usgs_dry_run_no_creds() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["sources-sync-usgs", "--dry-run"])
    assert r.exit_code != 0
    assert isinstance(r.exception, RuntimeError)
    assert "USGS_M2M_USERNAME" in str(r.exception)
