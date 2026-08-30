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
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import MatchResult

IMDB_CSV_FIELDS = [
    "Position",
    "Const",
    "Created",
    "Title",
    "Title Type",
    "Year",
]


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
    if ambiguous:
        _write_csv(base.with_name(f"{base.stem}_ambiguous{base.suffix}"), ambiguous)
    if unmatched:
        _write_unmatched(base.with_name(f"{base.stem}_unmatched{base.suffix}"), unmatched)

    return {
        "matched": len(matched),
        "ambiguous": len(ambiguous),
        "unmatched": len(unmatched),
        "total": len(matches),
    }


def _write_csv(path, matches: list[MatchResult]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=IMDB_CSV_FIELDS)
        writer.writeheader()
        for position, m in enumerate(matches, start=1):
            writer.writerow({
                "Position": position,
                "Const": m.imdb_id,
                "Created": "",
                "Title": m.imdb_title or m.item.title,
                "Title Type": "tvSeries" if m.item.media_type == "tv_series" else "movie",
                "Year": m.imdb_year or m.item.year or "",
            })


def _write_unmatched(path, matches: list[MatchResult]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Year", "Media Type", "FilmAffinity URL", "List"])
        for m in matches:
            item = m.item
            writer.writerow([item.title, item.year or "", item.media_type, item.fa_url or "", item.list_name])
