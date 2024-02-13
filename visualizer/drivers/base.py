from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
from io import BytesIO

import pandas as pd


@dataclass(frozen=True)
class VisualizationOptions:
    """
    Options to consider while drawing visualizations.
    """

    disable_nsfw: bool
    count_upcoming: bool


# from myanimelist's list of explicit genres
NSFW_GENRES = ("Erotica", "Ecchi", "Hentai")
IGNORE_GENRES = ("Avant Garde", "Award Winning")


class IVisualizationDriver(ABC):
    """
    Abstract base class for visualization drivers.
    """

    def __init__(self, df: pd.DataFrame, opts: VisualizationOptions) -> None:
        self.df = df
        self.opts = opts

    @staticmethod
    def to_base64(buf: BytesIO):
        buf.seek(0)
        img_str = base64.b64encode(buf.read())
        buf.close()
        return img_str

    @abstractmethod
    def visualize(self) -> BytesIO:
        raise NotImplementedError("visualize method not implemented")
