from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_schema_lists_group_ops():
    assert "avg" in client.get("/api/schema").json()["group_ops"]


def test_fields_without_joins():
    body = client.get("/api/fields", params={"collection": "quotes"}).json()
    assert body["fields"]["pe_ratio"] == "float"
    assert set(body["joinable"]) == {"company_id", "report_id"}


def test_fields_after_two_joins():
    r = client.get("/api/fields", params={"collection": "quotes", "joins": ["company_id", "company.sector_id"]})
    assert r.status_code == 200
    assert r.json()["fields"]["sector.name"] == "str"


def test_fields_bad_join_gives_400():
    r = client.get("/api/fields", params={"collection": "quotes", "joins": ["pe_ratio"]})
    assert r.status_code == 400


def test_aggregate_average_pe_by_sector():
    r = client.post(
        "/api/aggregate",
        json={
            "collection": "quotes",
            "joins": ["company_id", "company.sector_id"],
            "group_by": "sector.name",
            "metrics": [{"op": "avg", "field": "pe_ratio"}, {"op": "count"}],
            "sort": [{"field": "avg_pe_ratio", "direction": "desc"}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert [next(iter(s)) for s in body["pipeline"]][-2:] == ["$group", "$sort"]
    assert body["mongosh"].startswith("db.quotes.aggregate([")


def test_aggregate_error_gives_400_with_reason():
    r = client.post("/api/aggregate", json={"collection": "quotes", "limit": 0})
    assert r.status_code == 400
    assert "limit" in r.json()["detail"]
