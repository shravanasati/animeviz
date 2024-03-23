from flask_login import UserMixin
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True)
    login_provider = Column(String(50))
    oauth2_token = Column(String(781))
    refresh_token = Column(String(1000))

    def __init__(self, name: str, login_provider: str, oauth2_token: str, refresh_token: str):
        self.name = name
        self.login_provider = login_provider
        self.oauth2_token = oauth2_token
        self.refresh_token = refresh_token

    def __repr__(self):
        return f"<User {self.name!r}>"


class Genre(Base):
    __tablename__ = "genres"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    # animes = relationship("Anime", secondary="anime_genres")

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def __str__(self):
        return f"<Genre id:{self.id} name:{self.name}>"


class Anime(Base):
    __tablename__ = "anime"
    id = Column(Integer, primary_key=True)
    name = Column(String(250), unique=True)
    genres = relationship("Genre", secondary="anime_genres")

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def __str__(self):
        return f"<Anime id:{self.id} name:{self.name} genres:{self.genres}>"


class AnimeGenre(Base):
    __tablename__ = "anime_genres"

    anime_id = Column(Integer, ForeignKey("anime.id"), primary_key=True)
    genre_id = Column(Integer, ForeignKey("genres.id"), primary_key=True)

    def __init__(self, anime_id, genre_id):
        self.anime_id = anime_id
        self.genre_id = genre_id
