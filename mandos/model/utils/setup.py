from __future__ import annotations
import logging
import sys
from dataclasses import dataclass
from inspect import cleandoc
from pathlib import Path
from typing import Mapping, Optional, Union

# noinspection PyProtectedMember
import loguru._defaults as _defaults
import regex
from loguru import logger

# noinspection PyProtectedMember
from loguru._logger import Logger
from pocketutils.core.exceptions import IllegalStateError, XValueError

_LOGGER_ARG_PATTERN = regex.compile(r"(?:([a-zA-Z]+):)?(.*)", flags=regex.V1)
_DEFAULT_LEVEL: str = "INFO"
FMT = cleandoc(
    r"""
    <bold>{time:YYYY-MM-DD HH:mm:ss.SSS}</bold> |
    <level>{level: <8}</level> |
    <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>
    """
).replace("\n", " ")


class _SENTINEL:
    pass


log_compressions = {
    ".xz",
    ".lzma",
    ".gz",
    ".zip",
    ".bz2",
    ".tar",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
}
valid_log_suffixes = {
    *{f".log{c}" for c in log_compressions},
    *{f".txt{c}" for c in log_compressions},
    *{f".json{c}" for c in log_compressions},
}
# the levels for caution and notice are DEFINED here
# trace and success must match loguru's
# and the rest must match logging's
# note that most of these alternate between informative and problematic
# i.e. info (ok), caution (bad), success (ok), warning (bad), notice (ok), error (bad)
LEVELS = dict(
    TRACE=_defaults.LOGURU_TRACE_NO,
    DEBUG=_defaults.LOGURU_DEBUG_NO,
    INFO=_defaults.LOGURU_INFO_NO,
    CAUTION=23,
    SUCCESS=25,
    WARNING=_defaults.LOGURU_WARNING_NO,
    NOTICE=35,
    ERROR=_defaults.LOGURU_ERROR_NO,
    CRITICAL=_defaults.LOGURU_CRITICAL_NO,
)
LEVEL_COLORS = dict(
    TRACE="",
    DEBUG="",
    INFO="<bold>",
    CAUTION="<yellow>",
    SUCCESS="<blue>",
    WARNING="<yellow>",
    NOTICE="<blue>",
    ERROR="<red>",
    CRITICAL="<RED>",
)
LEVEL_ICONS = {}
_ALIASES = dict(NONE="OFF", NO="OFF", VERBOSE="INFO", QUIET="ERROR")


@dataclass(frozen=True, repr=True, order=True)
class LogSinkInfo:
    path: Path
    base: Path
    suffix: str
    serialize: bool
    compression: Optional[str]

    @classmethod
    def guess(cls, path: Union[str, Path]) -> LogSinkInfo:
        path = Path(path)
        base, compression = path.name, None
        for c in log_compressions:
            if path.name.endswith(c):
                base, compression = path.name[: -len(c)], c
        if not [base.endswith(s) for s in [".json", ".log", ".txt"]]:
            raise XValueError(
                f"Log filename {path.name} is not .json, .log, .txt, or a compressed variant"
            )
        return LogSinkInfo(
            path=path,
            base=path.parent / base,
            suffix=compression,
            serialize=base.endswith(".json"),
            compression=compression,
        )


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_stderr_log_level: Optional[str] = _DEFAULT_LEVEL

    @property
    def current_stderr_log_level(self) -> Optional[str]:
        return self._current_stderr_log_level

    def notice(self, __message: str, *args, **kwargs):
        raise NotImplementedError()  # not real

    def caution(self, __message: str, *args, **kwargs):
        raise NotImplementedError()  # not real


