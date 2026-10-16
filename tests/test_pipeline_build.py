import pytest

from pipeline import build_pipeline, to_mongosh_pipeline, to_pymongo_pipeline


def test_only_collection_gives_empty_pipeline():
    assert build_pipeline("quotes") == []


def test_stage_order():
    stages = build_pipeline(
        "quotes",
        joins=["company_id", "company.sector_id"],
        rows=[("pe_ratio", "less than", "50")],
        group_by="sector.name",
        metrics=[("avg", "pe_ratio"), ("count", None)],
        sort=[("avg_pe_ratio", "desc")],
        limit=5,
        project=["_id", "avg_pe_ratio"],
    )
    names = [next(iter(s)) for s in stages]
    assert names == ["$lookup", "$unwind", "$lookup", "$unwind", "$match", "$group", "$sort", "$limit", "$project"]


def test_filter_on_joined_field_uses_its_type():
    stages = build_pipeline("quotes", joins=["company_id"], rows=[("company.symbol", "equals", "100")])
    assert stages[-1] == {"$match": {"company.symbol": "100"}}


def test_filter_on_unjoined_field_is_refused():
    with pytest.raises(ValueError, match="can't filter"):
        build_pipeline("quotes", rows=[("company.symbol", "equals", "AAPL")])


def test_two_rows_any():
    stages = build_pipeline("quotes", rows=[("volume", "at least", "1"), ("pe_ratio", "equals", "null")], match="any")
    assert list(stages[0]["$match"]) == ["$or"]


def test_group_by_without_summary_is_refused():
    with pytest.raises(ValueError, match="needs at least one summary"):
        build_pipeline("quotes", group_by="company_id")


def test_top_ten_by_pe():
    stages = build_pipeline(
        "quotes",
        joins=["company_id"],
        sort=[("pe_ratio", "desc")],
        limit=10,
        project=["company.symbol", "pe_ratio"],
    )
    assert stages[-3:] == [
        {"$sort": {"pe_ratio": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0, "company.symbol": 1, "pe_ratio": 1}},
    ]


def test_output_text():
    stages = [{"$limit": 1}]
    assert to_mongosh_pipeline(stages, "quotes").startswith("db.quotes.aggregate([")
    assert "{'$limit': 1}" in to_pymongo_pipeline(stages, "quotes")
