from pathlib import Path


import pandas as pd


DATASET_FILE = "anime_data_cleaned.csv"


class AnimeStore:
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self.df = self._preprocess(
            pd.read_csv(Path(__file__).parent.parent / DATASET_FILE)
        )

    @staticmethod
    def _preprocess(df: pd.DataFrame):
        df["start_date"] = df["start_date"].fillna("")
        df["end_date"] = df["end_date"].fillna("")

        textcols = [
            "synopsis",
            "genres",
            "themes",
            "demographics",
            "studios",
            "related_anime",
            "alt_title_en",
            "alt_title_jp",
        ]
        for col in textcols:
            df[col] = df[col].fillna("")

        return df