class MandosLogging:
    # this is required for mandos to run

    DEFAULT_LEVEL: str = _DEFAULT_LEVEL
    _main_handler_id: int = None

    @classmethod
    def inverse_levels(cls) -> Mapping[int, str]:
        return {v: k for k, v in cls.levels()}

    @classmethod
    def levels(cls) -> Mapping[str, int]:
        return dict(LEVELS)

    @classmethod
    def init(
        cls,
        *,
        level: str = _DEFAULT_LEVEL,
        sink=sys.stderr,
        force_utf8: bool = True,
        intercept: bool = True,
        force: bool = False,
    ) -> None:
        """
        Sets an initial configuration.
        """
        if cls._main_handler_id is not None and not force:
            return
        if force_utf8:
            # we warn the user about this in the docs!
            sys.stderr.reconfigure(encoding="utf-8")
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdin.reconfigure(encoding="utf-8")
        if intercept:
            logging.basicConfig(handlers=[InterceptHandler()], level=0, encoding="utf-8")
        for k, v in LEVELS.items():
            cls.configure_level(
                k, v, color=LEVEL_COLORS.get(k, _SENTINEL), icon=LEVEL_ICONS.get(k, _SENTINEL)
            )
        logger.notice = _notice
        logger.caution = _caution
        logger.remove(None)  # get rid of the built-in handler
        cls.set_main_level(level, sink=sink)
        logger.disable("chembl_webresource_client")
        logger.notice("Started.")

    @classmethod
    def configure_level(
        cls,
        name: str,
        level: int,
        *,
        color: Union[None, str, _SENTINEL] = _SENTINEL,
        icon: Union[None, str, _SENTINEL] = _SENTINEL,
        replace: bool = True,
    ):
        try:
            data = logger.level(name)
        except ValueError:
            data = None
        if data:
            if replace:
                if level != data.no:  # loguru doesn't check whether they're eq; it just errors
                    raise IllegalStateError(f"Cannot set level={level}!={data.no} for {name}")
                logger.level(
                    name,
                    color=data.color if color is _SENTINEL else color,
                    icon=data.icon if icon is _SENTINEL else icon,
                )
        else:
            logger.level(
                name,
                no=level,
                color=None if color is _SENTINEL else color,
                icon=None if icon is _SENTINEL else icon,
            )

    @classmethod
    def set_main_level(cls, level: str, sink=sys.stderr) -> None:
        """
        Sets the logging level for the main handler (normally stderr).
        """
        level = level.upper()
        if cls._main_handler_id is not None:
            try:
                logger.remove(cls._main_handler_id)
            except ValueError:
                logger.error(f"Cannot remove handler {cls._main_handler_id}")
        if level != "OFF":
            cls._main_handler_id = logger.add(sink, level=level, format=FMT)

    @classmethod
    def add_path(cls, path: Path, level: str) -> int:
        level = level.upper()
        info = LogSinkInfo.guess(path)
        return logger.add(
            str(info.base),
            level=level,
            compression=info.compression,
            serialize=info.serialize,
            backtrace=True,
            diagnose=True,
            enqueue=True,
            encoding="utf-8",
        )


class MandosSetup:
    @classmethod
    def aliases(cls) -> Mapping[str, str]:
        return _ALIASES

    def __call__(
        self,
        log: Union[None, str, Path] = None,
        level: Optional[str] = MandosLogging.DEFAULT_LEVEL,
    ) -> None:
        """
        This function controls all aspects of the logging as set via command-line.

        Args:
            level: The level for stderr
            log: If set, the path to a file. Can be prefixed with ``:level:`` to set the level
                  (e.g. ``:INFO:mandos-run.log.gz``). Can serialize to JSON if .json is used
                  instead of .log or .txt.
        """
        if level is None:
            level = MandosLogging.DEFAULT_LEVEL
        level = level.upper()
        level = _ALIASES.get(level, level)
        if level not in LEVELS:
            _permitted = ", ".join([*LEVELS, *_ALIASES.keys()])
            raise XValueError(f"{level.lower()} not a permitted log level (allowed: {_permitted}")
        MandosLogging.set_main_level(level)
        if log is not None or len(str(log)) == 0:
            match = _LOGGER_ARG_PATTERN.match(str(log))
            path_level = "DEBUG" if match.group(1) is None else match.group(1)
            path = Path(match.group(2))
            MandosLogging.add_path(path, path_level)
            logger.info(f"Added logger to {path} at level {path_level}")
        logger.info(f"Set log level to {level}")


# weird as hell, but it works
# noinspection PyTypeChecker
logger: MyLogger = logger
MandosLogging.init()


MANDOS_SETUP = MandosSetup()

__all__ = ["logger", "MANDOS_SETUP", "MandosLogging", "LogSinkInfo"]
