from concurrent.futures import ThreadPoolExecutor
import os
from io import BufferedIOBase, TextIOBase
import pandas as pd
from drivers.base import VisualizationOptions
from helpers import get_anime_genre


class Visualizer:
    def __init__(self, df: pd.DataFrame, opts: VisualizationOptions) -> None:
        self.df = df
        self.opts = opts

        # add a genres column to the dataframe
        anime_names = df["series_title"]
        with ThreadPoolExecutor(max_workers=min(len(anime_names), 25)) as pool:
            results = pool.map(get_anime_genre, anime_names, timeout=10)

        self.df.loc[:, "series_genres"] = list(results)

        # todo load all drivers here

    @classmethod
    def from_xml(
        cls,
        xml_data: os.PathLike | BufferedIOBase | TextIOBase,
        opts: VisualizationOptions,
    ):
        df = pd.read_xml(xml_data)
        return cls(df, opts)

    def visualize_all(self):
        # todo call each driver and return base64 encoded image
        pass
