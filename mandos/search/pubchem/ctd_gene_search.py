import re
from dataclasses import dataclass
from typing import Sequence, Optional, Mapping, Any

from mandos.model import MiscUtils
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class CtdGeneHit(PubchemHit):
    """ """

    taxon_id: Optional[int]
    taxon_name: Optional[str]


class CtdGeneSearch(PubchemSearch[CtdGeneHit]):
    """ """

    @property
    def data_source(self) -> str:
        return "Comparative Toxicogenomics Database (CTD) :: chemical/gene interactions"

    def find(self, inchikey: str) -> Sequence[CtdGeneHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biomolecular_interactions_and_pathways.chemical_gene_interactions:
            for interaction in dd.interactions:
                for predicate in self._predicate(data.name, dd.gene_name, interaction):
                    results.append(
                        self._create_hit(
                            inchikey=inchikey,
                            c_id=str(data.cid),
                            c_origin=inchikey,
                            c_matched=data.names_and_identifiers.inchikey,
                            c_name=data.name,
                            predicate=predicate,
                            statement=predicate,
                            object_id=dd.gene_name,
                            object_name=dd.gene_name,
                            taxon_id=dd.tax_id,
                            taxon_name=dd.tax_name,
                        )
                    )
        return results

    @property
    def static_data(self) -> Mapping[str, Any]:
        return dict(
            search_key=self.key,
            search_class=self.search_class,
            data_source=self.data_source,
            run_date=MiscUtils.utc(),
            cache_date=None,
        )

    def _predicate(self, compound: str, gene: str, interaction: str) -> Sequence[str]:
        # TODO: Sometimes synonyms of the compound are used (e.g. "Crack Cocaine")
        if (
            "co-treated" in interaction
            or "co-treatment" in interaction
            or "mutant" in interaction
            or "modified form" in interaction
            or "alternative form" in interaction
        ):
            return []
        expression = {
            "results in increased ((?:expression)|(?:activity)|(?:phosphorylation))": "increases $1 of",
            "results in decreased ((?:expression)|(?:activity)|(?:phosphorylation))": "decreases $1 of",
            "affects the ((?:expression)|(?:activity)|(?:phosphorylation))": "affects $1 of",
            "affects the localization": "affects localization",
        }
        results = []
        for txt, effect in expression.items():
            result = self._if_match(
                interaction,
                re.escape(compound)
                + " "
                + txt
                + " "
                + gene
                + "(?: (?:mRNA)|(?:protein)|(?:exon))?",
                effect,
            )
            if result is not None:
                results.append(result)
            else:
                # catches "affects the activity of and affects the expression of"
                # TODO: could this catch something weird:
                if result is None:
                    result = self._if_match(
                        interaction, re.escape(compound) + " " + txt + " of and .+", effect
                    )
                if result is not None:
                    results.append(result)
        if len(results) > 0:
            return results
        result = self._if_match(
            interaction,
            re.escape(compound) + " ((?:affects)|(?:promotes)|(?:inhibits)) the reaction",
            "affects a reaction involving",
        )
        return [interaction.replace(compound, "").strip()] if result is None else [result]

    def _if_match(self, interaction: str, pattern: str, result: str) -> Optional[str]:
        pat = re.compile("^" + pattern + "$", flags=re.IGNORECASE)
        match = pat.fullmatch(interaction)
        if match is None:
            return None
        for i, group in enumerate(match.groupdict()):
            result = result.replace("$" + str(i + 1), group)
        return result


__all__ = ["CtdGeneHit", "CtdGeneSearch"]
