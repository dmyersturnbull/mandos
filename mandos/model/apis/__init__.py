from pocketutils.core.query_utils import QueryExecutor

from mandos.model.utils import logger


class _QueryMixin:
    @property
    def executor(self) -> QueryExecutor:
        raise NotImplementedError()

    def _query(self, url: str) -> str:
        data = self.executor(url)
        tt = self.executor.last_time_taken
        wt, qt = tt.wait.total_seconds(), tt.query.total_seconds()
        bts = int(len(data) * 8 / 1024)
        logger.trace(f"Queried {bts} kb from {url} in {qt:.1} s with {wt:.1} s of wait")
        return data


__all__ = ["QueryExecutor"]
