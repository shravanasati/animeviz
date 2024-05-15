import heapq

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px

from .base import (
    IVisualizationDriver,
    MatplotlibVisualizationResult,
    PlotlyVisualizationResult,
)
from .remaining_watching import trim_anime_title


class FastestFinishedDriver(IVisualizationDriver):
    def visualize(self):
        final_ignored = self.NSFW_GENRES if self.opts.disable_nsfw else tuple()

        # filter anime which are completed and whose start and finish dates exist
        df = self.df[
            (self.df["my_status"] == "Completed")
            & (self.df["my_start_date"] != "0000-00-00")
            & (self.df["my_finish_date"] != "0000-00-00")
            & (self.df["my_watched_episodes"] != 0)
        ]

        if len(df) == 0:
            return MatplotlibVisualizationResult(
                "Fastest Finished Anime", self.get_not_enough_data_image()
            )

        # convert date columns to actual dates
        df.loc[:, "my_start_date"] = pd.to_datetime(
            df["my_start_date"], format="ISO8601"
        )
        df.loc[:, "my_finish_date"] = pd.to_datetime(
            df["my_finish_date"], format="ISO8601"
        )

        df.loc[:, "episode_day_ratio"] = (
            df.loc[:, "my_finish_date"] - df.loc[:, "my_start_date"]
        )
        df.loc[:, "episode_day_ratio"] = df.loc[:, "episode_day_ratio"].apply(
            lambda x: x.days if x.days > 0 else 1
        )
        df.loc[:, "episode_day_ratio"] = (
            df.loc[:, "my_watched_episodes"] / df.loc[:, "episode_day_ratio"]
        )

        fastest_finished_tuple = heapq.nlargest(
            10, zip(df["series_title"], df["episode_day_ratio"]), key=lambda t: t[1]
        )
        fastest_finished_titles = [
            trim_anime_title(t[0], 15) for t in fastest_finished_tuple
        ]
        fastest_finished_ratio = [t[1] for t in fastest_finished_tuple]

        if self.opts.interactive_charts:
            # plotly code
            df_plottable = pd.DataFrame(
                {
                    "Anime Names": fastest_finished_titles,
                    "Episodes watched per day": fastest_finished_ratio,
                }
            )

            fig = px.bar(
                df_plottable,
                x="Anime Names",
                y="Episodes watched per day",
                title="Fastest Finished Anime (by episodes watched per day)",
                color_discrete_sequence=[
                    "#FF9999",
                    "#66B3FF",
                    "#99FF99",
                    "#FFCC99",
                    "#FFD700",
                    "#FF6347",
                ],
            )

            return PlotlyVisualizationResult("Fastest Finished Anime", fig)

        # matplotlib code
        fig, ax = plt.subplots()
        ax.set_title("Fastest Finished Anime (by episodes watched per day)")
        ax.set_xlabel("Anime Names")
        ax.set_ylabel("Episodes watched per day")
        bar = ax.bar(
            fastest_finished_titles,
            fastest_finished_ratio,
            color=["#FF9999", "#66B3FF", "#99FF99", "#FFCC99", "#FFD700", "#FF6347"],
        )
        ax.bar_label(bar)
        fig.autofmt_xdate()  # rotate xticks

        return MatplotlibVisualizationResult(
            "Fastest Finished Anime", self.b64_image_from_plt_fig(fig)
        )
