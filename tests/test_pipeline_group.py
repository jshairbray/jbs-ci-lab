import pytest

from pipeline import fields_after_group, fields_after_joins, group_stage, sort_stage

JOINED = fields_after_joins("quotes", ["company_id", "company.sector_id"])


def test_average_pe_by_sector_with_count():
    stage = group_stage(JOINED, "sector.name", [("avg", "pe_ratio"), ("count", None)])
    assert stage == {
        "$group": {"_id": "$sector.name", "avg_pe_ratio": {"$avg": "$pe_ratio"}, "count": {"$sum": 1}}
    }


def test_no_group_field_means_one_group():
    stage = group_stage(JOINED, None, [("max", "volume")])
    assert stage == {"$group": {"_id": None, "max_volume": {"$max": "$volume"}}}


def test_dotted_field_name_becomes_underscore():
    stage = group_stage(JOINED, None, [("min", "company.sector_id")])
    assert "min_company_sector_id" in stage["$group"]


def test_avg_needs_number_field():
    with pytest.raises(ValueError, match="needs a number"):
        group_stage(JOINED, "sector.name", [("avg", "company.symbol")])


def test_unknown_group_field():
    with pytest.raises(ValueError, match="can't group by"):
        group_stage(JOINED, "sector.title", [("count", None)])


def test_needs_a_summary():
    with pytest.raises(ValueError, match="at least one"):
        group_stage(JOINED, "sector.name", [])


def test_unknown_summary():
    with pytest.raises(ValueError, match="unknown summary"):
        group_stage(JOINED, None, [("median", "pe_ratio")])


def test_after_group_only_key_and_summaries_remain():
    metrics = [("avg", "pe_ratio"), ("count", None)]
    after = fields_after_group(JOINED, "sector.name", metrics)
    assert after == {"_id": "str", "avg_pe_ratio": "float", "count": "int"}
    assert sort_stage(after, [("avg_pe_ratio", "desc")]) == {"$sort": {"avg_pe_ratio": -1}}
    with pytest.raises(ValueError):
        sort_stage(after, [("pe_ratio", "desc")])
