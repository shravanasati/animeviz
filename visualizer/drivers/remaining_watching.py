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
        remaining = total_episodes - watched
        Y = np.arange(len(anime_names))

        fig, ax = plt.subplots()
        ax.set_title("Remaining Content View")
        ax.set_ylabel("Anime")
        ax.set_xlabel("Episode Count")

        # todo scale remaining and watched bars such they add up to 100

        ax.barh(
            Y, total_episodes, align="center", label="remaining", color="y"
        )
        # ax.bar_label(total_bar, label_type="edge")
        for rect, rc in zip(ax.patches, remaining):
            # rc is the remaining count

            xval = rect.get_width()
            yval = rect.get_y() + rect.get_height() / 2

            space = 5  # space b/w bar and label
            ha = "left"
            if xval < 0:
                space *= -1
                ha = "right"

            ax.annotate(
                rc,
                (xval, yval),
                xytext=(space, 0),
                textcoords="offset points",
                va="center",
                ha=ha,
            )

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
