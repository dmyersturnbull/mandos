from typing import Optional, Sequence

import regex

from mandos.model.concrete_hits import CtdGeneHit
from mandos.search.pubchem import PubchemSearch


class CtdGeneSearch(PubchemSearch[CtdGeneHit]):
    """ """

    def find(self, inchikey: str) -> Sequence[CtdGeneHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biomolecular_interactions_and_pathways.chemical_gene_interactions:
            for interaction in dd.interactions:
                source = self._format_source(taxon_id=dd.tax_id, taxon_name=dd.tax_name)
                predicates = self._predicate(
                    data.name, dd.gene_name, interaction, dd.tax_id, dd.tax_name
                )
                for predicate in predicates:
                    results.append(
                        self._create_hit(
                            inchikey=inchikey,
                            c_id=str(data.cid),
                            c_origin=inchikey,
                            c_matched=data.names_and_identifiers.inchikey,
                            c_name=data.name,
                            data_source=source,
                            predicate=predicate,
                            object_id=dd.gene_name,
                            object_name=dd.gene_name,
                            taxon_id=dd.tax_id,
                            taxon_name=dd.tax_name,
                        )
                    )
        return results

    def _predicate(
        self, compound: str, gene: str, interaction: str, taxon_id: int, taxon_name: str
    ) -> Sequence[str]:
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
            "results in increased ((?:expression)|(?:activity)|(?:phosphorylation))": (
                "$thing",
                "up",
            ),
            "results in decreased ((?:expression)|(?:activity)|(?:phosphorylation))": (
                "$thing",
                "down",
            ),
            "affects the ((?:expression)|(?:activity)|(?:phosphorylation))": ("$thing", "neutral"),
            "affects the localization": ("localization", "neutral"),
        }
        results = []
        for pattern, (thing, direction) in expression.items():
            _against = (
                "^"
                + regex.escape(compound)
                + f" {pattern} {gene}"
                + "(?: (?:mRNA)|(?:protein)|(?:exon)(?:of and .*))?"
                + "$"
            )
            result = self._if_match(interaction, _against, thing, direction, taxon_id, taxon_name)
            if result is not None:
                results.append(result)
        return results

    def _if_match(
        self,
        interaction: str,
        pattern: str,
        thing: str,
        direction: str,
        taxon_id: int,
        taxon_name: str,
    ) -> Optional[str]:
        pat = regex.compile(pattern, flags=regex.V1 | regex.IGNORECASE)
        match = pat.fullmatch(interaction)
        if match is None:
            return None
        thing = thing.replace("$thing", match.group(1))
        return self._format_predicate(
            what=thing, direction=direction, taxon_id=taxon_id, taxon_name=taxon_name
        )


__all__ = ["CtdGeneSearch"]
