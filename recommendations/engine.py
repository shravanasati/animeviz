from dataclasses import dataclass

import numpy as np


from recommendations.anime_store import AnimeStore
from recommendations.embed import EmbeddingGenerator
from recommendations.qdrant_store import QdrantStore


@dataclass(frozen=True, slots=True)
class AnimeRecommendation:
    mal_id: int
    title: str


class RecommendationEngine:
    def __init__(self) -> None:
        self.embedgen = EmbeddingGenerator()
        self.qdrant_store = QdrantStore()
        self.anime_store = AnimeStore()

    def _retrieve(self, userlist_ids: list[int]):
        userlist_df = self.anime_store.df[self.anime_store.df["id"].isin(userlist_ids)]
        userlist_df_rows = userlist_df.to_dict(orient="records")

        userlist_embeddings = np.array(self.embedgen.embed_anime_rows(userlist_df_rows))
        avg_vector = self._average_vector(userlist_embeddings)
        print(
            [
                r.payload["alt_title_en"]
                for r in self.qdrant_store.similarity_search(avg_vector).points
            ]
        )

    @staticmethod
    def _average_vector(userlist_embeddings: np.ndarray):
        avg_vector = (np.sum(userlist_embeddings, axis=0)) / len(userlist_embeddings)
        return avg_vector

    def recommend(self, userlist: list[int]) -> list[AnimeRecommendation]:
        candidate_set = self._retrieve(userlist)
        final = self._rank(candidate_set)


if __name__ == "__main__":
    receng = RecommendationEngine()
    # frieren, mt, eminence, dungeon
    receng._retrieve([52991, 39535, 48316, 52701])
