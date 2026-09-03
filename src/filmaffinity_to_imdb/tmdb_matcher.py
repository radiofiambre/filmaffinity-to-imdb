"""
Resuelve cada FAItem a un ID de IMDb usando la API de TMDb (The Movie
Database). A diferencia de OMDb, la búsqueda de TMDb acepta un parámetro de
idioma y compara la consulta contra títulos TRADUCIDOS, no solo el original
— crucial para listas de FilmAffinity, que muestra los títulos en español
("Canino") mientras que IMDb/OMDb indexan por título original ("Dogtooth").

Necesitas una API key gratuita (v3 auth) en
https://www.themoviedb.org/settings/api.

El proceso son DOS llamadas por título:
  1. /search/movie o /search/tv (según el tipo) con el título en español.
  2. /movie/{id}/external_ids o /tv/{id}/external_ids, para sacar el tt-ID.
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from .models import FAItem, MatchResult

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_SEARCH_PATH = {"movie": "/search/movie", "tv_series": "/search/tv"}
TMDB_EXTERNAL_IDS_PATH = {"movie": "/movie/{id}/external_ids", "tv_series": "/tv/{id}/external_ids"}
TMDB_YEAR_PARAM = {"movie": "year", "tv_series": "first_air_date_year"}
TMDB_TITLE_FIELD = {"movie": "title", "tv_series": "name"}
TMDB_ORIGINAL_TITLE_FIELD = {"movie": "original_title", "tv_series": "original_name"}
TMDB_DATE_FIELD = {"movie": "release_date", "tv_series": "first_air_date"}


class TMDbMatcher:
    def __init__(self, api_key: str, language: str = "es-ES", rate_limit_seconds: float = 0.15, timeout: int = 10):
        if not api_key:
            raise ValueError(
                "Falta la API key de TMDb. Consíguela gratis (v3 auth) en "
                "https://www.themoviedb.org/settings/api y pásala con "
                "--tmdb-key o la variable de entorno TMDB_API_KEY."
            )
        self.api_key = api_key
        self.language = language
        self.rate_limit_seconds = rate_limit_seconds
        self.timeout = timeout
        self.session = requests.Session()

    def match(self, item: FAItem) -> MatchResult:
        media_type = item.media_type if item.media_type in TMDB_SEARCH_PATH else "movie"

        result = self._search(item.title, item.year, media_type)
        if result is None and item.year is not None:
            result = self._search(item.title, None, media_type)  # reintenta sin año

        if result is None:
            return MatchResult(item=item, imdb_id=None, confidence="none")

        imdb_id = self._get_external_id(result["id"], media_type)
        time.sleep(self.rate_limit_seconds)

        if not imdb_id:
            return MatchResult(item=item, imdb_id=None, confidence="none")

        result_year = self._extract_year(result.get(TMDB_DATE_FIELD[media_type]))

        return MatchResult(
            item=item,
            imdb_id=imdb_id,
            imdb_title=result.get(TMDB_TITLE_FIELD[media_type]),
            imdb_original_title=result.get(TMDB_ORIGINAL_TITLE_FIELD[media_type]),
            imdb_year=result_year,
            confidence="exact" if (item.year and result_year == item.year) else "fuzzy",
        )
    def _search(self, title: str, year: Optional[int], media_type: str) -> Optional[dict]:
        params = {"api_key": self.api_key, "query": title, "language": self.language}
        if year:
            params[TMDB_YEAR_PARAM[media_type]] = year

        resp = self.session.get(f"{TMDB_BASE}{TMDB_SEARCH_PATH[media_type]}", params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results") or []
        return results[0] if results else None

    def _get_external_id(self, tmdb_id: int, media_type: str) -> Optional[str]:
        path = TMDB_EXTERNAL_IDS_PATH[media_type].format(id=tmdb_id)
        resp = self.session.get(f"{TMDB_BASE}{path}", params={"api_key": self.api_key}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("imdb_id")

    @staticmethod
    def _extract_year(date_str: Optional[str]) -> Optional[int]:
        if not date_str or len(date_str) < 4:
            return None
        return int(date_str[:4])