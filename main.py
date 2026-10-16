"""Web API around query.py. Run locally: uvicorn main:app --reload"""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from query import OPERATORS, build_filter, to_mongosh, to_pymongo
from schema import SCHEMA, collections

app = FastAPI(title="Mongo query builder")

PAGE = Path(__file__).parent / "static" / "index.html"


class Row(BaseModel):
    field: str
    op: str
    value: str = ""


class BuildRequest(BaseModel):
    collection: str
    match: Literal["all", "any"] = "all"
    rows: list[Row]


@app.get("/", include_in_schema=False)
def page() -> FileResponse:
    """The query builder page."""
    return FileResponse(PAGE)


@app.get("/healthz")
def healthz() -> dict:
    """Cloud Run and CI call this to check the app is up."""
    return {"status": "ok"}


@app.get("/api/schema")
def get_schema() -> dict:
    """Collections, their fields and types, and the operators. Fills the page's dropdowns."""
    return {
        "collections": {c: {f: kind for f, (kind, _) in SCHEMA[c].items()} for c in collections()},
        "operators": list(OPERATORS),
    }


@app.post("/api/build")
def build(req: BuildRequest) -> dict:
    """Rows from the page -> the filter, plus ready-to-paste mongosh and Python."""
    try:
        flt = build_filter([(r.field, r.op, r.value) for r in req.rows], req.match, req.collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return {
        "filter": flt,
        "mongosh": to_mongosh(flt, req.collection),
        "pymongo": to_pymongo(flt, req.collection),
    }
