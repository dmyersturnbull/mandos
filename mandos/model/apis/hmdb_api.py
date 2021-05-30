import abc

import defusedxml.ElementTree as Xml
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import Api


class HmdbApi(Api, metaclass=abc.ABCMeta):
    def fetch(self, hmdb_id: str) -> NestedDotDict:
        raise NotImplementedError()


class QueryingHmdbApi(HmdbApi):
    def fetch(self, hmdb_id: str) -> NestedDotDict:
        url = f"https://hmdb.ca/metabolites/{hmdb_id}.xml"
        # e.g. https://hmdb.ca/metabolites/HMDB0001925.xml

    def _to_json(self, xml):
        response = {}
        for child in list(xml):
            if len(list(child)) > 0:
                response[child.tag] = self._to_json(child)
            else:
                response[child.tag] = child.text or ""
            # one-liner equivalent
            # response[child.tag] = parseXmlToJson(child) if len(list(child)) > 0 else child.text or ''
        return response


__all__ = ["HmdbApi", "QueryingHmdbApi"]
