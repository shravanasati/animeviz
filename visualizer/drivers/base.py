import base64
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from io import BytesIO

import pandas as pd
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
    Represents a visualization result.
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
    def to_base64(buf: BytesIO):
        buf.seek(0)
        img_str = base64.b64encode(buf.read())
        buf.close()
        return img_str

    @abstractmethod
    def visualize(self) -> VisualizationResult:
        raise NotImplementedError("visualize method not implemented")
