from typing import Sequence

from mandos.model.apis.hmdb_support.hmdb_data import HmdbData
from mandos.model.concrete_hits import TissueConcentrationHit
from mandos.search.hmdb import HmdbSearch


class TissueConcentrationSearch(HmdbSearch[TissueConcentrationHit]):
    """ """

    def find(self, inchikey: str) -> Sequence[TissueConcentrationHit]:
        data: HmdbData = self.api.fetch_data(inchikey)
        dds = [*data.normal_concentrations, *data.abnormal_concentrations]
        dds = [dd for dd in dds if dd.micromolar is not None]
        return [
            self._create_hit(
                data_source=self._format_source(),
                c_id=str(data.cid),
                c_origin=inchikey,
                c_matched=data.inchikey,
                c_name=data.inchikey,
                predicate=self._format_predicate(
                    sexes=dd.sexes.name,
                    ages=dd.ages.name,
                    normality="normal" if dd.condition is None else "abnormal",
                    condition=dd.condition,
                ),
                object_id=dd.specimen,
                object_name=dd.specimen,
                micromolar=dd.micromolar,
            )
            for dd in dds
        ]


__all__ = ["TissueConcentrationSearch"]
