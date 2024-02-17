from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from .base import IVisualizationDriver, VisualizationResult


def get_cour_from_datetime(d: datetime):
    if d.month in range(1, 4):
        return f"Winter {d.year}"
    elif d.month in range(4, 7):
        return f"Spring {d.year}"
    elif d.month in range(7, 10):
        return f"Summer {d.year}"
    elif d.month in range(10, 13):
        return f"Fall {d.year}"
    else:
        raise Exception(f"invalid month {d.month}")


class CourwiseRatingsDriver(IVisualizationDriver):
    def visualize(self) -> VisualizationResult:
        df = self.df[self.df["my_start_date"] != "0000-00-00"]
        df["my_start_date"] = pd.to_datetime(df["my_start_date"])

        df.set_index("my_start_date", inplace=True)

        # Resample the DataFrame based on quarters
        quarterly_groups = df.resample("Q")

        quarter_ratings = {}

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
        }

        cours = quarter_percentages.keys()
        X = np.arange(len(cours))
        bad_plottable = np.array([t[0] for t in quarter_percentages.values()])
        average_plottable = np.array([t[1] for t in quarter_percentages.values()])
        good_plottable = np.array([t[2] for t in quarter_percentages.values()])

        fig, ax = plt.subplots()
        ax.set_title(
            "Ratings of anime in each cour as percentage of total anime I watched that season"
        )
        ax.set_xlabel("Cours (doesnt include only seasonal anime)")
        ax.set_ylabel("Bad, Average and Good rating percentages")

        bad_bar = ax.bar(cours, bad_plottable, color="r", label="bad rating ∈ [1, 4]")
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

        ax.legend()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)

		# todo fix the graph a little bit
        result = VisualizationResult(
            "Courwise Ratings", self.to_base64(buf).decode("utf-8")
        )

        return result
