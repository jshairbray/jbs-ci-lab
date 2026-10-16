"""Build MongoDB aggregation pipelines from simple choices. No database needed."""

from schema import RELATIONS, SCHEMA


def fields_after_joins(collection: str, joins: list[str]) -> dict[str, str]:
    """All field paths available after the joins, with their types.

    Example: quotes + ["company_id"] -> {"pe_ratio": "float", ..., "company.symbol": "str", ...}
    """
    if collection not in SCHEMA:
        raise ValueError(f"unknown collection: {collection}")
    available = {f: kind for f, (kind, _) in SCHEMA[collection].items()}
    for local in joins:
        if local not in available:
            raise ValueError(f"can't join on '{local}': no such field yet")
        target, alias = join_target(local)
        if any(p == alias or p.startswith(alias + ".") for p in available):
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
    """Fields that could be joined next (the page offers these)."""
    available = fields_after_joins(collection, joins)
    out = []
    for path in available:
        last = path.rsplit(".", 1)[-1]
        if last in RELATIONS and path not in joins:
            alias = RELATIONS[last][1]
            if not any(p == alias or p.startswith(alias + ".") for p in available):
                out.append(path)
    return out


def join_stages(collection: str, joins: list[str]) -> list[dict]:
    """$lookup + $unwind for each join, in order."""
    fields_after_joins(collection, joins)  # validates every join
    stages = []
    for local in joins:
        target, alias = join_target(local)
        stages.append(
            {"$lookup": {"from": target, "localField": local, "foreignField": "_id", "as": alias}}
        )
        # $lookup always returns a list; $unwind turns the one match into a plain sub-document
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
