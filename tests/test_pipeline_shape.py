import pytest

from pipeline import fields_after_joins, limit_stage, project_stage, sort_stage

QUOTES = fields_after_joins("quotes", ["company_id"])


def test_sort_desc():
    assert sort_stage(QUOTES, [("pe_ratio", "desc")]) == {"$sort": {"pe_ratio": -1}}


def test_sort_two_fields_keeps_order():
    stage = sort_stage(QUOTES, [("company.symbol", "asc"), ("pe_ratio", "desc")])
    assert list(stage["$sort"]) == ["company.symbol", "pe_ratio"]


def test_sort_unknown_field():
    with pytest.raises(ValueError, match="no such field"):
        sort_stage(QUOTES, [("price", "asc")])


def test_sort_bad_direction():
    with pytest.raises(ValueError, match="asc or desc"):
        sort_stage(QUOTES, [("pe_ratio", "up")])


def test_limit():
    assert limit_stage(10) == {"$limit": 10}


@pytest.mark.parametrize("n", [0, 1001])
def test_limit_out_of_range(n):
    with pytest.raises(ValueError):
        limit_stage(n)


def test_project_hides_id_by_default():
    assert project_stage(QUOTES, ["company.symbol", "pe_ratio"]) == {
        "$project": {"_id": 0, "company.symbol": 1, "pe_ratio": 1}
    }


def test_project_keeps_id_when_picked():
    assert project_stage(QUOTES, ["_id", "pe_ratio"]) == {"$project": {"_id": 1, "pe_ratio": 1}}


def test_project_needs_a_field():
    with pytest.raises(ValueError, match="at least one"):
        project_stage(QUOTES, [])
