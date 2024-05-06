from collections import Counter

import plotly.express as px
from matplotlib import pyplot as plt

from .base import (
    IVisualizationDriver,
    MatplotlibVisualizationResult,
    PlotlyVisualizationResult,
)


class RatingsCurveDriver(IVisualizationDriver):
    def visualize(self):
        df = self.df[self.df["my_score"] != 0]
        if len(df) == 0:
            return MatplotlibVisualizationResult(
                "Ratings Curve", self.get_not_enough_data_image()
            )

        if self.opts.interactive_charts:
            # plotly code
            ratings = df["my_score"].value_counts().sort_index()

            fig = px.bar(
                x=ratings.index,
                y=ratings.values,
                labels={"x": "Rating Value (1-10)", "y": "Rating Count"},
            )
            fig.update_xaxes(
                type="category", tickmode="array", tickvals=list(range(1, 11))
            )
            fig.update_traces(marker_color="skyblue", opacity=0.7)
            fig.update_layout(
                title="Ratings Distribution",
                xaxis_title="Rating Value (1-10)",
                yaxis_title="Rating Count",
            )
            return PlotlyVisualizationResult("Ratings Curve", fig)

        # matplotlib code
        ratings = Counter(df["my_score"])

        fig, ax = plt.subplots()
        ax.set_title("Ratings Distribution")
        ax.set_ylabel("Rating Count")
        ax.set_xlabel("Rating Value (1-10)")
        ax.set_xticks(range(1, 11))
        ratings_bar = ax.bar(range(1, 11), [ratings[i] for i in range(1, 11)])
        ax.bar_label(ratings_bar)

        return MatplotlibVisualizationResult(
            "Ratings Curve", self.b64_image_from_plt_fig(fig)
        )
