"""

"""


class PlotUtils:
    def _markers(self, df: pd.DataFrame, col: Optional[str]) -> Optional[pd.Series]:
        from matplotlib.markers import MarkerStyle

        if col is None:
            return None
        known = MarkerStyle.markers.keys()
        uniques = df[col].unique()
        if all((v in known for v in uniques)):
            return df[col]
        if len(uniques) > len(known):
            logger.error(f"{len(uniques)} unique markers > {len(known)} available. Cycling.")
        cycler = cycle(known)
        dct = {k: next(cycler) for k in uniques}
        return df[col].map(dct.get)

    def _colors(df: pd.DataFrame, col: Optional[str]) -> Optional[pd.Series]:
        if col is None:
            return None
        return df[col]
