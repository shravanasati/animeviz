# from concurrent.futures import ThreadPoolExecutor
import os
from io import BufferedIOBase, TextIOBase

import pandas as pd

from .drivers.base import (
    IVisualizationDriver,
    VisualizationOptions,
    VisualizationResult,
)
from .drivers.courwise_ratings import CourwiseRatingsDriver
from .drivers.monthwise_count import MonthwiseCountDriver

# from .helpers import get_anime_genres


class Visualizer:
    def __init__(self, df: pd.DataFrame, opts: VisualizationOptions) -> None:
        self.df = df
        self.opts = opts

        # todo add a genres column to the dataframe
        # anime_names = df["series_title"]
        # with ThreadPoolExecutor(max_workers=min(len(anime_names), 25)) as pool:
        #     results = pool.map(get_anime_genres, anime_names, timeout=10)

        # self.df.loc[:, "series_genres"] = list(results)
        # print(self.df.head())

        self.drivers: list[IVisualizationDriver] = [
            MonthwiseCountDriver(self.df, self.opts),
            CourwiseRatingsDriver(self.df, self.opts),
        ]

    @classmethod
    def from_xml(
        cls,
        xml_data: os.PathLike | BufferedIOBase | TextIOBase,
        opts: VisualizationOptions,
    ):
        df = pd.read_xml(xml_data)
        return cls(df, opts)

    def visualize_all(self):
        results: list[VisualizationResult] = []
        for d in self.drivers:
            try:
                r = d.visualize()
                results.append(r)
            except Exception as e:
                # todo add logging
                print(f"error occured while vizualizing {d.__class__}: {e}")
        return results
