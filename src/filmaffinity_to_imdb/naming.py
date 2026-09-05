"""Genera nombres de fichero seguros a partir del nombre de una lista, para
que migrar varias listas no sobreescriba los CSV de una con los de otra
(p.ej. "Películas que quiero ver" -> "peliculas_que_quiero_ver")."""

import re
import unicodedata


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "lista_filmaffinity"
