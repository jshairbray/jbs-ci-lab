"""Build MongoDB aggregation pipelines from simple choices. No database needed."""

import json
from pprint import pformat

from query import condition
from schema import RELATIONS, SCHEMA


def reverse_join(collection: str, join: str) -> tuple[str, str] | None:
    """'quotes:company_id' from companies -> ("quotes", "company_id").

    A reverse join brings in the documents of another collection that point HERE:
    every quote whose company_id is this company's _id. Returns None for a normal join.
    """
    if ":" not in join:
        return None
    other, field = join.split(":", 1)
    if other not in SCHEMA or field not in SCHEMA[other]:
        raise ValueError(f"unknown join '{join}'")
    if field not in RELATIONS or RELATIONS[field][0] != collection:
        raise ValueError(f"{other}.{field} doesn't point to {collection}")
    return other, field


def _used(available: dict[str, str], alias: str) -> bool:
    return any(p == alias or p.startswith(alias + ".") for p in available)


def fields_after_joins(collection: str, joins: list[str]) -> dict[str, str]:
    """All field paths available after the joins, with their types.

    Example: quotes + ["company_id"] -> {"pe_ratio": "float", ..., "company.symbol": "str", ...}
    Example: companies + ["quotes:company_id"] -> {..., "quotes.pe_ratio": "float", ...}
    """
    if collection not in SCHEMA:
        raise ValueError(f"unknown collection: {collection}")
    available = {f: kind for f, (kind, _) in SCHEMA[collection].items()}
    for join in joins:
        rev = reverse_join(collection, join)
        if rev:
            target, alias = rev[0], rev[0]
        else:
            if join not in available:
                raise ValueError(f"can't join on '{join}': no such field yet")
            target, alias = join_target(join)
        if _used(available, alias):
            raise ValueError(f"'{alias}' is already joined")
        for f, (kind, _) in SCHEMA[target].items():
            available[f"{alias}.{f}"] = kind
    return available


def join_target(local: str) -> tuple[str, str]:
    """'company_id' or 'company.sector_id' -> (collection to join, alias for the result)."""
    last = local.rsplit(".", 1)[-1]
    if last not in RELATIONS:
        raise ValueError(f"'{local}' doesn't point to another collection")
    return RELATIONS[last]


def joinable(collection: str, joins: list[str]) -> list[str]:
    """Joins that could be added next (the page offers these)."""
    available = fields_after_joins(collection, joins)
    out = []
    for path in available:  # normal joins: a field that points to another collection
        last = path.rsplit(".", 1)[-1]
        if last not in RELATIONS or path in joins or RELATIONS[last][0] == collection:
            continue  # not a link, already joined, or pointing back to where we started
        if not _used(available, RELATIONS[last][1]):
            out.append(path)
    for other in sorted(SCHEMA):  # reverse joins: collections that point to this one
        for field in SCHEMA[other]:
            if RELATIONS.get(field, ("",))[0] == collection and not _used(available, other):
                out.append(f"{other}:{field}")
    return out


def join_stages(collection: str, joins: list[str]) -> list[dict]:
    """$lookup + $unwind for each join, in order."""
    fields_after_joins(collection, joins)  # validates every join
    stages = []
    for join in joins:
        rev = reverse_join(collection, join)
        if rev:
            other, field = rev
            lookup = {"from": other, "localField": "_id", "foreignField": field, "as": other}
            alias = other
        else:
            target, alias = join_target(join)
            lookup = {"from": target, "localField": join, "foreignField": "_id", "as": alias}
        stages.append({"$lookup": lookup})
        # $lookup always returns a list. $unwind makes one document per item:
        # one match for a normal join, possibly many for a reverse join.
        stages.append({"$unwind": {"path": f"${alias}", "preserveNullAndEmptyArrays": True}})
    return stages


def sort_stage(available: dict[str, str], sort: list[tuple[str, str]]) -> dict:
    """[("pe_ratio", "desc")] -> {"$sort": {"pe_ratio": -1}}. First field sorts first."""
    spec = {}
    for field, direction in sort:
        if field not in available:
            raise ValueError(f"can't sort by '{field}': no such field")
        if direction not in ("asc", "desc"):
            raise ValueError(f"sort direction must be asc or desc, not '{direction}'")
        spec[field] = 1 if direction == "asc" else -1
    return {"$sort": spec}


