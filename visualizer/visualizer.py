import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv

from .api_helper import get_anime_genres
from .drivers.base import (
    IVisualizationDriver,
    MatplotlibVisualizationResult,
    PlotlyVisualizationResult,
    VisualizationOptions,
)
from .drivers.courwise_ratings import CourwiseRatingsDriver
from .drivers.fastest_finished import FastestFinishedDriver
from .drivers.format_distribution import FormatDistributionDriver
from .drivers.genre_distribution import GenreDistributionDriver
from .drivers.genre_ratings import GenrewiseRatingsDriver
from .drivers.monthwise_count import MonthwiseCountDriver
from .drivers.ratings_curve import RatingsCurveDriver
from .drivers.remaining_watching import RemainingCountDriver

load_dotenv("./credentials.env")

MAX_ANIME_SEARCH_THREADS = int(os.environ["MAX_ANIME_SEARCH_THREADS"])


@dataclass(frozen=True)
class VisualizationResult:
    """
    A generic data class which wraps around `MatplotlibVisualizationResult`
    and `PlotlyVisualizationResult` and is ultimately returned to the frontend.
    """

    interactive: bool
    result: MatplotlibVisualizationResult | PlotlyVisualizationResult

    def as_dict(self):
        return {"interactive": self.interactive, "result": self.result.as_dict()}


class Visualizer:
    def __init__(self, df: pd.DataFrame, opts: VisualizationOptions) -> None:
        self.df = df
        self.opts = opts

        anime_ids = df["series_animedb_id"]
        with ThreadPoolExecutor(
            max_workers=min(len(anime_ids), MAX_ANIME_SEARCH_THREADS)
        ) as pool:
            results = pool.map(get_anime_genres, anime_ids, timeout=10)

        self.df.loc[:, "series_genres"] = list(results)

        self.drivers: list[IVisualizationDriver] = [
            MonthwiseCountDriver(self.df, self.opts),
            CourwiseRatingsDriver(self.df, self.opts),
            GenreDistributionDriver(self.df, self.opts),
            GenrewiseRatingsDriver(self.df, self.opts),
            RatingsCurveDriver(self.df, self.opts),
            RemainingCountDriver(self.df, self.opts),
            FormatDistributionDriver(self.df, self.opts),
            FastestFinishedDriver(self.df, self.opts),
        ]

    @classmethod
    def from_xml(
        cls,
        xml_data,
        opts: VisualizationOptions,
    ):
        df = pd.read_xml(xml_data)
        return cls(df, opts)

    def visualize_all(self):
        results: list[VisualizationResult] = []
        for d in self.drivers:
            try:
                r = d.visualize()
                if isinstance(r, MatplotlibVisualizationResult):
                    interactive = False
                elif isinstance(r, PlotlyVisualizationResult):
                    interactive = True
                else:
                    raise Exception(f"Unknown visualization result type: {r=}")

                generic_result = VisualizationResult(interactive, r)
                results.append(generic_result)
            except Exception as e:
                logging.error(f"error occured while visualizing {d.__class__}")
                logging.exception(e)
        return results
