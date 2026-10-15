from schema import SCHEMA, collections, fields

KNOWN_TYPES = {"int", "float", "str", "objectid"}


def test_ten_collections():
    assert len(collections()) == 10


def test_every_collection_has_id():
    for name in collections():
        assert "_id" in fields(name), name


def test_only_known_types():
    for name, cols in SCHEMA.items():
        for field, (kind, nullable) in cols.items():
            assert kind in KNOWN_TYPES, f"{name}.{field}"
            assert isinstance(nullable, bool), f"{name}.{field}"
