"""
Genera un CSV con el formato que esperan los importadores de listas de IMDb
(la columna clave es "Const", que debe contener el tt-ID). Este es el mismo
formato que el propio IMDb usa al exportar tus listas, así que es compatible
tanto con userscripts tipo "IMDb List Bulk Uploader" como con cualquier otra
herramienta que espere un export nativo de IMDb.

También se generan dos ficheros aparte:
  - *_unmatched.csv: items que no se pudieron resolver a un ID de IMDb, para
    revisarlos y añadirlos a mano.
  - *_ambiguous.csv: items resueltos con baja confianza, para verificar antes
    de subirlos.

Nota: si una ejecución anterior generó *_ambiguous.csv o *_unmatched.csv y la
ejecución actual no tiene nada que poner en alguno de los dos, ese fichero se
borra en vez de dejarlo con datos de una ejecución vieja (ver _write_or_clear).
"""

from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import MatchResult

# Mismas columnas que exporta el propio IMDb, para máxima compatibilidad.
IMDB_CSV_FIELDS = [
    "Position", "Const", "Created", "Modified", "Description", "Title",
    "Original Title", "URL", "Title Type", "IMDb Rating", "Runtime (mins)",
    "Year", "Genres", "Num Votes", "Release Date", "Directors",
    "Your Rating", "Date Rated",
]

TITLE_TYPE_LABEL = {"movie": "Película", "tv_series": "Serie de TV"}


def export_matches(matches: Iterable[MatchResult], output_path: str) -> dict:
    """
    Escribe output_path (matched), output_path con sufijo _unmatched y
    _ambiguous. Devuelve un pequeño resumen con los conteos.
    """
    matches = list(matches)
    matched = [m for m in matches if m.imdb_id and m.confidence == "exact"]
    ambiguous = [m for m in matches if m.imdb_id and m.confidence != "exact"]
    unmatched = [m for m in matches if not m.imdb_id]

    _write_csv(output_path, matched)

    base = Path(output_path)
    ambiguous_path = base.with_name(f"{base.stem}_ambiguous{base.suffix}")
    unmatched_path = base.with_name(f"{base.stem}_unmatched{base.suffix}")

    _write_or_clear(ambiguous_path, ambiguous, lambda path, rows: _write_csv(path, rows))
    _write_or_clear(unmatched_path, unmatched, lambda path, rows: _write_unmatched(path, rows))

    return {
        "matched": len(matched),
        "ambiguous": len(ambiguous),
        "unmatched": len(unmatched),
        "total": len(matches),
    }


def _write_or_clear(path: Path, rows: list, writer_fn) -> None:
    """
    Si hay filas, las escribe con writer_fn. Si no hay ninguna, borra el
    fichero (si existe de una ejecución anterior) para no dejar datos
    caducados de una pasada previa.
    """
    if rows:
        writer_fn(path, rows)
    elif path.exists():
        os.remove(path)


def _write_csv(path, matches: list[MatchResult]) -> None:
    today = date.today().isoformat()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=IMDB_CSV_FIELDS)
        writer.writeheader()
        for position, m in enumerate(matches, start=1):
            user_rating = m.item.user_rating
            writer.writerow({
                "Position": position,
                "Const": m.imdb_id,
                "Created": "",
                "Modified": "",
                "Description": "",
                "Title": m.imdb_title or m.item.title,
                "Original Title": m.imdb_original_title or "",
                "URL": f"https://www.imdb.com/title/{m.imdb_id}/",
                "Title Type": TITLE_TYPE_LABEL.get(m.item.media_type, "Película"),
                "IMDb Rating": "",
                "Runtime (mins)": "",
                "Year": m.imdb_year or m.item.year or "",
                "Genres": "",
                "Num Votes": "",
                "Release Date": "",
                "Directors": "",
                "Your Rating": user_rating if user_rating is not None else "",
                "Date Rated": today if user_rating is not None else "",
            })


def _write_unmatched(path, matches: list[MatchResult]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Year", "Media Type", "FilmAffinity URL", "List"])
        for m in matches:
            item = m.item
            writer.writerow([item.title, item.year or "", item.media_type, item.fa_url or "", item.list_name])
