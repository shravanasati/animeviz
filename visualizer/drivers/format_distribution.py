import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px

from .base import (
    IVisualizationDriver,
    MatplotlibVisualizationResult,
    PlotlyVisualizationResult,
)


class FormatDistributionDriver(IVisualizationDriver):
    def visualize(self):
        if len(self.df) == 0:
            return MatplotlibVisualizationResult(
                "Format Distribution", self.get_not_enough_data_image()
            )

        final_ignored = self.IGNORE_GENRES + (
            self.NSFW_GENRES if self.opts.disable_nsfw else tuple()
        )
        formats = dict()
        series_type = self.df["series_type"]
        for i, genres in enumerate(self.df["series_genres"]):
            for genre in genres:
                if genre in final_ignored or series_type[i] in (
                    "PV",
                    "Music",
                    "Unknown",
                ):
                    continue
                if formats.get(series_type[i]):
                    formats[series_type[i]] += 1
                else:
                    formats[series_type[i]] = 1

        if self.opts.interactive_charts:
            # pie chart using plotly
            df_plottable = pd.DataFrame(formats.items(), columns=["Format", "Count"])

            fig = px.pie(
                df_plottable,
                values="Count",
                names="Format",
                title="Format Distribution",
                hole=0.1,
                labels={"Count": "Percentage"},
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            return PlotlyVisualizationResult("Format Distribution", fig)

        # pie chart using matplotlib
        fig, ax = plt.subplots()
        ax.axis("equal")
        ax.set_title("Anime Format Distribution")
        explode = [0 if i % 2 else 0.1 for i in range(len(formats))]
        ax.pie(
            formats.values(),
            labels=formats.keys(),
            explode=explode,
            shadow=True,
            autopct="%1.1f%%",
            labeldistance=1.2,
            pctdistance=0.6,
        )

        return MatplotlibVisualizationResult(
            "Format Distribution", self.b64_image_from_plt_fig(fig)
        )
