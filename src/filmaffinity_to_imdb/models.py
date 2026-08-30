"""Modelos de datos compartidos por todo el pipeline."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FAItem:
    """Un elemento (película o serie) extraído de una lista de FilmAffinity."""

    title: str
    year: Optional[int]
    media_type: str  # "movie" | "tv_series"
    fa_id: Optional[str] = None       # ID interno de FilmAffinity, si se pudo extraer
    fa_url: Optional[str] = None
    list_name: str = ""

    # Se rellena en la fase de matching
    imdb_id: Optional[str] = None     # p.ej. "tt0111161"
    match_confidence: Optional[str] = None  # "exact" | "fuzzy" | "manual" | None


@dataclass
class MatchResult:
    """Resultado de intentar casar un FAItem con un título de IMDb."""

    item: FAItem
    imdb_id: Optional[str]
    imdb_title: Optional[str] = None
    imdb_year: Optional[int] = None
    confidence: str = "none"  # "exact" | "fuzzy" | "none"
    candidates: list = field(default_factory=list)  # otros posibles matches, si hay ambigüedad
