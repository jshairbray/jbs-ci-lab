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
