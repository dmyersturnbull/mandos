import time
from functools import wraps

from pocketutils.tools.unit_tools import UnitTools

from mandos.model.utils.setup import logger


def entry():
    @wraps(entry)
    def dec(func):
        def my_fn(*args, **kwargs):
            t0 = time.monotonic()
            results = func(*args, **kwargs)
            delta = UnitTools.delta_time_to_str(time.monotonic() - t0)
            logger.debug(f"Command took {delta}")
            return results

        return wraps(func)(my_fn)

    return dec


__all__ = ["entry"]
