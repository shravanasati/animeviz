from functools import lru_cache
from animec import Anime


@lru_cache(maxsize=256)
def get_anime_genre(anime_name: str):
    return ",".join(Anime(anime_name).genres)
