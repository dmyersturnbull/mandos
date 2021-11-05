from pathlib import Path

from pocketutils.misc.loguru_utils import FancyLoguru, LoggerWithCautionAndNotice
from pocketutils.misc.resources import Resources

LOG_SETUP = FancyLoguru.new(LoggerWithCautionAndNotice).set_control(False)
logger = LOG_SETUP.logger

_home = Path(__file__).parent.parent.parent
MandosResources = Resources(_home / "resources", logger=logger)
_strings = {k.partition(":")[2]: v for k, v in MandosResources.json("strings.json").items()}
MandosResources.to_memory("strings", _strings)


__all__ = ["logger", "LOG_SETUP"]
