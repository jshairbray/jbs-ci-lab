import pytest

from pipeline import fields_after_joins, join_stages, joinable


def test_companies_can_reverse_join_quotes():
    assert "quotes:company_id" in joinable("companies", [])


def test_reverse_join_adds_fields():
    fields = fields_after_joins("companies", ["quotes:company_id"])
    assert fields["quotes.pe_ratio"] == "float"


def test_reverse_join_stages():
    assert join_stages("companies", ["quotes:company_id"]) == [
        {"$lookup": {"from": "quotes", "localField": "_id", "foreignField": "company_id", "as": "quotes"}},
        {"$unwind": {"path": "$quotes", "preserveNullAndEmptyArrays": True}},
    ]


def test_reverse_then_normal_join():
    joins = ["quotes:company_id", "quotes.report_id", "sector_id"]
    fields = fields_after_joins("companies", joins)
    assert fields["report.generated_at"] == "str"
    assert fields["sector.name"] == "str"


def test_reverse_join_must_point_here():
    with pytest.raises(ValueError, match="doesn't point to"):
        fields_after_joins("companies", ["quotes:report_id"])


def test_reverse_join_unknown():
    with pytest.raises(ValueError, match="unknown join"):
        fields_after_joins("companies", ["trades:company_id"])


def test_sectors_offer_companies():
    assert joinable("sectors", []) == ["companies:sector_id"]


def test_no_join_back_to_start():
    assert "quotes.company_id" not in joinable("companies", ["quotes:company_id"])
