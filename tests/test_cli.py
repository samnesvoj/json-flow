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
