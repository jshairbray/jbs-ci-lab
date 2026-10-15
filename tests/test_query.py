import pytest

from query import build_filter, condition, parse_value, to_mongosh


@pytest.mark.parametrize(
    "text, expected",
    [("42", 42), ("4.5", 4.5), ("true", True), ("null", None), ("AAPL", "AAPL"), ('"42"', "42")],
)
def test_parse_value(text, expected):
    assert parse_value(text) == expected


def test_equals():
    assert condition("ticker", "equals", "AAPL") == {"ticker": "AAPL"}


def test_greater_than():
    assert condition("price", "greater than", "100") == {"price": {"$gt": 100}}


def test_one_of():
    assert condition("ticker", "one of", "AAPL, MSFT") == {"ticker": {"$in": ["AAPL", "MSFT"]}}


def test_contains_escapes_special_characters():
    assert condition("name", "contains", "a.b") == {"name": {"$regex": r"a\.b", "$options": "i"}}


def test_two_rows_all_uses_and():
    flt = build_filter([("ticker", "equals", "AAPL"), ("price", "at least", "100")])
    assert flt == {"$and": [{"ticker": "AAPL"}, {"price": {"$gte": 100}}]}


def test_two_rows_any_uses_or():
    flt = build_filter([("a", "equals", "1"), ("b", "equals", "2")], match="any")
    assert list(flt) == ["$or"]


def test_no_rows_matches_everything():
    assert build_filter([]) == {}


def test_empty_field_is_refused():
    with pytest.raises(ValueError):
        condition(" ", "equals", "1")


def test_mongosh_output():
    assert to_mongosh({"a": 1}, "stocks").startswith("db.stocks.find(")
