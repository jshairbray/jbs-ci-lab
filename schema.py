"""Collections and fields in the local `stocks` database (names and types only, no data).

Types: "int", "float", "str", "objectid".
Fields marked nullable=True can also be null.
Regenerate the list by hand from: python /c/Temp/mongo_schema.py stocks
"""

N = True  # shorthand: this field can be null

SCHEMA: dict[str, dict[str, tuple[str, bool]]] = {
    "companies": {
        "_id": ("int", False),
        "symbol": ("str", False),
        "name": ("str", False),
        "industry_id": ("int", False),
        "sector_id": ("int", False),
        "exchange_id": ("int", False),
    },
    "exchanges": {
        "_id": ("int", False),
        "name": ("str", False),
        "exchange_name": ("str", False),
    },
    "fundamentals": {
        "_id": ("int", False),
        "report_id": ("int", False),
        "company_id": ("int", False),
        "price_to_book": ("float", False),
        "book_value": ("float", False),
        "return_on_equity": ("float", N),
        "debt_to_equity": ("float", N),
        "current_ratio": ("float", N),
        "quick_ratio": ("float", N),
        "revenue_growth": ("float", False),
        "earnings_growth": ("float", N),
        "free_cashflow": ("float", N),
        "operating_cashflow": ("float", False),
        "profit_margins": ("float", False),
        "gross_margins": ("float", False),
        "operating_margins": ("float", False),
        "return_on_assets": ("float", N),
        "enterprise_value": ("float", False),
        "peg_ratio": ("float", N),
        "forward_pe": ("float", False),
        "trailing_pe": ("float", N),
    },
    "group_members": {
        "_id": ("objectid", False),
        "group_id": ("int", False),
        "company_id": ("int", False),
    },
    "groups": {
        "_id": ("int", False),
        "name": ("str", False),
    },
    "industries": {
        "_id": ("int", False),
        "name": ("str", False),
    },
    "portfolio_owners": {
        "_id": ("int", False),
        "name": ("str", False),
    },
    "quotes": {
        "_id": ("int", False),
        "report_id": ("int", False),
        "company_id": ("int", False),
        "pe_ratio": ("float", N),
        "dividend_yield": ("float", N),
        "current_price": ("float", False),
        "previous_close": ("float", False),
        "day_high": ("float", False),
        "day_low": ("float", False),
        "week52_high": ("float", False),
        "week52_low": ("float", False),
        "volume": ("int", False),
        "market_cap": ("float", False),
        "error_message": ("str", N),
    },
    "reports": {
        "_id": ("int", False),
        "generated_at": ("str", False),
    },
    "sectors": {
        "_id": ("int", False),
        "name": ("str", False),
    },
}


def collections() -> list[str]:
    return sorted(SCHEMA)


def fields(collection: str) -> list[str]:
    return list(SCHEMA[collection])
