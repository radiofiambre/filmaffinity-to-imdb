"""
Resuelve cada FAItem (título + año + tipo) a un ID de IMDb (tt...) usando la
API gratuita de OMDb (http://www.omdbapi.com/). Necesitas una API key gratuita
en https://www.omdbapi.com/apikey.aspx (el tier gratuito permite 1000
peticiones/día, suficiente para migrar listas personales).

Por qué OMDb y no cinemagoer/IMDbPY: OMDb permite buscar directamente por
título+año+tipo y te devuelve el imdbID en una sola llamada HTTP sencilla,
sin necesidad de scrapear IMDb. Es la opción con menos fricción para
un proyecto que ya depende de un scraper (el de FilmAffinity).
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from .models import FAItem, MatchResult

OMDB_URL = "http://www.omdbapi.com/"
OMDB_TYPE = {"movie": "movie", "tv_series": "series"}


class OMDbMatcher:
    def __init__(self, api_key: str, rate_limit_seconds: float = 0.2, timeout: int = 10):
        if not api_key:
            raise ValueError(
                "Falta la API key de OMDb. Consíguela gratis en "
                "https://www.omdbapi.com/apikey.aspx y pásala con "
                "--omdb-key o la variable de entorno OMDB_API_KEY."
            )
        self.api_key = api_key
        self.rate_limit_seconds = rate_limit_seconds
        self.timeout = timeout
        self.session = requests.Session()

    def match(self, item: FAItem) -> MatchResult:
        omdb_type = OMDB_TYPE.get(item.media_type)

        result = self._search(item.title, item.year, omdb_type)
        if result is None and item.year is not None:
            # Reintenta sin año: a veces FilmAffinity y OMDb difieren en un
            # año (fecha de estreno vs. fecha de producción).
            result = self._search(item.title, None, omdb_type)

        time.sleep(self.rate_limit_seconds)

        if result is None:
            return MatchResult(item=item, imdb_id=None, confidence="none")

        return MatchResult(
            item=item,
            imdb_id=result.get("imdbID"),
            imdb_title=result.get("Title"),
            imdb_year=self._safe_int(result.get("Year")),
            confidence="exact" if item.year else "fuzzy",
        )

    def _search(self, title: str, year: Optional[int], omdb_type: Optional[str]) -> Optional[dict]:
        params = {"apikey": self.api_key, "t": title}
        if year:
            params["y"] = str(year)
        if omdb_type:
            params["type"] = omdb_type

        resp = self.session.get(OMDB_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        if data.get("Response") == "True":
            return data
        return None

    @staticmethod
    def _safe_int(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits[:4]) if digits else None
