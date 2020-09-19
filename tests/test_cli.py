import pytest
from typer.testing import CliRunner

from mandos.cli import Commands, What, cli


class TestCli:
    def test_cli(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])
        assert result.exit_code == 0
        # assert result.stdout


if __name__ == "__main__":
    pytest.main()
