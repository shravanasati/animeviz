import pandas as pd
import plotly.express as px
from matplotlib import pyplot as plt

from .base import (
    IVisualizationDriver,
    MatplotlibVisualizationResult,
    PlotlyVisualizationResult,
)


class GenrewiseRatingsDriver(IVisualizationDriver):
    # todo consider using a scatter plot
    def visualize(self):
        df = self.df[
            (self.df["my_status"] != "Plan to Watch") & (self.df["my_score"] != 0)
        ]
        if len(df) == 0:
            return MatplotlibVisualizationResult(
                "Genrewise Ratings", self.get_not_enough_data_image()
            )

        items = zip(df["series_genres"], df["my_score"])

        genres_data: dict[str, list[int]] = {}

        for genres_score_pair in items:
            genres = genres_score_pair[0]
            rating = genres_score_pair[1]
            for g in genres:
                if g in genres_data:
                    genres_data[g].append(rating)
                else:
                    genres_data[g] = [rating]

        if self.opts.disable_nsfw:
            for g in self.NSFW_GENRES:
                if g in genres_data:
                    genres_data.pop(g)

        average_data = {
            k: round(sum(v) / len(v), 2) for k, v in genres_data.items() if len(v) != 0
        }
        plottable_data = dict(sorted(average_data.items(), key=lambda x: x[1]))

        if self.opts.interactive_charts:
            # plotly code
            df_plottable = pd.DataFrame(
                plottable_data.items(), columns=["Genres", "Average Rating"]
            )

            fig = px.bar(
                df_plottable,
                x="Genres",
                y="Average Rating",
                title="Average rating of anime per genre",
            )

            return PlotlyVisualizationResult("Genrewise Ratings", fig)

        # matplotlib code
        fig, ax = plt.subplots()
        ax.set_title("Average rating of anime per genre")
        ax.set_xlabel("Genres")
        ax.set_ylabel("Average rating (out of 10)")

        bar = ax.bar(plottable_data.keys(), plottable_data.values())
        ax.bar_label(bar)
        fig.autofmt_xdate()

        return MatplotlibVisualizationResult(
            "Genrewise Ratings", self.b64_image_from_plt_fig(fig)
        )
