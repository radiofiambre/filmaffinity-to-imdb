import responses

from filmaffinity_to_imdb.matcher import OMDB_URL, OMDbMatcher
from filmaffinity_to_imdb.models import FAItem


@responses.activate
def test_match_exact_hit():
    responses.add(
        responses.GET,
        OMDB_URL,
        json={"Response": "True", "imdbID": "tt0111161", "Title": "The Shawshank Redemption", "Year": "1994"},
        status=200,
    )

    matcher = OMDbMatcher(api_key="fake-key", rate_limit_seconds=0)
    item = FAItem(title="Cadena perpetua", year=1994, media_type="movie")

    result = matcher.match(item)

    assert result.imdb_id == "tt0111161"
    assert result.confidence == "exact"


@responses.activate
def test_match_retries_without_year_when_not_found():
    responses.add(responses.GET, OMDB_URL, json={"Response": "False"}, status=200)
    responses.add(
        responses.GET,
        OMDB_URL,
        json={"Response": "True", "imdbID": "tt0111161", "Title": "The Shawshank Redemption", "Year": "1994"},
        status=200,
    )

    matcher = OMDbMatcher(api_key="fake-key", rate_limit_seconds=0)
    item = FAItem(title="Cadena perpetua", year=1993, media_type="movie")  # año ligeramente distinto

    result = matcher.match(item)

    assert result.imdb_id == "tt0111161"


@responses.activate
def test_match_returns_none_when_never_found():
    responses.add(responses.GET, OMDB_URL, json={"Response": "False"}, status=200)

    matcher = OMDbMatcher(api_key="fake-key", rate_limit_seconds=0)
    item = FAItem(title="Película inexistente", year=None, media_type="movie")

    result = matcher.match(item)

    assert result.imdb_id is None
    assert result.confidence == "none"
