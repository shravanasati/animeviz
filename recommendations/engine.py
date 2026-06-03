from dataclasses import dataclass
from datetime import date
from pprint import pprint
from typing import NamedTuple

import numpy as np


from recommendations.anime_store import AnimeStore
from recommendations.embed import EmbeddingGenerator
from recommendations.qdrant_store import QdrantStore


CANDIDATE_SET_SIZE = 200
NUM_RECOMMENDATIONS = 20


class AnimeRelation(NamedTuple):
    id: int
    title: str
    relation: str


@dataclass(frozen=True, slots=True)
class AnimePayload:
    id: int
    title: str
    alt_title_en: str
    alt_title_jp: str
    start_date: date | None
    end_date: date | None
    mean: float
    rank: int
    popularity: int
    num_list_users: int
    num_scoring_users: int
    media_type: str
    status: str
    genres: list[str]
    themes: list[str]
    demographics: list[str]
    num_episodes: int
    average_episode_duration: str
    rating: str
    related_anime: list[AnimeRelation]
    studios: list[str]

    @staticmethod
    def _parse_date(date_str: str):
        if not date_str:
            return None
        return date.fromisoformat(date_str.split("T")[0])

    @staticmethod
    def _parse_list(list_str: str, delim: str = "|"):
        return [i.strip() for i in list_str.split(delim) if i.strip()]

    @staticmethod
    def _parse_relations(relations_list: list[str]):
        relations: list[AnimeRelation] = []
        for item in relations_list:
            splitted = item.split("|")
            if len(splitted) != 3:
                continue
            id_, title, relation = splitted
            relations.append(AnimeRelation(int(id_), title, relation))

        return relations

    @classmethod
    def from_dict(cls, d: dict):
        return AnimePayload(
            id=d["id"],
            title=d["title"],
            alt_title_en=d["alt_title_en"],
            alt_title_jp=d["alt_title_jp"],
            start_date=cls._parse_date(d["start_date"]),
            end_date=cls._parse_date(d["end_date"]),
            mean=d["mean"],
            rank=int(d["rank"]),
            popularity=int(d["popularity"]),
            num_list_users=int(d["num_list_users"]),
            num_scoring_users=int(d["num_scoring_users"]),
            media_type=d["media_type"],
            status=d["status"],
            genres=cls._parse_list(d["genres"]),
            themes=cls._parse_list(d["themes"]),
            demographics=cls._parse_list(d["demographics"]),
            studios=cls._parse_list(d["studios"]),
            num_episodes=int(d["num_episodes"]),
            rating=d["rating"],
            average_episode_duration=d["average_episode_duration"],
            related_anime=cls._parse_relations(
                cls._parse_list(d["related_anime"], ";")
            ),
        )


@dataclass(frozen=True, slots=True)
class AnimeRecommendation:
    mal_id: int
    title: str
    title_en: str


class RecommendationEngine:
    def __init__(self) -> None:
        self.embedgen = EmbeddingGenerator()
        self.qdrant_store = QdrantStore()
        self.anime_store = AnimeStore()

    def _retrieve(self, userlist_ids: list[int]):
        userlist_df = self.anime_store.df[self.anime_store.df["id"].isin(userlist_ids)]
        userlist_df_rows = userlist_df.to_dict(orient="records")

        if userlist_df_rows:
            userlist_embeddings = np.array(self.embedgen.embed_anime_rows(userlist_df_rows))
        else:
            embedding_size = self.embedgen.model.embedding_size
            userlist_embeddings = np.random.random((10, embedding_size))

        avg_vector = self._average_vector(userlist_embeddings)

        return [
            AnimePayload.from_dict(r.payload)
            for r in self.qdrant_store.search_similar_anime(
                avg_vector, userlist_ids, CANDIDATE_SET_SIZE
            ).points
        ]

    @staticmethod
    def _average_vector(userlist_embeddings: np.ndarray):
        # todo implement weighted average
        avg_vector = (np.sum(userlist_embeddings, axis=0)) / len(userlist_embeddings)
        return avg_vector

    def _rank(
        self, userlist: list[int], candidate_set: list[AnimePayload]
    ) -> list[AnimeRecommendation]:
        scored_set: list[tuple[float, AnimePayload]] = []
        # todo handle userlist
        for candidate in candidate_set:
            score = self._calculate_score(candidate)
            scored_set.append((score, candidate))

        return [
            AnimeRecommendation(
                mal_id=i[1].id, title=i[1].title, title_en=i[1].alt_title_en
            )
            for i in sorted(scored_set, reverse=True, key=lambda x: x[0])
        ]

    @staticmethod
    def _calculate_score(candidate: AnimePayload):
        score = 0
        score += (candidate.mean / 10) ** 2
        # todo implement more heuristics
        # score += (candidate.)
        return score

    def recommendations(self, userlist: list[int]) -> list[AnimeRecommendation]:
        # todo userlist is a dataframe instead of just list of IDs
        candidate_set = self._retrieve(userlist)
        ranked = self._rank(userlist, candidate_set)
        return ranked[:NUM_RECOMMENDATIONS]


if __name__ == "__main__":
    receng = RecommendationEngine()
    # frieren, mt, eminence, dungeon
    # pprint(receng.recommendations([52991, 39535, 48316, 52701]))
    pprint(receng.recommendations([]))
