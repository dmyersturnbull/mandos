import pytest
from typer.testing import CliRunner

from mandos.cli import Commands, What, cli


class TestCli:
    def test_cli(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])
        assert result.exit_code == 0
        # assert result.stdout
        # df = Commands.search_for(What.activity, ["ZPUCINDJVBIVPJ-LJISPDSOSA-N"])
        # assert len(df) > 0
        # df.to_csv("hits.csv")
        # df = Commands.search_for(What.mechanism, ["RTHCYVBBDHJXIQ-UHFFFAOYSA-N"])
        # assert len(df) > 0
        # df.to_csv("hits.csv")

    """
    def make_atc_csv(self):
        df = pd.read_csv(
            Path(__file__).parent.parent / "mandos" / "resources" / "atc.csv"
        )
        df = df[~df["ATC LEVEL"].isna()]
        df = df.drop("Is Drug Class", axis=1)
        df.columns = ["class_id", "label", "parent", "level"]
        df.to_csv("atc.tab.gz", sep="\t")
    """


if __name__ == "__main__":
    pytest.main()
