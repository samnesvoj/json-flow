import json

import pytest

from json_flow.batch import expand, plan_outputs, run_batch
from json_flow.formats import FlowError
from json_flow.cli import main


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "in" / "a").mkdir(parents=True)
    (tmp_path / "in" / "b").mkdir()
    (tmp_path / "in" / "a" / "users.csv").write_text("id,name\n1,Ada\n2,Linus\n")
    (tmp_path / "in" / "b" / "users.csv").write_text("id,name\n3,Grace\n")
    (tmp_path / "in" / "b" / "settings.yaml").write_text("debug: true\n")
    (tmp_path / "in" / "b" / "broken.json").write_text("{oops")
    return tmp_path


def test_expand_globs_recursively_without_duplicates(tree):
    files = expand([str(tree / "in" / "**" / "*.csv"), str(tree / "in" / "a" / "users.csv")])
    assert [p.parent.name + "/" + p.name for p in files] == ["a/users.csv", "b/users.csv"]


def test_outputs_mirror_layout_so_names_do_not_collide(tree):
    inputs = expand([str(tree / "in" / "**" / "*.csv")])
    outs = plan_outputs(inputs, tree / "out", "json")
    assert [o.relative_to(tree / "out").as_posix() for o in outs] == ["a/users.json", "b/users.json"]


def test_batch_converts_and_reports_failures(tree):
    result = run_batch([str(tree / "in" / "**" / "*.*")], str(tree / "out"), "json")
    assert sorted(d.relative_to(tree / "out").as_posix() for _, d in result.converted) == [
        "a/users.json", "b/settings.json", "b/users.json"]
    assert [(s.name, "invalid JSON" in e) for s, e in result.failed] == [("broken.json", True)]
    assert json.loads((tree / "out" / "a" / "users.json").read_text()) == [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]


def test_batch_validates_before_writing(tree):
    schema = {"type": "object", "required": ["id", "name"], "properties": {"id": {"type": "integer", "maximum": 2}}}
    result = run_batch([str(tree / "in" / "**" / "*.csv")], str(tree / "out"), "yaml", schema=schema)
    assert [s.parent.name for s, _ in result.converted] == ["a"]
    assert result.failed[0][1] == "invalid: $[0].id: must be <= 2, got 3"
    assert not (tree / "out" / "b" / "users.yaml").exists()


def test_no_matches_is_an_error(tmp_path):
    with pytest.raises(FlowError, match="no input files"):
        run_batch([str(tmp_path / "*.csv")], str(tmp_path / "out"), "json")


def test_cli_exit_code_and_summary(tree, capsys):
    rc = main(["batch", str(tree / "in" / "**" / "*.*"), "--to", "yaml", "--out-dir", str(tree / "out")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "3/4 converted, 1 failed" in err
