from functools import lru_cache
from animec import Anime

# todo ditch animec, use mal api

# todo instead of caching make an anime database
# todo request data from api only when unknown anime in database


@lru_cache(maxsize=256)
def get_anime_genres(anime_name: str):
    try:
        genres = ",".join(Anime(anime_name).genres)
        return genres
    except Exception as e:
        print("error occured while fetching genres for {}: {}".format(anime_name, e))
        return ""
