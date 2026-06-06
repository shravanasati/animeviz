from collections import Counter
from dataclasses import dataclass, asdict
from datetime import date
import math
from typing import Literal, NamedTuple

import numpy as np
import pandas as pd


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

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RecommendationOpts:
    disable_nsfw: bool
    average_algo: Literal["weighted"] | Literal["unweighted"] = "weighted"
    ranking_features: Literal["all"] | Literal["score"] = "all"


class RecommendationEngine:
    def __init__(self) -> None:
        self.embedgen = EmbeddingGenerator()
        self.qdrant_store = QdrantStore()
        self.anime_store = AnimeStore()

    def _retrieve(self, userlist: pd.DataFrame, opts: RecommendationOpts):
        # the fields are in parity with those defined in api_helper.py
        userlist_ids = (userlist["series_animedb_id"]).to_list()

        userlist_df = self.anime_store.df[self.anime_store.df["id"].isin(userlist_ids)]
        userlist_df_rows = userlist_df.to_dict(orient="records")

        if userlist_df_rows:
            userlist_embeddings = np.array(
                self.embedgen.embed_anime_rows(userlist_df_rows)
            )
        else:
            embedding_size = self.embedgen.model.embedding_size
            userlist_embeddings = np.random.random((10, embedding_size))

        avg_func = (
            self._average_vector_weighted
            if opts.average_algo == "weighted"
            else self._average_vector_unweighted
        )

        avg_vector = avg_func(userlist_embeddings, userlist)

        return [
            (AnimePayload.from_dict(r.payload), r.score)
            for r in self.qdrant_store.search_similar_anime(
                avg_vector.tolist(), userlist_ids, CANDIDATE_SET_SIZE, opts.disable_nsfw
            ).points
        ]

    @staticmethod
    def _average_vector_unweighted(
        userlist_embeddings: np.ndarray, userlist: pd.DataFrame
    ):
        return np.average(userlist_embeddings, axis=0)

    @staticmethod
    def _average_vector_weighted(
        userlist_embeddings: np.ndarray, userlist: pd.DataFrame
    ):
        status_weights = {
            "Completed": 1.0,
            "Watching": 0.85,
            "On Hold": 0.5,
            "Dropped": 0.2,
        }
        userlist["score_weight"] = (userlist["my_score"] / 10) ** 2
        userlist["status_weight"] = userlist["my_status"].apply(
            lambda x: status_weights.get(x, 0)
        )

        # using guassian decay for calculating recency weight
        reference_date = pd.to_datetime(pd.Timestamp.today())
        userlist["days_passed"] = userlist["my_date"]
        half_life_days = 30.0
        sigma = half_life_days / np.sqrt(2 * np.log(2))
        userlist["days_passed"] = (reference_date - userlist["my_date"]).dt.days
        userlist["recency_weight"] = np.exp(
            -(userlist["days_passed"] ** 2) / (2 * (sigma**2))
        )

        userlist["progress_weight"] = userlist["my_watched_episodes"].div(
            userlist["series_episodes"]
        )
        userlist.loc[~np.isfinite(userlist["progress_weight"]), "progress_weight"] = 0

        weights = (
            userlist["score_weight"]
            + userlist["progress_weight"]
            + userlist["recency_weight"]
            + userlist["status_weight"]
        ).to_numpy()
        weights /= weights.sum()

        avg_vector = np.average(userlist_embeddings, weights=weights, axis=0)
        return avg_vector

    def _rank_naive(self, candidate_set: list[tuple[AnimePayload, float]]):
        scored_set: list[tuple[float, AnimePayload]] = []
        for candidate, _ in candidate_set:
            score = (candidate.mean / 10) ** 2
            scored_set.append((score, candidate))

        return [
            AnimeRecommendation(
                mal_id=i[1].id, title=i[1].title, title_en=i[1].alt_title_en
            )
            for i in sorted(scored_set, reverse=True, key=lambda x: x[0])
        ]

    def _rank(
        self, userlist: pd.DataFrame, candidate_set: list[tuple[AnimePayload, float]]
    ) -> list[AnimeRecommendation]:
        # feature weights
        WEIGHT_SIM = 1.0
        WEIGHT_QUALITY = 0.7
        WEIGHT_POPULARITY = 0  # 0.4
        WEIGHT_NOVELTY = 0  # 0.15
        WEIGHT_TIME = 0.05
        RELATED_BOOST = 0.6

        # popularity smoothing constant to avoid extreme boosts for very obscure items
        POP_C = 50.0

        # gather user ids for related-anime checks
        user_ids = set((userlist["series_animedb_id"]).to_list())

        # prepare intermediate feature list
        feats: list[dict] = []
        pops: list[float] = []
        for candidate, sim_score in candidate_set:
            pop = float(max(1, candidate.popularity or 1))
            pops.append(pop)
            feats.append(
                {
                    "candidate": candidate,
                    "sim": float(sim_score),
                    "mean": float(candidate.mean or 0.0),
                    "pop": pop,
                    "start_year": candidate.start_date.year
                    if candidate.start_date
                    else None,
                    "related_ids": [r.id for r in candidate.related_anime],
                }
            )

        if not feats:
            return []

        pop_min = min(pops)
        pop_max = max(pops)
        pop_range = pop_max - pop_min if pop_max > pop_min else 1.0

        # compute base scores
        for f in feats:
            sim_term = WEIGHT_SIM * f["sim"]

            quality_term = WEIGHT_QUALITY * ((f["mean"] / 10.0) ** 2)

            popularity_term = WEIGHT_POPULARITY * (1.0 / math.log(f["pop"] + POP_C))

            # novelty = 1 - normalized_popularity (small weight)
            pop_norm = (f["pop"] - pop_min) / pop_range
            novelty_term = WEIGHT_NOVELTY * (1.0 - pop_norm)

            # time bias: reward more recent (small)
            if f["start_year"] is not None:
                years_diff = abs(date.today().year - f["start_year"])
                time_score = max(0.0, 1.0 - min(years_diff / 30.0, 1.0))
            else:
                time_score = 0.0
            time_term = WEIGHT_TIME * time_score

            # related anime boost
            related_term = (
                RELATED_BOOST if any(r in user_ids for r in f["related_ids"]) else 0.0
            )

            base_score = (
                sim_term
                + quality_term
                + popularity_term
                + novelty_term
                + time_term
                + related_term
            )

            f["base_score"] = base_score

        # diversity-aware greedy selection with genre-penalty
        genre_counts = Counter()
        selected: list[dict] = []
        remaining = feats.copy()

        # cap selection to NUM_RECOMMENDATIONS or available candidates
        select_k = min(NUM_RECOMMENDATIONS, len(remaining))

        for _ in range(select_k):
            # compute adjusted scores with genre penalty
            best_idx = None
            best_score = -math.inf
            for idx, f in enumerate(remaining):
                multiplier = 1.0
                # if any genre already overrepresented, apply penalty
                for g in f["candidate"].genres:
                    if genre_counts[g] >= 4:
                        multiplier = 0.8
                        break

                adjusted = f["base_score"] * multiplier
                if adjusted > best_score:
                    best_score = adjusted
                    best_idx = idx

            if best_idx is None:
                break

            pick = remaining.pop(best_idx)
            # update genre counts
            for g in pick["candidate"].genres:
                genre_counts[g] += 1

            selected.append(pick)

        # return ordered AnimeRecommendation list
        return [
            AnimeRecommendation(
                mal_id=s["candidate"].id,
                title=s["candidate"].title,
                title_en=s["candidate"].alt_title_en,
            )
            for s in selected
        ]

    @staticmethod
    def _prepare_userlist_df(df: pd.DataFrame):
        # fill NaN scores with 0
        df["my_score"] = df["my_score"].fillna(0)
        df["my_watched_episodes"] = df["my_watched_episodes"].fillna(0).astype(float)
        df["series_episodes"] = df["series_episodes"].fillna(0).astype(float)

        # Resolve a single date column with priority:
        # finish_date -> watching(today) -> start_date -> 2000-01-01.
        finish_dates = df["my_finish_date"].fillna("0000-00-00").astype(str)
        start_dates = df["my_start_date"].fillna("0000-00-00").astype(str)
        watching = df["my_status"].astype(str).eq("Watching")
        today_str = date.today().isoformat()

        resolved_dates = np.where(
            finish_dates != "0000-00-00",
            finish_dates,
            np.where(
                watching,
                today_str,
                np.where(start_dates != "0000-00-00", start_dates, "2000-01-01"),
            ),
        )

        df["my_date"] = pd.to_datetime(resolved_dates, errors="coerce").fillna(
            pd.Timestamp("2000-01-01")
        )

        # drop PTW entries
        df = df.drop(df[df["my_status"] == "Plan to Watch"].index)

        return df

    def recommendations(
        self, userlist: pd.DataFrame, opts: RecommendationOpts
    ) -> list[AnimeRecommendation]:
        userlist = self._prepare_userlist_df(userlist)
        candidate_set = self._retrieve(userlist, opts)
        if opts.ranking_features == "all":
            ranked = self._rank(userlist, candidate_set )
        else:
            ranked = self._rank_naive(candidate_set)
        return ranked[:NUM_RECOMMENDATIONS]


if __name__ == "__main__":
    # print(RecommendationEngine._average_vector(np.arange(1, 7).reshape((2, 3)), None))
    receng = RecommendationEngine()
    # frieren, mt, eminence, dungeon
    # pprint(receng.recommendations([52991, 39535, 48316, 52701]))
    # pprint(receng.recommendations([]))
