from pathlib import Path

from pocketutils.misc.resources import Resources

from mandos.model.utils.setup import logger


class _MandosResources(Resources):
    def __init__(self, path: Path, ell=logger):
        super().__init__(path, logger=ell)
        self.strings = None


MandosResources = _MandosResources(Path(__file__).parent.parent.parent)

MandosResources.strings = {
    k.partition(":")[2]: v for k, v in MandosResources.json("strings.json").items()
}
