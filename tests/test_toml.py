import sys

import pytest

from json_flow.formats import FlowError, dumps, loads
from json_flow.cli import main

pytestmark = pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib needs Python 3.11+")


def test_toml_tables_arrays_and_dates(examples):
    data = loads((examples / "app.toml").read_text(), "toml")
    assert data["app"] == {"name": "json-flow demo", "debug": False, "released": "2026-10-23"}
    assert data["database"]["ports"] == [5432, 5433]
    assert [u["name"] for u in data["users"]] == ["Ada", "Linus"]


def test_toml_errors_are_flow_errors():
    with pytest.raises(FlowError, match="invalid TOML"):
        loads("key = ", "toml")


def test_toml_is_input_only():
    with pytest.raises(FlowError, match="input format only"):
        dumps({"a": 1}, "toml")


def test_cli_filters_a_toml_array_of_tables(examples, capsys):
    assert main(["filter", str(examples / "app.toml"), "-w", "roles~=admin", "--select", "name", "--indent", "0"]) == 0
    assert capsys.readouterr().out.strip() == '[{"name": "Ada"}]'
