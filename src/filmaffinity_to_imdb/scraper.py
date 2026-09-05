"""
Scraper de listas de FilmAffinity.

FilmAffinity no tiene API pública, así que esto funciona parseando el HTML
público de una lista.

URL a usar: la vista PÚBLICA de una lista es
    https://www.filmaffinity.com/es/userlist.php?user_id=<TU_USER_ID>&list_id=<LIST_ID>
(NO mylist.php, que es la vista privada de gestión y exige login). Ese enlace
lo genera FilmAffinity con la opción "compartir lista" — debes marcar la
lista como pública para que esta URL funcione sin sesión iniciada.

FilmAffinity está detrás de Cloudflare, así que usamos `cloudscraper` en vez
de `requests` normal para poder pasar el challenge anti-bot.

Notas sobre paginación: al pedir una página más allá de la última real,
FilmAffinity puede devolver un 404 o repetir el contenido de la última
página válida, según el caso — este scraper contempla ambos.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterator, Optional

import cloudscraper
import requests
from bs4 import BeautifulSoup

from .models import FAItem

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}

SELECTORS = {
    "item_card": "li[data-movie-id]",
    "title": ".mc-title a",
    "year": ".mc-year",
    "poster_img": ".mc-poster img",
    "user_rating": ".fa-user-rat-box",
}

RATE_LIMIT_SECONDS = 3  # espera entre peticiones para no saturar el servidor


@dataclass
class FAScraperConfig:
    rate_limit_seconds: float = RATE_LIMIT_SECONDS
    max_pages: int = 50
    timeout: int = 15


class FAScraper:
    def __init__(self, config: Optional[FAScraperConfig] = None):
        self.config = config or FAScraperConfig()
        # cloudscraper en vez de requests.Session(): FilmAffinity está detrás
        # de Cloudflare y bloquea peticiones simples con 403.
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.session.headers.update(DEFAULT_HEADERS)

    def scrape_list(self, list_url: str, list_name: str = "") -> Iterator[FAItem]:
        """
        Recorre una lista de FilmAffinity (con paginación) y va cediendo
        FAItem por cada película/serie encontrada.
        """
        page = 1
        seen_any = False
        seen_ids: set[str] = set()

        while page <= self.config.max_pages:
            url = self._paginate(list_url, page)
            try:
                html = self._fetch(url)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    break  # nos pasamos del final real de la lista
                raise

            items = list(self._parse_page(html, list_name=list_name))
            if not items:
                break

            new_items = [item for item in items if item.fa_id not in seen_ids]
            if not new_items:
                break  # página repetida: hemos llegado al final real de la lista

            seen_any = True
            seen_ids.update(item.fa_id for item in new_items)
            yield from new_items

            page += 1
            time.sleep(self.config.rate_limit_seconds)

        if not seen_any:
            raise ValueError(
                f"No se encontró ningún item en {list_url}. Puede que la "
                "lista sea privada (revisa que esté marcada como pública en "
                "FilmAffinity), que la URL sea incorrecta, o que FilmAffinity "
                "haya cambiado su maquetación."
            )

    def _fetch(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.config.timeout)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _paginate(list_url: str, page: int) -> str:
        if page == 1:
            return list_url
        sep = "&" if "?" in list_url else "?"
        return f"{list_url}{sep}page={page}"

    def _parse_page(self, html: str, list_name: str) -> Iterator[FAItem]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(SELECTORS["item_card"])

        for card in cards:
            fa_id = card.get("data-movie-id")

            title_el = card.select_one(SELECTORS["title"])
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            fa_url = title_el.get("href")

            year_el = card.select_one(SELECTORS["year"])
            year = None
            if year_el:
                year_match = re.search(r"\d{4}", year_el.get_text())
                if year_match:
                    year = int(year_match.group())

            media_type = self._guess_media_type(card)
            user_rating = self._parse_user_rating(card)

            yield FAItem(
                title=title,
                year=year,
                media_type=media_type,
                fa_id=fa_id,
                fa_url=fa_url,
                list_name=list_name,
                user_rating=user_rating,
            )

    @staticmethod
    def _guess_media_type(card) -> str:
        # El alt de la imagen del póster trae el sufijo "(Serie de TV)"
        # cuando es una serie; en películas no lleva ningún sufijo.
        poster_img = card.select_one(SELECTORS["poster_img"])
        alt_text = poster_img.get("alt", "") if poster_img else ""
        if "serie de tv" in alt_text.lower():
            return "tv_series"
        return "movie"

    @staticmethod
    def _parse_user_rating(card) -> Optional[int]:
        # "-" significa que no has puntuado el título; si hay nota, viene
        # como texto plano dentro del mismo div (p.ej. "8").
        rating_el = card.select_one(SELECTORS["user_rating"])
        if not rating_el:
            return None
        text = rating_el.get_text(strip=True)
        if not text or text == "-":
            return None
        try:
            return int(text)
        except ValueError:
            return None
