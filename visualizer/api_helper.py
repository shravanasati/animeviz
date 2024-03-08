import os
from pathlib import Path
import sys
from urllib.parse import urlencode

from dotenv import load_dotenv
import requests
from pandas import DataFrame

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import db_session
from models import Anime, AnimeGenre, Genre


KNOWN_GENRES = set(
    (
        "Action",
        "Adventure",
        "Comedy",
        "Drama",
        "Fantasy",
        "Gourmet",
        "Horror",
        "Isekai",
        "Mystery",
        "Romance",
        "Sci-Fi",
        "Slice of Life",
        "Sports",
        "Suspense",
    )
)

load_dotenv("../credentials.env")


def _anime_genres_mal(anime_name: str) -> tuple[Anime | None, list[Genre]]:
    """
    Sends a request to the MAL API to fetch the genres of the given anime.
    """
    try:
        anime_endpoint = "https://api.myanimelist.net/v2/anime?"
        query = urlencode({"q": anime_name[:64], "limit": 1, "fields": "genres"})
        api_url = anime_endpoint + query
        resp = requests.get(
            api_url,
            headers={"X-MAL-CLIENT-ID": os.environ["MAL_CLIENT_ID"]},
            timeout=10,
        )
        resp.raise_for_status()
        anime_data = resp.json()["data"][0]["node"]

        return Anime(anime_data["id"], anime_data["title"]), [
            Genre(**g) for g in anime_data["genres"] if g["name"] in KNOWN_GENRES
        ]

    except requests.HTTPError:
        print(
            f"non 200 status code returned from MAL API, {api_url=}, {resp.status_code=}"
        )
        return None, []

    except IndexError:
        print("unexpected response from MAL")
        print(resp.json())
        return None, []

    except Exception as e:
        print("cant send request to mal api")
        print(e)
        return None, []


def add_anime_genres_to_db(new_anime: Anime, genres: list[Genre]):
    db_session.add(new_anime)
    for genre in genres:
        if db_session.query(Genre).filter_by(id=genre.id).first():
            continue
        db_session.add(genre)

    db_session.commit()

    anime_genres_objs = [AnimeGenre(new_anime.id, genre.id) for genre in genres]
    db_session.add_all(anime_genres_objs)

    db_session.commit()


def get_anime_genres(anime_name: str):
    """
    Returns the genres of anime if present in the database, otherwise sends request to MAL API.
    """
    try:
        anime = Anime.query.filter_by(name=anime_name).first()
        print("anime object found in database:", anime)
        if not anime:
            anime_obj, genres = _anime_genres_mal(anime_name)
            if not anime_obj or not genres:
                return []
            add_anime_genres_to_db(anime_obj, genres)
            genres = [g.name for g in genres]
        else:
            genres = [g.name for g in anime.genres]

        return genres

    except Exception as e:
        print("error occured while fetching genres for {}: {}".format(anime_name, e))
        return []


def build_df_from_mal_api_data(data: list):
    df_compatible_data = []
    for item in data:
        node = item["node"]
        if not node:
            continue

        user_status = node["my_list_status"]

        df_compatible_data.append(
            {
                "series_animedb_id": node["id"],
                "series_title": node["title"],
                "series_episodes": node["num_episodes"],
                "series_type": node["media_type"],
                "my_watched_episodes": user_status["num_episodes_watched"],
                "my_status": user_status["status"],
                "my_start_date": user_status.get("start_date") or "0000-00-00",
                "my_finish_date": user_status.get("finish_date") or "0000-00-00",
                "my_score": user_status["score"],
            }
        )

    return DataFrame(df_compatible_data)
