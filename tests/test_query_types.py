import pytest

from query import build_filter


def test_float_field_turns_text_into_number():
    assert build_filter([("current_price", "greater than", "100")], collection="quotes") == {
        "current_price": {"$gt": 100.0}
    }


def test_text_field_keeps_digits_as_text():
    assert build_filter([("symbol", "equals", "100")], collection="companies") == {"symbol": "100"}


def test_letters_in_number_field_are_refused():
    with pytest.raises(ValueError, match="not a number"):
        build_filter([("pe_ratio", "less than", "abc")], collection="quotes")


def test_null_works_on_number_field():
    assert build_filter([("pe_ratio", "equals", "null")], collection="quotes") == {"pe_ratio": None}


def test_unknown_field_is_refused():
    with pytest.raises(ValueError, match="has no field"):
        build_filter([("price", "equals", "1")], collection="quotes")


def test_unknown_collection_is_refused():
    with pytest.raises(ValueError, match="unknown collection"):
        build_filter([("_id", "equals", "1")], collection="trades")


def test_contains_refused_on_number_field():
    with pytest.raises(ValueError, match="only works on text"):
        build_filter([("volume", "contains", "5")], collection="quotes")


def test_one_of_ints():
    assert build_filter([("sector_id", "one of", "1, 3")], collection="companies") == {
        "sector_id": {"$in": [1, 3]}
    }
