import pytest

from biblissima.rql import iter_rows, page_query, quote

from conftest import FakeClient


def test_quote_plain_and_with_quotes():
    assert quote("Pal.gr.348") == '"Pal.gr.348"'
    assert quote('say "hi"') == "'say \"hi\"'"


def test_quote_rejects_unsafe_values():
    for bad in ["a\\b", "a\nb", "it's \"both\""]:
        with pytest.raises(ValueError):
            quote(bad)


def test_page_query_clause_order():
    q = page_query("M,U", "M is Manuscript", order_by="M", limit=10, offset=20)
    assert q == "Any M,U ORDERBY M LIMIT 10 OFFSET 20 WHERE M is Manuscript"


def test_page_query_validates():
    with pytest.raises(ValueError):
        page_query("M", "M is Manuscript", order_by="M", limit=0, offset=0)


def test_iter_rows_pages_until_short_page():
    client = FakeClient([[[1], [2]], [[3], [4]], [[5]]])
    rows = list(iter_rows(client, "M", "M is Manuscript", order_by="M", page_size=2))
    assert rows == [[1], [2], [3], [4], [5]]
    assert "OFFSET 0" in client.queries[0] and "OFFSET 4" in client.queries[2]
    assert client.allow_empty_flags == [False, True, True]


def test_iter_rows_handles_exact_multiple_with_empty_last_page():
    client = FakeClient([[[1], [2]], []])
    rows = list(iter_rows(client, "M", "M is Manuscript", order_by="M", page_size=2))
    assert rows == [[1], [2]]


def test_iter_rows_respects_limit():
    client = FakeClient([[[1], [2], [3]]])
    rows = list(iter_rows(client, "M", "M is Manuscript", order_by="M", page_size=3, limit=3))
    assert rows == [[1], [2], [3]]
    assert len(client.queries) == 1


def test_page_query_distinct():
    q = page_query("W,P", "W is Work", order_by="W,P", limit=5, offset=0, distinct=True)
    assert q.startswith("DISTINCT Any W,P ORDERBY")
