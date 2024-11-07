import base64
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from matplotlib import use as plt_use
from matplotlib.figure import Figure as PltFigure


@dataclass(frozen=True)
class VisualizationOptions:
    """
    Options to consider while drawing visualizations.
    """

    disable_nsfw: bool
    count_upcoming: bool
    interactive_charts: bool


@dataclass(frozen=True)
class MatplotlibVisualizationResult:
    """
    Represents a visualization result of a chart rendered by matplotlib.
    The image is of type `str` and must be a base64 string.
    """

    title: str
    image: str

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class PlotlyVisualizationResult:
    """
    Represents a visualization result of a chart rendered by plotly.
    The figure is of type `plotly.graph_objects.Figure`.
    """

    title: str
    figure: go.Figure

    def as_dict(self):
        """
        Converts this dataclass to a dictionary, with figure converted to JSON.
        """
        # add modebar before converting to dictionary
        # todo dirty fix, but works for now
        fig = self.figure.update_layout(modebar_add=["v1hovermode", "toggleSpikeLines"])
        return {"title": self.title, "figure": pio.to_json(fig)}


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
        # pio.templates.default = "seaborn"

    @staticmethod
    def _to_base64(buf: BytesIO):
        buf.seek(0)
        img_str = base64.b64encode(buf.read())
        buf.close()
        return img_str

    def get_not_enough_data_image(self):
        img_path = Path(__file__).parent / "not_enough_data_to_visualize.png"
        with open(str(img_path), "rb") as img:
            image_b64 = base64.b64encode(img.read()).decode("utf-8")
        return image_b64

    def b64_image_from_plt_fig(self, fig: PltFigure):
        """
        Takes a matplotlib `Figure` and returns a decoded base64 image.
        """
        buf = BytesIO()
        fig.savefig(buf, format="png")
        image = self._to_base64(buf).decode("utf-8")
        buf.close()
        return image

    @abstractmethod
    def visualize(self) -> MatplotlibVisualizationResult | PlotlyVisualizationResult:
        """
        The visualize method contains the code for using matplotlib to render a chart and wrap it
        with a VisualizationResult.
        """
        pass
