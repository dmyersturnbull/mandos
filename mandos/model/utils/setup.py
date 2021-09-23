import logging
import sys
from pathlib import Path
from typing import Optional, Union

import regex
from loguru import logger

from loguru._logger import Logger
from pocketutils.core.exceptions import BadCommandError, XValueError
from typeddfs import FileFormat
from typeddfs.file_formats import CompressionFormat

_LOGGER_ARG_PATTERN = regex.compile(r"(?:([a-zA-Z]+):)?(.*)", flags=regex.V1)


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
        # we warn the user about this in the docs!
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
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
        logging.basicConfig(handlers=[InterceptHandler()], level=level, encoding="utf-8")

    @classmethod
    def set_main_level(cls, level: str) -> None:
        logger.remove()
        logger.add(sys.stderr, level=level)

    @classmethod
    def disable_main(cls) -> None:
        logger.remove()

    @classmethod
    def add_path_logger(cls, path: Path, level: str) -> None:
        cls.get_log_suffix(path)
        compressions = [
            ".xz",
            ".lzma",
            ".gz",
            ".zip",
            ".bz2",
            ".tar",
            ".tar.gz",
            ".tar.bz2",
            ".tar.xz",
        ]
        compressions = {c: c.lstrip(".") for c in compressions}
        serialize = path.with_suffix("").name.endswith(".json")
        compression = compressions.get(path.suffix)
        logger.add(
            str(path),
            level=level,
            compression=compression,
            serialize=serialize,
            backtrace=True,
            diagnose=True,
            enqueue=True,
            encoding="utf-8",
        )

    @classmethod
    def get_log_suffix(cls, path: Path) -> str:
        valid_log_suffixes = {
            *{f".log{c.suffix}" for c in CompressionFormat.list()},
            *{f".txt{c.suffix}" for c in CompressionFormat.list()},
            *{f".json{c.suffix}" for c in CompressionFormat.list()},
        }
        # there's no overlap, right? pretty sure
        matches = {s for s in valid_log_suffixes if path.name.endswith(s)}
        if len(matches) == 0:
            raise XValueError(
                f"{path} is not a valid logging path; use one of {', '.join(valid_log_suffixes)}"
            )
        suffix = next(iter(matches))
        return suffix


class MandosSetup:

    LEVELS = ["off", "error", "notice", "warning", "caution", "info", "debug"]
    ALIASES = dict(none="off", no="off", verbose="info", quiet="error")

    def __call__(
        self,
        log: Union[None, str, Path] = None,
        level: Optional[str] = MandosLogging.DEFAULT_LEVEL,
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
        if level is None or len(str(level)) == 0:
            level = MandosLogging.DEFAULT_LEVEL
        level = MandosSetup.ALIASES.get(level.lower(), level).upper()
        if level.lower() not in MandosSetup.LEVELS:
            _permitted = ", ".join([*MandosSetup.LEVELS, *MandosSetup.ALIASES.keys()])
            raise XValueError(f"{level.lower()} not a permitted log level (allowed: {_permitted}")
        if level == "OFF":
            MandosLogging.disable_main()
        else:
            MandosLogging.set_main_level(level)
        if log is not None or len(str(log)) == 0:
            match = _LOGGER_ARG_PATTERN.match(str(log))
            path_level = "DEBUG" if match.group(1) is None else match.group(1)
            path = Path(match.group(2))
            MandosLogging.add_path_logger(path, path_level)
            logger.info(f"Added logger to {path} at level {path_level}")
        logger.info(f"Set log level to {level}")


# weird as hell, but it works
# noinspection PyTypeChecker
logger: MyLogger = logger
MandosLogging.init()


MANDOS_SETUP = MandosSetup()
