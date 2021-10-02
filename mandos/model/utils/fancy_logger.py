from __future__ import annotations
import logging
import os
import sys
from dataclasses import dataclass
from inspect import cleandoc
from pathlib import Path
from typing import Mapping, Optional, Union, Any, Callable, TypeVar, Generic, TextIO, AbstractSet

# noinspection PyProtectedMember
import loguru._defaults as _defaults
import regex
from loguru import logger

# noinspection PyProtectedMember
from loguru._logger import Logger
from pocketutils.core.exceptions import IllegalStateError, XValueError


Formatter = Union[str, Callable[[Mapping[str, Any]], str]]
_FMT = cleandoc(
    r"""
    <bold>{time:YYYY-MM-DD HH:mm:ss.SSS}</bold> |
    <level>{level: <8}</level> |
    <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>
    — <level>{message}[EXTRA]</level>
    {exception}
    """
).replace("\n", " ")


class FormatFactory:
    @classmethod
    def with_extras(
        cls,
        *,
        fmt: str = _FMT,
        sep: str = "; ",
        eq_sign: str = " ",
    ) -> Callable[[Mapping[str, Any]], str]:
        def FMT(record: Mapping[str, Any]) -> str:
            extra = sep.join([e + eq_sign + "{extra[" + e + "]}" for e in record["extra"].keys()])
            if len(extra) > 0:
                extra = f" [ {extra} ]"
            return fmt.replace("[EXTRA]", extra) + os.linesep

        return FMT

    @classmethod
    def plain(cls, *, fmt: str = _FMT) -> Callable[[Mapping[str, Any]], str]:
        def FMT(record: Mapping[str, Any]) -> str:
            return fmt.replace("[EXTRA]", "")

        return FMT


class _SENTINEL:
    pass


T = TypeVar("T", covariant=True, bound=Logger)


_LOGGER_ARG_PATTERN = regex.compile(r"(?:([a-zA-Z]+):)?(.*)", flags=regex.V1)
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


class Defaults:

    levels_built_in = dict(
        TRACE=_defaults.LOGURU_TRACE_NO,
        DEBUG=_defaults.LOGURU_DEBUG_NO,
        INFO=_defaults.LOGURU_INFO_NO,
        WARNING=_defaults.LOGURU_WARNING_NO,
        ERROR=_defaults.LOGURU_ERROR_NO,
        CRITICAL=_defaults.LOGURU_CRITICAL_NO,
    )

    # the levels for caution and notice are DEFINED here
    # trace and success must match loguru's
    # and the rest must match logging's
    # note that most of these alternate between informative and problematic
    # i.e. info (ok), caution (bad), success (ok), warning (bad), notice (ok), error (bad)
    levels_extended = {
        **levels_built_in,
        **dict(
            CAUTION=23,
            SUCCESS=25,
            NOTICE=35,
        ),
    }

    colors = dict(
        TRACE="<dim>",
        DEBUG="<dim>",
        INFO="<bold>",
        CAUTION="<yellow>",
        SUCCESS="<blue>",
        WARNING="<yellow>",
        NOTICE="<blue>",
        ERROR="<red>",
        CRITICAL="<red>",
    )
    icons = dict(
        TRACE=_defaults.LOGURU_TRACE_ICON,
        DEBUG=_defaults.LOGURU_DEBUG_ICON,
        INFO=_defaults.LOGURU_INFO_ICON,
        CAUTION="⚐",  # or ☡
        SUCCESS=_defaults.LOGURU_SUCCESS_ICON,
        WARNING=_defaults.LOGURU_WARNING_ICON,
        NOTICE="★",
        ERROR=_defaults.LOGURU_ERROR_ICON,
        CRITICAL=_defaults.LOGURU_CRITICAL_ICON,
    )

    level: str = "INFO"

    fmt = FormatFactory.with_extras()

    aliases = dict(NONE=None, NO=None, OFF=None, VERBOSE="INFO", QUIET="ERROR")


@dataclass(frozen=True, repr=True, order=True)
class HandlerInfo:
    hid: int
    path: Optional[Path]
    level: Optional[str]
    fmt: Formatter


@dataclass(frozen=False, repr=True)
class _HandlerInfo:
    hid: int
    sink: Any
    level: Optional[int]
    fmt: Formatter


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


