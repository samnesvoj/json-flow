import json

import pytest

from json_flow.formats import FlowError, detect_format, dumps, flatten, infer, loads, unflatten


@pytest.mark.parametrize(
    "text, expected",
    [("42", 42), ("-7", -7), ("0", 0), ("0.5", 0.5), ("1e3", 1000.0), ("007", "007"),
     ("true", True), ("FALSE", False), ("", None), ("null", None), ("[1, 2]", [1, 2]),
     ("hello", "hello"), ("1_000", "1_000"), (" 5", " 5")],
)
def test_infer(text, expected):
    assert infer(text) == expected


def test_flatten_round_trip():
    record = {"a": {"b": 1, "c": {"d": "x"}}, "tags": ["t"], "empty": {}}
    flat = flatten(record)
    assert flat == {"a.b": 1, "a.c.d": "x", "tags": '["t"]', "empty": "{}"}
    assert unflatten({"a.b": 1, "a.c.d": "x"}) == {"a": {"b": 1, "c": {"d": "x"}}}


def test_csv_to_records_infers_types_and_nesting(examples):
    rows = loads((examples / "people.csv").read_text(), "csv")
    assert rows[0] == {"id": 1, "name": "Ada", "age": 36, "city": "London",
                       "address": {"zip": "007"}, "active": True, "tags": ["math", "engines"]}


def test_csv_without_inference_keeps_strings(examples):
    rows = loads((examples / "people.csv").read_text(), "csv", infer_types=False)
    assert rows[1]["age"] == "29" and rows[1]["active"] == "false"


@pytest.mark.parametrize("fmt", ["json", "jsonl", "yaml", "csv"])
def test_round_trip_every_format(fmt, examples):
    rows = loads((examples / "people.csv").read_text(), "csv")
    assert loads(dumps(rows, fmt), fmt) == rows


def test_csv_output_union_of_columns_and_nulls():
    out = dumps([{"a": 1}, {"b": None, "c": True}], "csv")
    assert out == "a,b,c\n1,,\n,,true\n"


def test_csv_output_rejects_scalars():
    with pytest.raises(FlowError, match="list of objects"):
        dumps([1, 2], "csv")


def test_invalid_json_is_a_flow_error():
    with pytest.raises(FlowError, match="invalid JSON"):
        loads("{nope", "json")


def test_detect_format():
    assert detect_format("x.YML") == "yaml"
    assert detect_format("x.ndjson") == "jsonl"
    with pytest.raises(FlowError):
        detect_format("x.txt")


def test_unicode_is_kept():
    assert json.loads(dumps({"name": "Соня"}, "json")) == {"name": "Соня"}
    assert "Соня" in dumps({"name": "Соня"}, "yaml")
