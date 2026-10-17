import pytest

from pipeline import fields_after_joins, join_stages, joinable


def test_no_joins_gives_own_fields():
    fields = fields_after_joins("quotes", [])
    assert fields["pe_ratio"] == "float"
    assert "company.symbol" not in fields


def test_join_adds_prefixed_fields():
    fields = fields_after_joins("quotes", ["company_id"])
    assert fields["company.symbol"] == "str"
    assert fields["company.sector_id"] == "int"


def test_chained_join_through_company_to_sector():
    fields = fields_after_joins("quotes", ["company_id", "company.sector_id"])
    assert fields["sector.name"] == "str"


def test_chained_join_needs_first_join():
    with pytest.raises(ValueError, match="no such field yet"):
        fields_after_joins("quotes", ["company.sector_id"])


def test_cannot_join_plain_field():
    with pytest.raises(ValueError, match="doesn't point"):
        fields_after_joins("quotes", ["pe_ratio"])


def test_cannot_join_twice():
    with pytest.raises(ValueError):
        fields_after_joins("quotes", ["company_id", "company_id"])


def test_joinable_offers_next_steps():
    assert set(joinable("quotes", [])) == {"company_id", "report_id"}
    after = joinable("quotes", ["company_id"])
    assert "company.sector_id" in after
    assert "company_id" not in after


def test_join_stages_lookup_then_unwind():
    assert join_stages("quotes", ["company_id"]) == [
        {"$lookup": {"from": "companies", "localField": "company_id", "foreignField": "_id", "as": "company"}},
        {"$unwind": {"path": "$company", "preserveNullAndEmptyArrays": True}},
    ]
