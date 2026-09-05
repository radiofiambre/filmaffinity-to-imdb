"""
Genera un CSV con el mismo formato que exporta el propio IMDb (columna clave
"Const" = tt-ID), listo para importar desde
https://www.imdb.com/es-es/labs/import-watch-history/

Los ficheros de salida se nombran a partir del nombre de la lista (ver
naming.slugify), para que migrar varias listas no sobreescriba los CSV de
unas con los de otras. Para la lista "Películas que quiero ver" se generan:

  peliculas_que_quiero_ver.csv             -> resueltos con confianza alta
  peliculas_que_quiero_ver_ambiguous.csv   -> resueltos pero a revisar (el
                                               año no coincidía exactamente)
  peliculas_que_quiero_ver_unmatched.csv   -> no se encontraron en TMDb

Si una ejecución no tiene nada que poner en _ambiguous o _unmatched, el
fichero correspondiente de una ejecución anterior se borra en vez de
dejarse con datos caducados.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import MatchResult
from .naming import slugify

# Mismas columnas que exporta el propio IMDb, para máxima compatibilidad.
IMDB_CSV_FIELDS = [
    "Position", "Const", "Created", "Modified", "Description", "Title",
    "Original Title", "URL", "Title Type", "IMDb Rating", "Runtime (mins)",
    "Year", "Genres", "Num Votes", "Release Date", "Directors",
    "Your Rating", "Date Rated",
]

TITLE_TYPE_LABEL = {"movie": "Película", "tv_series": "Serie de TV"}


def export_matches(matches: Iterable[MatchResult], list_name: str, output_dir: str = ".") -> dict:
    """
    Escribe los CSV de salida (nombrados según list_name) y devuelve un
    resumen con los conteos y las rutas generadas.
    """
    matches = list(matches)
    matched = [m for m in matches if m.imdb_id and m.confidence == "exact"]
    ambiguous = [m for m in matches if m.imdb_id and m.confidence != "exact"]
    unmatched = [m for m in matches if not m.imdb_id]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(list_name)

    matched_path = out_dir / f"{slug}.csv"
    ambiguous_path = out_dir / f"{slug}_ambiguous.csv"
    unmatched_path = out_dir / f"{slug}_unmatched.csv"

    _write_csv(matched_path, matched)
    _write_or_clear(ambiguous_path, ambiguous, _write_csv)
    _write_or_clear(unmatched_path, unmatched, _write_unmatched)

    return {
        "matched": len(matched),
        "ambiguous": len(ambiguous),
        "unmatched": len(unmatched),
        "total": len(matches),
        "matched_path": str(matched_path),
        "ambiguous_path": str(ambiguous_path) if ambiguous else None,
        "unmatched_path": str(unmatched_path) if unmatched else None,
    }


def _write_or_clear(path: Path, rows: list, writer_fn) -> None:
    """Si hay filas las escribe; si no, borra el fichero de una ejecución
    anterior (si existe) para no dejar datos caducados."""
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
        writer.writerow(["Title", "Year", "Media Type", "Your Rating", "FilmAffinity URL"])
        for m in matches:
            item = m.item
            writer.writerow([
                item.title, item.year or "", item.media_type,
                item.user_rating if item.user_rating is not None else "",
                item.fa_url or "",
            ])