def limit_stage(n: int) -> dict:
    """Keep only the first n documents (1 to 1000)."""
    if not 1 <= n <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    return {"$limit": n}


def project_stage(available: dict[str, str], keep: list[str]) -> dict:
    """Show only these fields. _id is hidden unless you pick it."""
    if not keep:
        raise ValueError("pick at least one field to show")
    spec = {} if "_id" in keep else {"_id": 0}
    for field in keep:
        if field not in available:
            raise ValueError(f"can't show '{field}': no such field")
        spec[field] = 1
    return {"$project": spec}


GROUP_OPS = ("count", "avg", "sum", "min", "max")


def metric_name(op: str, field: str | None) -> str:
    """("avg", "pe_ratio") -> "avg_pe_ratio"; ("count", None) -> "count"."""
    return "count" if op == "count" else f"{op}_{field.replace('.', '_')}"


def group_stage(
    available: dict[str, str], by: str | None, metrics: list[tuple[str, str | None]]
) -> dict:
    """Group documents and summarize each group.

    by="sector.name", metrics=[("avg", "pe_ratio"), ("count", None)] ->
    {"$group": {"_id": "$sector.name", "avg_pe_ratio": {"$avg": "$pe_ratio"}, "count": {"$sum": 1}}}
    by=None puts every document in one group.
    """
    if by is not None and by not in available:
        raise ValueError(f"can't group by '{by}': no such field")
    if not metrics:
        raise ValueError("pick at least one summary, e.g. count")
    spec: dict = {"_id": f"${by}" if by else None}
    for op, field in metrics:
        if op not in GROUP_OPS:
            raise ValueError(f"unknown summary: {op}")
        if op == "count":
            spec["count"] = {"$sum": 1}
            continue
        if field not in available:
            raise ValueError(f"can't {op} '{field}': no such field")
        if available[field] not in ("int", "float"):
            raise ValueError(f"{op} needs a number field; {field} is {available[field]}")
        spec[metric_name(op, field)] = {f"${op}": f"${field}"}
    return {"$group": spec}


def fields_after_group(available: dict[str, str], by: str | None, metrics: list) -> dict[str, str]:
    """After $group only the group key (_id) and the summaries exist. Sort and show use these."""
    out = {"_id": available.get(by, "null") if by else "null"}
    for op, field in metrics:
        out[metric_name(op, field)] = "int" if op == "count" else "float"
    return out


def match_stage(available: dict[str, str], rows: list[tuple[str, str, str]], match: str) -> dict | None:
    """Filter rows -> {"$match": ...}, using field types after the joins. None if no rows."""
    parts = []
    for field, op, value in rows:
        f = field.strip()
        if f not in available:
            raise ValueError(f"can't filter on '{f}': no such field")
        parts.append(condition(f, op, value, available[f]))
    if not parts:
        return None
    if len(parts) == 1:
        return {"$match": parts[0]}
    return {"$match": {"$and" if match == "all" else "$or": parts}}


def build_pipeline(
    collection: str,
    joins: list[str] | None = None,
    rows: list[tuple[str, str, str]] | None = None,
    match: str = "all",
    group_by: str | None = None,
    metrics: list[tuple[str, str | None]] | None = None,
    sort: list[tuple[str, str]] | None = None,
    limit: int | None = None,
    project: list[str] | None = None,
) -> list[dict]:
    """All choices -> stages in this order: joins, $match, $group, $sort, $limit, $project."""
    joins = joins or []
    stages = join_stages(collection, joins)
    available = fields_after_joins(collection, joins)

    m = match_stage(available, rows or [], match)
    if m:
        stages.append(m)
    if metrics:
        stages.append(group_stage(available, group_by, metrics))
        available = fields_after_group(available, group_by, metrics)
    elif group_by:
        raise ValueError("grouping needs at least one summary, e.g. count")
    if sort:
        stages.append(sort_stage(available, sort))
    if limit is not None:
        stages.append(limit_stage(limit))
    if project:
        stages.append(project_stage(available, project))
    return stages


def to_mongosh_pipeline(stages: list[dict], collection: str) -> str:
    return f"db.{collection}.aggregate({json.dumps(stages, indent=2)})"


def to_pymongo_pipeline(stages: list[dict], collection: str) -> str:
    return f"db.{collection}.aggregate(\n{pformat(stages, sort_dicts=False)}\n)"
