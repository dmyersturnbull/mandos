from typing import TypeVar

from pocketutils.misc.loguru_utils import FancyLoguru, LoggerWithCautionAndNotice

T = TypeVar("T", covariant=True)


LOG_SETUP = FancyLoguru.new(LoggerWithCautionAndNotice).set_control(False)

logger = LOG_SETUP.logger


__all__ = ["LOG_SETUP", "logger"]
