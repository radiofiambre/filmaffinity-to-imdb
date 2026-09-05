"""CLI de filmaffinity-to-imdb. Ejemplos:

  filmaffinity-to-imdb scrape "https://www.filmaffinity.com/es/userlist.php?user_id=X&list_id=XXXX" \\
      --list-name "Películas que he visto"

  filmaffinity-to-imdb match peliculas_que_he_visto_fa.csv --tmdb-key TU_KEY

  filmaffinity-to-imdb run "https://www.filmaffinity.com/es/userlist.php?user_id=X&list_id=XXXX" \\
      --list-name "Películas que he visto" --tmdb-key TU_KEY
"""

from __future__ import annotations

import csv
import os

import click
from dotenv import load_dotenv

from .exporter import export_matches
from .models import FAItem
from .naming import slugify
from .scraper import FAScraper
from .tmdb_matcher import TMDbMatcher

load_dotenv()

TMDB_KEY_OPTION = click.option(
    "--tmdb-key",
    default=lambda: os.environ.get("TMDB_API_KEY", ""),
    help="API key de TMDb (o usa TMDB_API_KEY en .env).",
)


@click.group()
def cli():
    """filmaffinity-to-imdb: migra listas de FilmAffinity a IMDb."""


@cli.command()
@click.argument("list_url")
@click.option("--list-name", required=True, help="Nombre de la lista (se usa para nombrar los ficheros de salida).")
@click.option("--output-dir", default=".", help="Carpeta donde guardar el CSV intermedio.")
def scrape(list_url: str, list_name: str, output_dir: str):
    """Extrae los items de una lista de FilmAffinity a un CSV intermedio."""
    scraper = FAScraper()
    items = list(scraper.scrape_list(list_url, list_name=list_name))

    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, f"{slugify(list_name)}_fa.csv")

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "year", "media_type", "fa_id", "fa_url", "list_name", "user_rating"])
        for item in items:
            writer.writerow([
                item.title, item.year or "", item.media_type, item.fa_id or "",
                item.fa_url or "", item.list_name,
                item.user_rating if item.user_rating is not None else "",
            ])

    click.echo(f"{len(items)} items guardados en {output}")


@cli.command()
@click.argument("input_csv")
@click.option("--list-name", default=None, help="Nombre de la lista para nombrar los ficheros de salida (si no se indica, se toma del propio CSV intermedio).")
@click.option("--output-dir", default=".", help="Carpeta donde guardar los CSV de salida.")
@TMDB_KEY_OPTION
def match(input_csv: str, list_name: str, output_dir: str, tmdb_key: str):
    """Resuelve los títulos de un CSV intermedio a IDs de IMDb."""
    items = _read_intermediate_csv(input_csv)
    resolved_name = list_name or (items[0].list_name if items else "") or "lista_filmaffinity"

    matcher = TMDbMatcher(api_key=tmdb_key)
    matches = []
    with click.progressbar(items, label="Buscando en TMDb") as bar:
        for item in bar:
            matches.append(matcher.match(item))

    summary = export_matches(matches, resolved_name, output_dir=output_dir)
    _print_summary(summary)


@cli.command()
@click.argument("list_url")
@click.option("--list-name", required=True, help="Nombre de la lista (se usa para nombrar los ficheros de salida).")
@click.option("--output-dir", default=".", help="Carpeta donde guardar los CSV de salida.")
@TMDB_KEY_OPTION
def run(list_url: str, list_name: str, output_dir: str, tmdb_key: str):
    """Pipeline completo: scrape + match en un solo paso."""
    scraper = FAScraper()
    items = list(scraper.scrape_list(list_url, list_name=list_name))
    click.echo(f"{len(items)} items extraídos de FilmAffinity.")

    matcher = TMDbMatcher(api_key=tmdb_key)
    matches = []
    with click.progressbar(items, label="Buscando en TMDb") as bar:
        for item in bar:
            matches.append(matcher.match(item))

    summary = export_matches(matches, list_name, output_dir=output_dir)
    _print_summary(summary)


def _print_summary(summary: dict) -> None:
    click.echo(
        f"Resueltos: {summary['matched']} | "
        f"Ambiguos: {summary['ambiguous']} | "
        f"Sin encontrar: {summary['unmatched']} | "
        f"Total: {summary['total']}"
    )
    click.echo(f"CSV listo para importar en IMDb: {summary['matched_path']}")
    if summary["ambiguous_path"]:
        click.echo(f"Revisar antes de importar: {summary['ambiguous_path']}")
    if summary["unmatched_path"]:
        click.echo(f"No encontrados (añadir a mano): {summary['unmatched_path']}")


def _read_intermediate_csv(path: str) -> list[FAItem]:
    items = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(FAItem(
                title=row["title"],
                year=int(row["year"]) if row.get("year") else None,
                media_type=row.get("media_type", "movie"),
                fa_id=row.get("fa_id") or None,
                fa_url=row.get("fa_url") or None,
                list_name=row.get("list_name", ""),
                user_rating=int(row["user_rating"]) if row.get("user_rating") else None,
            ))
    return items


if __name__ == "__main__":
    cli()
