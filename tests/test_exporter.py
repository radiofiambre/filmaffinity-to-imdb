import csv

from filmaffinity_to_imdb.exporter import export_matches
from filmaffinity_to_imdb.models import FAItem, MatchResult


def _match(title, year, imdb_id, confidence, user_rating=None, media_type="movie"):
    item = FAItem(title=title, year=year, media_type=media_type, user_rating=user_rating)
    return MatchResult(item=item, imdb_id=imdb_id, imdb_title=title, imdb_year=year, confidence=confidence)


def test_filenames_are_derived_from_list_name(tmp_path):
    matches = [_match("Canino", 2009, "tt1291584", "exact", user_rating=8)]

    summary = export_matches(matches, "Películas que quiero ver", output_dir=str(tmp_path))

    assert (tmp_path / "peliculas_que_quiero_ver.csv").exists()
    assert summary["matched_path"].endswith("peliculas_que_quiero_ver.csv")


def test_your_rating_is_written_for_rated_items(tmp_path):
    matches = [_match("Canino", 2009, "tt1291584", "exact", user_rating=8)]

    export_matches(matches, "Lista", output_dir=str(tmp_path))

    with open(tmp_path / "lista.csv", newline="", encoding="utf-8") as f:
        row = next(csv.DictReader(f))

    assert row["Your Rating"] == "8"
    assert row["Date Rated"] != ""


def test_stale_unmatched_file_is_removed_when_no_longer_needed(tmp_path):
    stale_path = tmp_path / "lista_unmatched.csv"
    stale_path.write_text("Title,Year\nvieja,2000\n", encoding="utf-8")

    matches = [_match("Canino", 2009, "tt1291584", "exact")]  # sin nada sin encontrar esta vez
    export_matches(matches, "Lista", output_dir=str(tmp_path))

    assert not stale_path.exists()


def test_ambiguous_items_are_separated_from_matched(tmp_path):
    matches = [
        _match("Canino", 2009, "tt1291584", "exact"),
        _match("Begotten", 1991, "tt0097366", "fuzzy"),
    ]

    summary = export_matches(matches, "Lista", output_dir=str(tmp_path))

    assert summary["matched"] == 1
    assert summary["ambiguous"] == 1
    assert (tmp_path / "lista_ambiguous.csv").exists()
