from click.testing import CliRunner

from sate_image_query.cli import main


def test_sources_list() -> None:
    runner = CliRunner()
    r = runner.invoke(main, ["sources-list"])
    assert r.exit_code == 0
    assert "mpc-stac" in r.output
