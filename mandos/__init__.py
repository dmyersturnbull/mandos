"""
Metadata for this project.
"""

import logging
import re
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as __load
from pathlib import Path
from typing import Optional

from loguru import logger

pkg = "mandos"
_metadata = None
try:
    _metadata = __load(Path(__file__).absolute().parent.name)
    __status__ = "Development"
    __copyright__ = "Copyright 2020–2021"
    __date__ = "2020-08-14"
    __uri__ = _metadata["home-page"]
    __title__ = _metadata["name"]
    __summary__ = _metadata["summary"]
    __license__ = _metadata["license"]
    __version__ = _metadata["version"]
    __author__ = _metadata["author"]
    __maintainer__ = _metadata["maintainer"]
    __contact__ = _metadata["maintainer"]
except PackageNotFoundError:  # pragma: no cover
    logger.error(f"Could not load package metadata for {pkg}. Is it installed?")


class MandosMetadata:
    version = __version__


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


class MandosLogging:
    # this is required for mandos to run
    try:
        logger.level("NOTICE", no=35)
    except TypeError:
        # this happens if it's already been added (e.g. from an outside library)
        # if we don't have it set after this, we'll find out soon enough
        logger.debug("Could not add 'NOTICE' loguru level. Did you already set it?")
    logger.notice = _notice

    @classmethod
    def init(cls) -> None:
        """
        Sets an initial configuration.
        """
        cls.redirect_std_logging()
        cls.set_log_level("INFO", None)

    @classmethod
    def redirect_std_logging(cls, level: int = 10) -> None:
        # 10 b/c we're really never going to want trace output
        logging.basicConfig(handlers=[InterceptHandler()], level=level)

    @classmethod
    def set_log_level(cls, level: str, path: Optional[Path]) -> None:
        """
        This function will control all aspects of the logging as set via command-line.

        Args:
            level: The level to use for output to stderr
            path: If set, the path to a file. Can be prefixed with ``:level:`` to set the level
                  (e.g. ``:INFO:mandos-run.log.gz``). Can serialize to JSON if .json is used
                  instead of .log.
        """
        logger.remove()
        logger.add(sys.stderr, level=level)
        cls._add_path_logger(path)

    @classmethod
    def _add_path_logger(cls, path: Path) -> None:
        if path is None:
            return
        match = re.compile(r"(?:[A-Z]+:)??(.*)").match(str(path))
        level = "DEBUG" if match.group(1) is None else match.group(1)
        path = Path(match.group(2))
        for e, c in dict(gz="gzip", zip="zip", bz2="bzip2", xz="xz"):
            if str(path).endswith("." + e):
                serialize = True if path.suffix == f".json.{e}" else False
                logger.add(
                    str(path),
                    level=level,
                    compression=c,
                    serialize=serialize,
                    backtrace=True,
                    diagnose=True,
                )


class MandosSetup:
    def __init__(self):
        self._set_up = False

    def __call__(
        self,
        log: Optional[Path],
        quiet: bool,
        verbose: bool,
        no_setup: bool = False,
    ):
        if not self._set_up:
            self.run_command_setup(verbose, quiet, log, no_setup)

    def run_command_setup(
        self, verbose: bool, quiet: bool, log: Optional[Path], skip_setup: bool
    ) -> None:
        if not skip_setup:
            level = self._set_logging(verbose, quiet, log)
            logger.notice(f"Ready. Set log level to {level}")

    def _set_logging(self, verbose: bool, quiet: bool, log: Optional[Path]) -> str:
        if verbose and quiet:
            raise ValueError(f"Cannot set both --quiet and --verbose")
        elif quiet:
            level = "ERROR"
        elif verbose:
            level = "INFO"
        else:
            level = "WARNING"
        MandosLogging.set_log_level(level, log)
        return level


MANDOS_SETUP = MandosSetup()

if __name__ == "__main__":  # pragma: no cover
    if _metadata is not None:
        print(f"{pkg} (v{_metadata['version']})")
    else:
        print("Unknown project info")


__all__ = ["MandosMetadata", "logger", "MandosLogging", "MandosSetup", "MANDOS_SETUP"]
