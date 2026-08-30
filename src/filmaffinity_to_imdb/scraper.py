"""
Scraper de listas de FilmAffinity.

FilmAffinity no tiene API pública, así que esto funciona parseando el HTML
público de una lista. Los selectores CSS están centralizados en `SELECTORS`
para que sea fácil ajustarlos si FilmAffinity cambia su maquetación (algo que
ya le ha pasado a varios scrapers de la comunidad, ver README).

URL correcta a usar: la vista PÚBLICA de una lista es https://www.filmaffinity.com/es/userlist.php?user_id=<TU_USER_ID>&list_id=<LIST_ID>
(NO mylist.php, que es la vista privada de gestión y exige login). Puedes
forzar el formato "listado con pósters" añadiendo &chv=list. La paginación
se controla con &page=N.

IMPORTANTE: los selectores CSS de abajo siguen siendo un punto de partida:
se han inferido de una extracción en texto/markdown de la página real, no
del HTML crudo con sus clases (mi entorno no puede inspeccionar el DOM
directamente). Antes de fiarte del scraper, ejecuta
`filmaffinity-to-imdb scrape` sobre tu lista y revisa si los items salen
bien. Si no, comparte un fragmento de HTML real (clic derecho sobre una
tarjeta de película → Inspeccionar → Copy → Copy outerHTML) para ajustar
los selectores con precisión.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterator, Optional

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

# Selectores centralizados: si FilmAffinity cambia el HTML, solo hay que
# tocar aquí.
SELECTORS = {
    "item_card": "li.list-row[data-movie-id]",
    "title": ".mc-title a",
    "year": ".mc-year",
    "poster_img": ".mc-poster img",
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
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def scrape_list(self, list_url: str, list_name: str = "") -> Iterator[FAItem]:
        """
        Recorre una lista de FilmAffinity (con paginación) y va cediendo
        FAItem por cada película/serie encontrada.

        list_url: URL completa de la primera página de la lista, p.ej.
            https://www.filmaffinity.com/es/mylist.php?list_id=XXXX
        """
        page = 1
        seen_any = False

        while page <= self.config.max_pages:
            url = self._paginate(list_url, page)
            html = self._fetch(url)
            items = list(self._parse_page(html, list_name=list_name))

            if not items:
                break

            seen_any = True
            yield from items
            page += 1
            time.sleep(self.config.rate_limit_seconds)

        if not seen_any:
            raise ValueError(
                f"No se encontró ningún item en {list_url}. "
                "Puede que la lista sea privada, que la URL sea incorrecta, "
                "o que los selectores en SELECTORS ya no coincidan con el "
                "HTML actual de FilmAffinity (ver docstring del módulo)."
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
        return f"{list_url}{sep}p={page}"

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

            yield FAItem(
                title=title,
                year=year,
                media_type=media_type,
                fa_id=fa_id,
                fa_url=fa_url,
                list_name=list_name,
            )

    @staticmethod
    def _guess_media_type(card) -> str:
        # El alt de la imagen del póster trae el sufijo "(Serie de TV)"
        # cuando es una serie; en películas no lleva ningún sufijo. Es más
        # fiable que buscar la palabra "serie" en el texto de la tarjeta,
        # que podría aparecer por casualidad en el reparto o el género.
        poster_img = card.select_one(SELECTORS["poster_img"])
        alt_text = poster_img.get("alt", "") if poster_img else ""
        if "serie de tv" in alt_text.lower():
            return "tv_series"
        return "movie"
