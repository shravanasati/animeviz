from matplotlib import pyplot as plt
import numpy as np

from .base import IVisualizationDriver, VisualizationResult


def trim_anime_title(name: str):
    max_name_length = 12
    return name[: max_name_length + 1] + "..."


class RemainingCountDriver(IVisualizationDriver):
    def visualize(self) -> VisualizationResult:
        df = self.df[self.df["my_status"] == "Watching"]
        anime_names = df["series_title"].apply(trim_anime_title)
        watched = df["my_watched_episodes"]
        total_episodes = df["series_episodes"]
        Y = np.arange(len(anime_names))

        fig, ax = plt.subplots()
        ax.set_title("Remaining Content View")
        ax.set_ylabel("Anime")
        ax.set_xlabel("Episode Count")

        # todo scale remaining and watched bars such they add up to 100

        total_bar = ax.barh(
            Y, total_episodes, align="center", label="remaining", color="y"
        )
        ax.bar_label(total_bar, label_type="edge")

        watched_bar = ax.barh(Y, watched, align="center", label="watched", color="g")
        ax.bar_label(watched_bar, label_type="center")

        ax.set_yticks(Y, labels=anime_names, rotation=60)
        ax.legend(fancybox=True, framealpha=0.5)
        ax.tick_params(
            axis="x", which="both", bottom=False, top=False, labelbottom=False
        )

        return VisualizationResult(
            "Remaining Watching Content", self.b64_image_from_plt_fig(fig)
        )
