from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_schema_lists_collections_and_operators():
    body = client.get("/api/schema").json()
    assert body["collections"]["quotes"]["pe_ratio"] == "float"
    assert "greater than" in body["operators"]


def test_build_returns_filter_and_code():
    r = client.post(
        "/api/build",
        json={"collection": "quotes", "rows": [{"field": "pe_ratio", "op": "less than", "value": "20"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["filter"] == {"pe_ratio": {"$lt": 20.0}}
    assert body["mongosh"].startswith("db.quotes.find(")


def test_bad_value_gives_400_with_reason():
    r = client.post(
        "/api/build",
        json={"collection": "quotes", "rows": [{"field": "pe_ratio", "op": "less than", "value": "abc"}]},
    )
    assert r.status_code == 400
    assert "not a number" in r.json()["detail"]


def test_bad_match_gives_422():
    r = client.post("/api/build", json={"collection": "quotes", "match": "some", "rows": []})
    assert r.status_code == 422
