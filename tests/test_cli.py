import pytest
from typer.testing import CliRunner

from mandos.cli import Commands, What, cli

from . import get_test_resource


class TestCli:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.stdout

    def test_search(self):
        runner = CliRunner()
        path = get_test_resource("inchis.txt")
        result = runner.invoke(cli, ["search", "atc", str(path)])
        if result.exception is not None:
            raise result.exception
        assert result.stdout == ""


if __name__ == "__main__":
    pytest.main()
