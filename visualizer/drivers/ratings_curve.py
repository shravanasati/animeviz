from collections import Counter
from matplotlib import pyplot as plt

from .base import IVisualizationDriver, VisualizationResult


class RatingsCurveDriver(IVisualizationDriver):
    def visualize(self) -> VisualizationResult:
        df = self.df[self.df["my_score"] != 0]
        ratings = Counter(df["my_score"])

        fig, ax = plt.subplots()
        ax.set_title("Ratings Distribution")
        ax.set_ylabel("Rating Count")
        ax.set_xlabel("Rating Value (1-10)")
        ax.set_xticks(range(1, 11))
        ratings_bar = ax.bar(range(1, 11), [ratings[i] for i in range(1, 11)])
        ax.bar_label(ratings_bar)

        return VisualizationResult("Ratings Curve", self.b64_image_from_plt_fig(fig))
