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

# Selectores centralizados: si FilmAffinity cambia el HTML, solo hay que
# tocar aquí.
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
        # cloudscraper en vez de requests.Session(): resuelve automáticamente
        # los challenges de Cloudflare (ver cf-mitigated: challenge en la
        # respuesta 403). Si en el futuro Cloudflare endurece el challenge,
        # esto podría dejar de bastar y tocaría pasar a Playwright.
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.session.headers.update(DEFAULT_HEADERS)

    def scrape_list(self, list_url: str, list_name: str = "") -> Iterator[FAItem]:
        """
        Recorre una lista de FilmAffinity (con paginación) y va cediendo
        FAItem por cada película/serie encontrada.

        list_url: URL completa de la primera página de la lista, p.ej.
            https://www.filmaffinity.com/es/userlist.php?user_id=X&list_id=XXXX

        Nota: al pedir una página más allá de la última real, FilmAffinity
        no devuelve una página vacía, sino que repite el contenido de la
        última página válida. Por eso llevamos la cuenta de los fa_id ya
        vistos: si una página no aporta ningún item nuevo, asumimos que
        hemos llegado al final y paramos ahí, en vez de fiarnos solo de
        max_pages.
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
        # cuando es una serie; en películas no lleva ningún sufijo. Es más
        # fiable que buscar la palabra "serie" en el texto de la tarjeta,
        # que podría aparecer por casualidad en el reparto o el género.
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