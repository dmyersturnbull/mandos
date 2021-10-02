from __future__ import annotations
from loguru import logger

# noinspection PyProtectedMember
from loguru._logger import Logger

from mandos.model.utils.fancy_logger import FancyLoguru, HandlerInfo, Defaults


def _notice(__message: str, *args, **kwargs):
    return logger.log("NOTICE", __message, *args, **kwargs)


def _caution(__message: str, *args, **kwargs):
    return logger.log("CAUTION", __message, *args, **kwargs)


class MyLogger(Logger):
    """
    A wrapper that has a fake notice() method to trick static analysis.
    """

    def notice(self, __message: str, *args, **kwargs):
        raise NotImplementedError()  # not real

    def caution(self, __message: str, *args, **kwargs):
        raise NotImplementedError()  # not real


# WEIRD AS HELL, but it works
# noinspection PyTypeChecker
logger: MyLogger = logger
logger.notice = _notice
logger.caution = _caution
MANDOS_SETUP = FancyLoguru(logger).config_levels()


__all__ = ["logger", "MANDOS_SETUP", "FancyLoguru", "HandlerInfo", "Defaults"]
