import pytest

from json_flow.formats import FlowError
from json_flow.validate import validate

SCHEMA = {
    "type": "object",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "name": {"type": "string", "minLength": 2, "pattern": "^[A-Z]"},
        "role": {"enum": ["admin", "user"]},
        "tags": {"type": "array", "items": {"type": "string"}, "uniqueItems": True, "maxItems": 3},
        "score": {"type": "number", "exclusiveMaximum": 100},
    },
    "additionalProperties": False,
}


def test_valid_document():
    assert validate({"id": 1, "name": "Ada", "role": "admin", "tags": ["a"], "score": 99.5}, SCHEMA) == []


def test_collects_every_error_with_paths():
    errors = validate({"id": 0, "name": "a", "role": "root", "tags": ["x", 1, "x", "y"], "score": 100, "extra": 1},
                      SCHEMA)
    assert errors == [
        "$.id: must be >= 1, got 0",
        "$.name: must be at least 2 characters",
        "$.name: does not match pattern '^[A-Z]'",
        "$.role: must be one of ['admin', 'user'], got 'root'",
        "$.tags: must have at most 3 items",
        "$.tags[2]: duplicate item 'x'",
        "$.tags[1]: expected string, got integer",
        "$.score: must be < 100, got 100",
        "$.extra: property is not allowed",
    ]


def test_missing_required_and_type_mismatch():
    assert validate({"name": "Ada"}, SCHEMA) == ["$: missing required property 'id'"]
    assert validate([1], SCHEMA) == ["$: expected object, got array"]


def test_booleans_are_not_integers_but_whole_floats_are():
    assert validate(True, {"type": "integer"}) == ["$: expected integer, got boolean"]
    assert validate(3.0, {"type": "integer"}) == []


def test_each_validates_list_items_with_indexes():
    assert validate([{"id": 1, "name": "Ada"}, {"name": "Bo"}], SCHEMA, each=True) == [
        "$[1]: missing required property 'id'"]


def test_unsupported_keywords_are_rejected_not_ignored():
    with pytest.raises(FlowError, match="unsupported schema keyword.*oneOf"):
        validate({}, {"oneOf": [{"type": "string"}]})
    with pytest.raises(FlowError, match="unsupported.*properties.a"):
        validate({}, {"properties": {"a": {"format": "email"}}})


def test_annotations_are_allowed_and_boolean_schemas_work():
    assert validate(1, {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "x", "type": "integer"}) == []
    assert validate({"a": 1}, {"properties": {"a": False}}) == ["$.a: no value is allowed here"]
