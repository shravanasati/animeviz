from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib import pyplot as plt

from .base import (
    IVisualizationDriver,
    MatplotlibVisualizationResult,
    PlotlyVisualizationResult,
)


class CourSeason(Enum):
    WINTER = 0
    SPRING = 1
    SUMMER = 2
    FALL = 3


@dataclass(frozen=True)
class Cour:
    season: CourSeason
    year: int

    def __lt__(self, other):
        if self.year != other.year:
            return self.year < other.year
        else:
            return self.season.value < other.season.value

    def __eq__(self, other):
        return self.year == other.year and self.season == other.season

    def __hash__(self) -> int:
        return hash((self.season, self.year))

    def __str__(self) -> str:
        return f"{self.season.name.capitalize()} {self.year}"


def get_cour_from_datetime(d: datetime):
    if d.month in range(1, 4):
        return Cour(CourSeason.WINTER, d.year)
    elif d.month in range(4, 7):
        return Cour(CourSeason.SPRING, d.year)
    elif d.month in range(7, 10):
        return Cour(CourSeason.SUMMER, d.year)
    elif d.month in range(10, 13):
        return Cour(CourSeason.FALL, d.year)
    else:
        raise Exception(f"invalid month {d.month}")


class CourwiseRatingsDriver(IVisualizationDriver):
    def visualize(self):
        df = self.df[self.df["my_start_date"] != "0000-00-00"]
        if len(df) == 0:
            return MatplotlibVisualizationResult(
                "Courwise Ratings", self.get_not_enough_data_image()
            )

        df.loc[:, "my_start_date"] = pd.to_datetime(
            df["my_start_date"], format="ISO8601"
        )

        df.set_index("my_start_date", inplace=True)

        # Resample the DataFrame based on quarters
        quarterly_groups = df.resample("QE")

        quarter_ratings: dict[Cour, tuple[int, int, int]] = {}

        # Perform any desired operations on the quarterly groups
        for quarter, group in quarterly_groups:
            quarter_datetime = datetime.fromisoformat(str(quarter))
            cour = get_cour_from_datetime(quarter_datetime)

            bad_count = group[group["my_score"].isin(range(1, 5))].shape[0]
            average_count = group[group["my_score"].isin(range(5, 8))].shape[0]
            good_count = group[group["my_score"].isin(range(8, 11))].shape[0]

            quarter_ratings[cour] = (bad_count, average_count, good_count)

        quarter_percentages = {
            k: tuple(round(i / sum(v) * 100, 2) for i in v)
            for k, v in quarter_ratings.items()
            if sum(v) != 0
        }

        if self.opts.interactive_charts:
            # plotly code
            df_plottable = pd.DataFrame.from_dict(
                quarter_percentages, orient="index", columns=["bad", "average", "good"]
            )
            df_plottable.reset_index(inplace=True)
            df_plottable.rename(columns={"index": "cours"}, inplace=True)
            df_plottable["cours"] = df_plottable["cours"].astype(str)

            fig = px.bar(
                df_plottable,
                x="cours",
                y=["bad", "average", "good"],
                title="Ratings Distribution of Anime Each Season",
                labels={
                    "x": "Cours",
                    "y": "Bad [1,4], Average [5,7] and Good [8,10] Rating Percentages",
                },
                color_discrete_sequence=["red", "yellow", "green"],
            )
            return PlotlyVisualizationResult("Courwise Ratings", fig)

        # matplotlib code
        cours = quarter_percentages.keys()
        keys = sorted(cours)[-12:]
        values = [quarter_percentages[k] for k in keys]

        X = np.arange(len(keys))
        bad_plottable = np.array([t[0] for t in values])
        average_plottable = np.array([t[1] for t in values])
        good_plottable = np.array([t[2] for t in values])

        fig, ax = plt.subplots()
        ax.set_title(
            "Ratings Distribution of Anime Each Season\nExpressed as percentage of total anime watched that season"
        )
        ax.set_xlabel("Cours (doesnt include only seasonal anime)")
        ax.set_ylabel("Bad, Average and Good rating percentages")

        bad_bar = ax.bar(
            [str(c) for c in cours],
            bad_plottable,
            color="r",
            label="bad rating ∈ [1, 4]",
        )
        ax.bar_label(bad_bar, label_type="center")

        average_bar = ax.bar(
            X,
            average_plottable,
            color="y",
            bottom=bad_plottable,
            label="average rating ∈ [5, 7]",
        )
        ax.bar_label(average_bar, label_type="center")

        good_bar = ax.bar(
            X,
            good_plottable,
            color="g",
            bottom=average_plottable + bad_plottable,
            label="good rating ∈ [8, 10]",
        )
        ax.bar_label(good_bar, label_type="center")

        ax.legend(fancybox=True, framealpha=0.5)
        fig.autofmt_xdate()

        result = MatplotlibVisualizationResult(
            "Courwise Ratings", self.b64_image_from_plt_fig(fig)
        )

        return result
