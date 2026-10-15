"""Turn simple conditions into a MongoDB filter. No database needed."""

import json
import re

from schema import SCHEMA

# Words shown in the app -> MongoDB operator
OPERATORS = {
    "equals": None,
    "not equals": "$ne",
    "greater than": "$gt",
    "at least": "$gte",
    "less than": "$lt",
    "at most": "$lte",
    "one of": "$in",
    "contains": "$regex",
    "exists": "$exists",
}


def parse_value(text: str, kind: str | None = None):
    """Convert typed text to a value.

    kind=None guesses: '42' -> 42, '4.5' -> 4.5, 'true' -> True, 'null' -> None.
    kind='int' / 'float' / 'str' converts to that type, or raises ValueError.
    'null' always means None. Wrap text in double quotes to keep it as text.
    """
    t = text.strip()
    if t.lower() == "null":
        return None
    if len(t) >= 2 and t[0] == t[-1] == '"':
        t = t[1:-1]
        if kind in (None, "str"):
            return t

    if kind == "str":
        return t
    if kind == "int":
        try:
            return int(t)
        except ValueError:
            raise ValueError(f"'{t}' is not a whole number") from None
    if kind == "float":
        try:
            return float(t)
        except ValueError:
            raise ValueError(f"'{t}' is not a number") from None
    if kind == "objectid":
        raise ValueError("searching ObjectId fields isn't supported yet")

    # kind is None: guess
    low = t.lower()
    if low in ("true", "false"):
        return low == "true"
    for convert in (int, float):
        try:
            return convert(t)
        except ValueError:
            pass
    return t


def condition(field: str, op: str, value: str, kind: str | None = None) -> dict:
    """One row of the form -> one MongoDB condition."""
    field = field.strip()
    if not field:
        raise ValueError("field is empty")
    if op not in OPERATORS:
        raise ValueError(f"unknown operator: {op}")

    if op == "exists":
        return {field: {"$exists": parse_value(value) is not False}}
    if op == "contains":
        if kind not in (None, "str"):
            raise ValueError(f"'contains' only works on text fields; {field} is {kind}")
        return {field: {"$regex": re.escape(value.strip()), "$options": "i"}}
    if op == "one of":
        return {field: {"$in": [parse_value(v, kind) for v in value.split(",")]}}
    if op == "equals":
        return {field: parse_value(value, kind)}
    return {field: {OPERATORS[op]: parse_value(value, kind)}}


def build_filter(
    conditions: list[tuple[str, str, str]],
    match: str = "all",
    collection: str | None = None,
) -> dict:
    """Several rows -> one filter. match='all' uses $and, 'any' uses $or.

    With a collection, each field must exist there and values use its type.
    """
    parts = []
    for field, op, value in conditions:
        kind = None
        if collection is not None:
            cols = SCHEMA.get(collection)
            if cols is None:
                raise ValueError(f"unknown collection: {collection}")
            if field.strip() not in cols:
                raise ValueError(f"{collection} has no field '{field.strip()}'")
            kind = cols[field.strip()][0]
        parts.append(condition(field, op, value, kind))

    if not parts:
        return {}
    if len(parts) == 1:
        return parts[0]
    return {"$and" if match == "all" else "$or": parts}


def to_mongosh(flt: dict, collection: str = "collection") -> str:
    return f"db.{collection}.find({json.dumps(flt, indent=2)})"


def to_pymongo(flt: dict, collection: str = "collection") -> str:
    return f"db.{collection}.find({flt!r})"
