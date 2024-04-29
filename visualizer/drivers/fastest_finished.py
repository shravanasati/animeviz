import heapq
import pandas as pd
import matplotlib.pyplot as plt

from .base import IVisualizationDriver, VisualizationResult


class FastestFinishedDriver(IVisualizationDriver):
    def visualize(self) -> VisualizationResult:
        final_ignored = self.NSFW_GENRES if self.opts.disable_nsfw else tuple()

        # filter anime which are completed and whose start and finish dates exist
        df = self.df[
            (self.df["my_status"] == "Completed")
            & (self.df["my_start_date"] != "0000-00-00")
            & (self.df["my_finish_date"] != "0000-00-00")
            & (self.df["my_watched_episodes"] != 0)
        ]

        # convert date columns to actual dates
        df.loc[:, "my_start_date"] = pd.to_datetime(
            df["my_start_date"], format="ISO8601"
        )
        df.loc[:, "my_finish_date"] = pd.to_datetime(
            df["my_finish_date"], format="ISO8601"
        )

        df.loc[:, "episode_day_ratio"] = (df["my_finish_date"] - df["my_start_date"])
        df.loc[:, "episode_day_ratio"] = df["episode_day_ratio"].apply(lambda x: x.days)
        df.loc[:, "episode_day_ratio"] /= df["my_watched_episodes"]

        fastest_finished_tuple = heapq.nsmallest(
            6, zip(df["series_title"], df["episode_day_ratio"]), key=lambda t: t[1]
        )
        fastest_finished_titles = [t[0] for t in fastest_finished_tuple]
        fastest_finished_ratio = [t[1] for t in fastest_finished_tuple]

        fig, ax = plt.subplots()
        ax.set_title("Fastest Finished Anime (by episodes watched per day)")
        ax.set_xlabel("Anime Names")
        ax.set_ylabel("Episodes watched per day")
        bar = ax.bar(fastest_finished_titles, fastest_finished_ratio)
        ax.bar_label(bar)
        fig.autofmt_xdate()

        return VisualizationResult(
            "Fastest Finished Anime", self.b64_image_from_plt_fig(fig)
        )
