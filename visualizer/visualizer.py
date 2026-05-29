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
from .drivers.status_distribution import StatusDistributionDriver

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
            StatusDistributionDriver(self.df, self.opts),
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

    def get_summary(self):
        """
        Calculates Key Performance Indicators (KPIs) for the user's animelist.
        """
        total_anime = int(len(self.df))
        completed = int(len(self.df[self.df["my_status"] == "Completed"]))
        total_episodes = int(self.df["my_watched_episodes"].sum())

        # Mean score (excluding unrated)
        scored_df = self.df[self.df["my_score"] > 0]
        mean_score = float(scored_df["my_score"].mean()) if not scored_df.empty else 0.0

        # Approximate watch time (assume 24 mins per episode)
        total_minutes = total_episodes * 24
        days = total_minutes // (24 * 60)

        # Recent activity (this month)
        from datetime import date

        current_month = date.today().strftime("%Y-%m")
        finished_this_month = self.df[
            self.df["my_finish_date"].str.startswith(current_month)
        ]
        count_this_month = int(len(finished_this_month))

        # Favorite genre factor
        genres_list = []
        for g in self.df["series_genres"]:
            genres_list.extend(g)

        most_common_genre = "N/A"
        if genres_list:
            from collections import Counter

            most_common_genre = Counter(genres_list).most_common(1)[0][0]

        return {
            "total_anime": total_anime,
            "completed": completed,
            "total_episodes": total_episodes,
            "mean_score": round(float(mean_score), 2),
            "days_watched": int(days),
            "finished_this_month": count_this_month,
            "favorite_genre": most_common_genre,
        }

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
