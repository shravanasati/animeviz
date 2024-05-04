from collections import Counter

import matplotlib.pyplot as plt

from .base import IVisualizationDriver, VisualizationResult


class GenreDistributionDriver(IVisualizationDriver):
    def visualize(self) -> VisualizationResult:
        if len(self.df) == 0:
            return VisualizationResult(
                "Genre Distribution", self.get_not_enough_data_image()
            )

        genres = self.get_genre_count()

        # pie chart
        fig, ax = plt.subplots()
        ax.axis("equal")
        ax.set_title("Anime Genre Distribution")
        explode = [0 if i % 2 else 0.1 for i in range(len(genres))]
        ax.pie(
            genres.values(),
            labels=genres.keys(),
            explode=explode,
            shadow=True,
            autopct="%1.1f%%",
            labeldistance=1.2,
            pctdistance=0.6,
        )

        return VisualizationResult(
            "Genre Distribution", self.b64_image_from_plt_fig(fig)
        )

    def get_genre_count(
        self,
    ):
        """
        Takes a dataframe which contains anime names and their respective genres.
        Returns a dictionary containing different genres as key and their count as values.
        """
        # todo implement count upcoming option
        genres = self.df["series_genres"]
        genre_count = Counter()
        for genre_list in genres:
            genre_count.update(Counter(genre_list))
        final_ignored = self.IGNORE_GENRES + (
            self.NSFW_GENRES if self.opts.disable_nsfw else tuple()
        )
        for ignore_genre in final_ignored:
            if ignore_genre in genre_count:
                genre_count.pop(ignore_genre)
        # for _, row in self.df.iterrows():
        #     for g in row["genres"]:
        #         skip_conditions = (g in self.IGNORE_GENRES, g in self.NSFW_GENRES and self.opts.disable_nsfw)
        #         if any(skip_conditions):
        #             continue

        #         if g not in genres.keys():
        #             genres.update({g: 1})
        #         else:
        #             prev = genres[g]
        #             genres.update({g: prev + 1})

        return genre_count
