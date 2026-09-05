import responses

from filmaffinity_to_imdb.tmdb_matcher import TMDB_BASE, TMDbMatcher
from filmaffinity_to_imdb.models import FAItem


@responses.activate
def test_match_exact_hit_when_years_match():
    responses.add(
        responses.GET,
        f"{TMDB_BASE}/search/movie",
        json={"results": [{
            "id": 42, "title": "Canino", "original_title": "Kynodontas",
            "release_date": "2009-05-15",
        }]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{TMDB_BASE}/movie/42/external_ids",
        json={"imdb_id": "tt1291584"},
        status=200,
    )

    matcher = TMDbMatcher(api_key="fake-key", rate_limit_seconds=0)
    item = FAItem(title="Canino", year=2009, media_type="movie")

    result = matcher.match(item)

    assert result.imdb_id == "tt1291584"
    assert result.confidence == "exact"
    assert result.imdb_original_title == "Kynodontas"


@responses.activate
def test_match_marks_ambiguous_when_year_differs():
    responses.add(
        responses.GET,
        f"{TMDB_BASE}/search/movie",
        json={"results": [{
            "id": 7, "title": "Begotten", "original_title": "Begotten",
            "release_date": "1989-01-01",
        }]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{TMDB_BASE}/movie/7/external_ids",
        json={"imdb_id": "tt0097366"},
        status=200,
    )

    matcher = TMDbMatcher(api_key="fake-key", rate_limit_seconds=0)
    item = FAItem(title="Begotten", year=1991, media_type="movie")  # FA dice 1991, TMDb dice 1989

    result = matcher.match(item)

    assert result.imdb_id == "tt0097366"
    assert result.confidence == "fuzzy"


@responses.activate
def test_match_returns_none_when_never_found():
    responses.add(responses.GET, f"{TMDB_BASE}/search/movie", json={"results": []}, status=200)

    matcher = TMDbMatcher(api_key="fake-key", rate_limit_seconds=0)
    item = FAItem(title="Película inexistente", year=None, media_type="movie")

    result = matcher.match(item)

    assert result.imdb_id is None
    assert result.confidence == "none"


@responses.activate
def test_match_uses_tv_endpoints_for_series():
    responses.add(
        responses.GET,
        f"{TMDB_BASE}/search/tv",
        json={"results": [{
            "id": 99, "name": "Dune: La profecía", "original_name": "Dune: Prophecy",
            "first_air_date": "2024-11-17",
        }]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{TMDB_BASE}/tv/99/external_ids",
        json={"imdb_id": "tt15271862"},
        status=200,
    )

    matcher = TMDbMatcher(api_key="fake-key", rate_limit_seconds=0)
    item = FAItem(title="Dune: La profecía", year=2024, media_type="tv_series")

    result = matcher.match(item)

    assert result.imdb_id == "tt15271862"
    assert result.confidence == "exact"
