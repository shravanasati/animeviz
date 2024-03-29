import base64
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from io import BytesIO

import pandas as pd
from matplotlib.figure import Figure
from matplotlib import use as plt_use


@dataclass(frozen=True)
class VisualizationOptions:
    """
    Options to consider while drawing visualizations.
    """

    disable_nsfw: bool
    count_upcoming: bool


@dataclass(frozen=True)
class VisualizationResult:
    """
    Represents a visualization result. The image is of type `str` and must be a base64 string.
    """

    title: str
    image: str

    def as_dict(self):
        return asdict(self)


class IVisualizationDriver(ABC):
    """
    Abstract base class for visualization drivers.
    """

    # from myanimelist's list of explicit genres
    NSFW_GENRES = ("Erotica", "Ecchi", "Hentai")
    IGNORE_GENRES = ("Avant Garde", "Award Winning")

    def __init__(self, df: pd.DataFrame, opts: VisualizationOptions) -> None:
        self.df = df
        self.opts = opts
        plt_use("agg")

    @staticmethod
    def _to_base64(buf: BytesIO):
        buf.seek(0)
        img_str = base64.b64encode(buf.read())
        buf.close()
        return img_str

    def b64_image_from_plt_fig(self, fig: Figure):
        """
        Takes a matplotlib `Figure` and returns a decoded base64 image.
        """
        buf = BytesIO()
        fig.savefig(buf, format="png")
        image = self._to_base64(buf).decode("utf-8")
        buf.close()
        return image

    @abstractmethod
    def visualize(self) -> VisualizationResult:
        """
        The visualize method contains the code for using matplotlib to render a chart and wrap it
        with a VisualizationResult.
        """
        pass