class FancyLoguru(Generic[T]):
    def __init__(self, log: T):
        self._levels = dict(Defaults.levels_built_in)
        self._logger = log
        self._main = None
        self._paths = {}
        self._aliases = dict(Defaults.aliases)

    @property
    def logger(self) -> T:
        return self._logger

    @property
    def levels(self) -> Mapping[str, int]:
        return dict(self._levels)

    @property
    def aliases(self) -> Mapping[str, str]:
        return self._aliases

    @property
    def main(self) -> Optional[HandlerInfo]:
        if self._main is None:
            return None
        return HandlerInfo(
            hid=self._main.hid, level=self._main.level, fmt=self._main.fmt, path=None
        )

    @property
    def paths(self) -> AbstractSet[HandlerInfo]:
        if self._main is None:
            return set()
        return {HandlerInfo(hid=h.hid, level=h.level, fmt=h.fmt, path=h.sink) for h in self._paths}

    def config_levels(
        self,
        *,
        levels: Mapping[str, int] = _SENTINEL,
        colors: Mapping[str, str] = _SENTINEL,
        icons: Mapping[str, str] = _SENTINEL,
        aliases: Mapping[str, str] = _SENTINEL,
    ) -> __qualname__:
        levels = Defaults.levels_extended if levels is _SENTINEL else levels
        colors = Defaults.colors if colors is _SENTINEL else colors
        icons = Defaults.icons if icons is _SENTINEL else icons
        aliases = Defaults.aliases if aliases is _SENTINEL else aliases
        for k, v in levels.items():
            self.config_level(k, v, color=colors.get(k, _SENTINEL), icon=icons.get(k, _SENTINEL))
        self._aliases = dict(aliases)
        return self

    def init(
        self,
        *,
        level: str = Defaults.level,
        sink=sys.stderr,
        fmt: Formatter = Defaults.fmt,
        intercept: bool = True,
    ) -> __qualname__:
        """
        Sets an initial configuration.
        """
        if intercept:
            logging.basicConfig(handlers=[InterceptHandler()], level=0, encoding="utf-8")
        self.logger.remove(None)  # get rid of the built-in handler
        self.config_main(level=level, sink=sink, fmt=fmt)
        return self

    def config_level(
        self,
        name: str,
        level: int,
        *,
        color: Union[None, str, _SENTINEL] = _SENTINEL,
        icon: Union[None, str, _SENTINEL] = _SENTINEL,
        replace: bool = True,
    ) -> __qualname__:
        try:
            data = logger.level(name)
        except ValueError:
            data = None
        if data is None:
            logger.level(
                name,
                no=level,
                color=None if color is _SENTINEL else color,
                icon=None if icon is _SENTINEL else icon,
            )
        elif replace:
            if level != data.no:  # loguru doesn't check whether they're eq; it just errors
                raise IllegalStateError(f"Cannot set level={level}!={data.no} for {name}")
            logger.level(
                name,
                color=data.color if color is _SENTINEL else color,
                icon=data.icon if icon is _SENTINEL else icon,
            )
        return self

    def config_main(
        self,
        *,
        sink: TextIO = _SENTINEL,
        level: Optional[str] = _SENTINEL,
        fmt: Formatter = _SENTINEL,
    ) -> __qualname__:
        """
        Sets the logging level for the main handler (normally stderr).
        """
        if level is not None and level is not _SENTINEL:
            level = level.upper()
        if self._main is None:
            self._main = _HandlerInfo(
                hid=-1, sink=sys.stderr, level=self._levels[Defaults.level], fmt=Defaults.fmt
            )
        else:
            try:
                logger.remove(self._main.hid)
            except ValueError:
                logger.error(f"Cannot remove handler {self._main.hid}")
        self._main.level = self._main.level if level is _SENTINEL else level
        self._main.sink = self._main.sink if sink is _SENTINEL else sink
        self._main.fmt = self._main.fmt if fmt is _SENTINEL else fmt
        self._main.hid = logger.add(self._main.sink, level=self._main.level, format=self._main.fmt)
        return self

    def remove_path(self, path: Path) -> __qualname__:
        for k, h in self._paths.items():
            if h.path.resolve() == path.resolve():
                h.level = None
                try:
                    logger.remove(k)
                except ValueError:
                    logger.error(f"Cannot remove handler {k} to {path}")

    def add_path(
        self, path: Path, level: str = Defaults.level, *, fmt: str = Defaults.fmt
    ) -> __qualname__:
        level = level.upper()
        ell = self._levels[level]
        info = LogSinkInfo.guess(path)
        x = logger.add(
            str(info.base),
            format=fmt,
            level=level,
            compression=info.compression,
            serialize=info.serialize,
            backtrace=True,
            diagnose=True,
            enqueue=True,
            encoding="utf-8",
        )
        self._paths[x] = _HandlerInfo(hid=x, sink=info.base, level=ell, fmt=fmt)
        return self

    def __call__(
        self,
        path: Union[None, str, Path] = None,
        main: Optional[str] = Defaults.level,
    ) -> __qualname__:
        """
        This function controls logging set via command-line.

        Args:
            main: The level for stderr
            path: If set, the path to a file. Can be prefixed with ``:level:`` to set the level
                  (e.g. ``:INFO:mandos-run.log.gz``). Can serialize to JSON if .json is used
                  instead of .log or .txt.
        """
        if main is None:
            main = Defaults.level
        main = self._aliases.get(main.upper(), main.upper())
        if main not in Defaults.levels_extended:
            _permitted = ", ".join([*Defaults.levels_extended, *Defaults.aliases.keys()])
            raise XValueError(f"{main.lower()} not a permitted log level (allowed: {_permitted}")
        self.config_main(level=main)
        if path is not None or len(str(path)) == 0:
            match = _LOGGER_ARG_PATTERN.match(str(path))
            path_level = "DEBUG" if match.group(1) is None else match.group(1)
            path = Path(match.group(2))
            self.add_path(path, path_level)
            self.logger.info(f"Added logger to {path} at level {path_level}")
        self.logger.info(f"Set main log level to {main}")
        return self


class LoguruUtils:
    @classmethod
    def force_streams_to_utf8(cls) -> None:
        # we warn the user about this in the docs!
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")


__all__ = ["Defaults", "FancyLoguru", "LoguruUtils", "HandlerInfo"]
