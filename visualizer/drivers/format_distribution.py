import matplotlib.pyplot as plt

from .base import IVisualizationDriver, VisualizationResult


class FormatDistributionDriver(IVisualizationDriver):
    def visualize(self) -> VisualizationResult:
        final_ignored = self.IGNORE_GENRES + (
            self.NSFW_GENRES if self.opts.disable_nsfw else tuple()
        )
        formats = dict()
        series_type = self.df["series_type"]
        for i, genres in enumerate(self.df["series_genres"]):
            for genre in genres:
                if genre in final_ignored or series_type[i] in ("PV", "Music", "Unknown"):
                    continue
                if formats.get(series_type[i]):
                    formats[series_type[i]] += 1
                else:
                    formats[series_type[i]] = 1

        # pie chart
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

        return VisualizationResult(
            "Format Distribution", self.b64_image_from_plt_fig(fig)
        )
