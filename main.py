"""Web API around query.py and pipeline.py. Run locally: uvicorn main:app --reload"""

from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from pipeline import (
    GROUP_OPS,
    build_pipeline,
    fields_after_joins,
    joinable,
    to_mongosh_pipeline,
    to_pymongo_pipeline,
)
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


class Metric(BaseModel):
    op: str
    field: str | None = None


class SortKey(BaseModel):
    field: str
    direction: Literal["asc", "desc"] = "asc"


class AggregateRequest(BaseModel):
    collection: str
    joins: list[str] = []
    match: Literal["all", "any"] = "all"
    rows: list[Row] = []
    group_by: str | None = None
    metrics: list[Metric] = []
    sort: list[SortKey] = []
    limit: int | None = None
    project: list[str] = []


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
        "group_ops": list(GROUP_OPS),
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


@app.get("/api/fields")
def get_fields(collection: str, joins: Annotated[list[str] | None, Query()] = None) -> dict:
    """Fields available after the joins, and what could be joined next."""
    joins = joins or []
    try:
        return {
            "fields": fields_after_joins(collection, joins),
            "joinable": joinable(collection, joins),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@app.post("/api/aggregate")
def aggregate(req: AggregateRequest) -> dict:
    """All pipeline choices -> the stages, plus ready-to-paste mongosh and Python."""
    try:
        stages = build_pipeline(
            req.collection,
            joins=req.joins,
            rows=[(r.field, r.op, r.value) for r in req.rows],
            match=req.match,
            group_by=req.group_by,
            metrics=[(m.op, m.field) for m in req.metrics],
            sort=[(s.field, s.direction) for s in req.sort],
            limit=req.limit,
            project=req.project,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return {
        "pipeline": stages,
        "mongosh": to_mongosh_pipeline(stages, req.collection),
        "pymongo": to_pymongo_pipeline(stages, req.collection),
    }
