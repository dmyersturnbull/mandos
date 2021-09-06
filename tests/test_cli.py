import pytest
from typer.testing import CliRunner

from mandos.cli import cli

from . import get_test_resource


class TestCli:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.stdout

    def test_spec_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["chembl:atc", "--help"])
        if result.exception is not None:
            raise result.exception
        assert "--verbose" in result.stdout


if __name__ == "__main__":
    pytest.main()
