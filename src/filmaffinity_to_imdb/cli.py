"""CLI de filmaffinity-to-imdb. Ejemplos:

  filmaffinity-to-imdb scrape "https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXX" \\
      --list-name "Pendientes" -o pendientes_fa.csv

  filmaffinity-to-imdb match pendientes_fa.csv -o pendientes_imdb.csv --omdb-key TU_KEY

  filmaffinity-to-imdb run "https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXX" \\
      --list-name "Pendientes" --omdb-key TU_KEY -o pendientes_imdb.csv
"""

from __future__ import annotations

import csv
import os

import click
from dotenv import load_dotenv

from .exporter import export_matches
from .tmdb_matcher import TMDbMatcher
from .models import FAItem
from .scraper import FAScraper

load_dotenv()


@click.group()
def cli():
    """filmaffinity-to-imdb: migra listas de FilmAffinity a IMDb."""


@cli.command()
@click.argument("list_url")
@click.option("--list-name", default="", help="Nombre descriptivo de la lista (se guarda en el CSV).")
@click.option("-o", "--output", default="fa_list.csv", help="CSV de salida con los items scrapeados.")
def scrape(list_url: str, list_name: str, output: str):
    """Extrae los items de una lista de FilmAffinity a un CSV intermedio."""
    scraper = FAScraper()
    items = list(scraper.scrape_list(list_url, list_name=list_name))

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "year", "media_type", "fa_id", "fa_url", "list_name"])
        for item in items:
            writer.writerow([item.title, item.year or "", item.media_type, item.fa_id or "", item.fa_url or "", item.list_name])

    click.echo(f"{len(items)} items guardados en {output}")


@cli.command()
@click.argument("input_csv")
@click.option("-o", "--output", default="imdb_import.csv", help="CSV compatible con importadores de IMDb.")
@click.option("--tmdb-key", default=lambda: os.environ.get("TMDB_API_KEY", ""), help="API key de TMDb (o usa TMDB_API_KEY en .env).")
def match(input_csv: str, output: str, tmdb_key: str):
    """Resuelve los títulos de un CSV intermedio a IDs de IMDb."""
    items = _read_intermediate_csv(input_csv)
    matcher = TMDbMatcher(api_key=tmdb_key)

    matches = []
    with click.progressbar(items, label="Buscando en OMDb") as bar:
        for item in bar:
            matches.append(matcher.match(item))

    summary = export_matches(matches, output)
    click.echo(
        f"Resueltos: {summary['matched']} | "
        f"Ambiguos: {summary['ambiguous']} | "
        f"Sin encontrar: {summary['unmatched']} | "
        f"Total: {summary['total']}"
    )
    click.echo(f"CSV listo para importar en IMDb: {output}")


@cli.command()
@click.argument("list_url")
@click.option("--list-name", default="")
@click.option("-o", "--output", default="imdb_import.csv")
@click.option("--tmdb-key", default=lambda: os.environ.get("TMDB_API_KEY", ""))
def run(list_url: str, list_name: str, output: str, tmdb_key: str):
    """Pipeline completo: scrape + match en un solo paso."""
    scraper = FAScraper()
    items = list(scraper.scrape_list(list_url, list_name=list_name))
    click.echo(f"{len(items)} items extraídos de FilmAffinity.")

    matcher = TMDbMatcher(api_key=tmdb_key)
    matches = []
    with click.progressbar(items, label="Buscando en OMDb") as bar:
        for item in bar:
            matches.append(matcher.match(item))

    summary = export_matches(matches, output)
    click.echo(
        f"Resueltos: {summary['matched']} | "
        f"Ambiguos: {summary['ambiguous']} | "
        f"Sin encontrar: {summary['unmatched']} | "
        f"Total: {summary['total']}"
    )
    click.echo(f"CSV listo para importar en IMDb: {output}")


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
            ))
    return items


if __name__ == "__main__":
    cli()
