import json
import subprocess
import sys

from json_flow.cli import main


def test_convert_csv_to_json_stdout(examples, capsys):
    assert main(["convert", str(examples / "people.csv")]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [p["name"] for p in data] == ["Ada", "Linus", "Grace"]


def test_convert_picks_output_format_from_extension(examples, tmp_path):
    out = tmp_path / "nested" / "people.yaml"
    assert main(["convert", str(examples / "people.csv"), "-o", str(out)]) == 0
    assert out.read_text().startswith("- id: 1\n")


def test_compact_json(examples, capsys):
    main(["convert", str(examples / "people.csv"), "--indent", "0"])
    assert capsys.readouterr().out.count("\n") == 1


def test_missing_file_exits_1(capsys):
    assert main(["convert", "nope.json"]) == 1
    assert "file not found" in capsys.readouterr().err


def test_stdin_needs_from(capsys):
    assert main(["convert", "-"]) == 1


def test_module_entry_point_reads_stdin():
    r = subprocess.run([sys.executable, "-m", "json_flow", "convert", "-", "--from", "yaml", "--to", "json", "--indent", "0"],
                       input="a: 1\nb: [x, y]\n", capture_output=True, text=True, check=True)
    assert json.loads(r.stdout) == {"a": 1, "b": ["x", "y"]}


def test_filter_select_sort_limit(examples, capsys):
    rc = main(["filter", str(examples / "people.csv"), "-w", "active==true", "--sort", "age", "--desc",
               "--select", "name,age", "--indent", "0"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == [{"name": "Grace", "age": 45}, {"name": "Ada", "age": 36}]


def test_filter_count(examples, capsys):
    main(["filter", str(examples / "people.csv"), "-w", "age<40", "--count"])
    assert capsys.readouterr().out.strip() == "2"


def test_filter_unwraps_single_list_object(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text('{"items": [{"a": 1}, {"a": 2}]}')
    main(["filter", str(f), "-w", "a>1", "--indent", "0"])
    assert json.loads(capsys.readouterr().out) == [{"a": 2}]


def test_filter_rejects_scalars(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("42")
    assert main(["filter", str(f)]) == 1
