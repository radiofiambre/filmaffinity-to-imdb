from pathlib import Path

from filmaffinity_to_imdb.scraper import FAScraper

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_page_extracts_title_year_type_and_rating():
    html = (FIXTURES / "fa_list_page.html").read_text(encoding="utf-8")
    scraper = FAScraper()

    items = list(scraper._parse_page(html, list_name="Test"))

    assert len(items) == 2

    movie = items[0]
    assert movie.title == "Canino"
    assert movie.year == 2009
    assert movie.media_type == "movie"
    assert movie.fa_id == "270437"
    assert movie.user_rating == 8

    series = items[1]
    assert series.title == "Dune: La profecía"
    assert series.year == 2024
    assert series.media_type == "tv_series"
    assert series.fa_id == "811200"
    assert series.user_rating is None
