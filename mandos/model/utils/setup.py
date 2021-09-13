import logging
import sys
from pathlib import Path
from typing import Optional

import regex
from loguru import logger

from loguru._logger import Logger
from typeddfs import FileFormat


_LOGGER_ARG_PATTERN = regex.compile(r"(?:[A-Z]+:)??(.*)", flags=regex.V1)


class InterceptHandler(logging.Handler):
    """
    Redirects standard logging to loguru.
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


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


class MandosLogging:
    # this is required for mandos to run

    DEFAULT_LEVEL: str = "NOTICE"

    @classmethod
    def init(cls) -> None:
        """
        Sets an initial configuration.
        """
        cls._init()
        cls.redirect_std_logging()
        cls.set_main_level(MandosLogging.DEFAULT_LEVEL)

    @classmethod
    def _init(cls) -> None:
        try:
            logger.level("NOTICE", no=35)
        except TypeError:
            # this happens if it's already been added (e.g. from an outside library)
            # if we don't have it set after this, we'll find out soon enough
            logger.debug("Could not add 'NOTICE' loguru level. Did you already set it?")
        try:
            logger.level("CAUTION", no=25)
        except TypeError:
            logger.debug("Could not add 'CAUTION' loguru level. Did you already set it?")
        logger.notice = _notice
        logger.caution = _caution

    @classmethod
    def redirect_std_logging(cls, level: int = 10) -> None:
        # 10 b/c we're really never going to want trace output
        logging.basicConfig(handlers=[InterceptHandler()], level=level)

    @classmethod
    def set_main_level(cls, level: str) -> None:
        logger.remove()
        logger.add(sys.stderr, level=level)

    @classmethod
    def disable_main(cls) -> None:
        logger.remove()

    @classmethod
    def add_path_logger(cls, path: Path, level: str) -> None:
        serialize = FileFormat.from_path(path) is FileFormat.json
        compression = FileFormat.compression_from_path(path).name.lstrip(".")
        logger.add(
            str(path),
            level=level,
            compression=compression,
            serialize=serialize,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )


class MandosSetup:

    LEVELS = ["off", "error", "notice", "warning", "caution", "info", "debug"]
    ALIASES = dict(none="off", no="off", verbose="info", quiet="error")

    def __call__(
        self,
        log: Optional[Path] = None,
        level: str = MandosLogging.DEFAULT_LEVEL,
        skip: bool = False,
    ) -> None:
        """
        This function controls all aspects of the logging as set via command-line.

        Args:
            level: The level for stderr
            log: If set, the path to a file. Can be prefixed with ``:level:`` to set the level
                  (e.g. ``:INFO:mandos-run.log.gz``). Can serialize to JSON if .json is used
                  instead of .log or .txt.
        """
        if skip:
            return
        level = MandosSetup.ALIASES.get(level.lower(), level).upper()
        if level.lower() not in MandosSetup.LEVELS:
            _permitted = ", ".join([*MandosSetup.LEVELS, *MandosSetup.ALIASES.keys()])
            raise ValueError(f"{level.lower()} not a permitted log level (allowed: {_permitted}")
        if level == "OFF":
            MandosLogging.disable_main()
        else:
            MandosLogging.set_main_level(level)
        match = _LOGGER_ARG_PATTERN.match(str(log))
        if log is not None:
            path_level = "DEBUG" if match.group(1) is None else match.group(1)
            path = Path(match.group(2))
            MandosLogging.add_path_logger(path, path_level)
            logger.info(f"Added logger to {path} at level {path_level}")
        logger.notice(f"Ready. Set log level to {level}")


# weird as hell, but it works
# noinspection PyTypeChecker
logger: MyLogger = logger


MANDOS_SETUP = MandosSetup()
