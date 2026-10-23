# json-flow

Convert, filter, merge, validate and batch-process **JSON, JSON Lines, CSV and YAML** from the command line.
One small dependency (PyYAML), predictable output, useful exit codes.

```console
$ json-flow convert examples/people.csv --to yaml
- id: 1
  name: Ada
  age: 36
  city: London
  address:
    zip: '007'
  active: true
  tags:
  - math
  - engines
...
```

CSV values are typed on the way in (`36` → number, `true` → boolean, `""` → null, JSON arrays/objects are parsed),
while values with leading zeros such as ZIP codes stay strings. Dotted column names (`address.zip`) become nested
objects, and nested objects are flattened back into dotted columns when you write CSV.

## Install

Requires Python 3.10+.

```bash
pip install git+https://github.com/samnesvoj/json-flow.git
```

## Usage

```bash
json-flow convert data.csv -o data.json          # format picked from the extension
json-flow convert data.json --to csv              # to stdout
json-flow convert config.yaml --to json --indent 0
cat data.jsonl | json-flow convert - --from jsonl --to yaml
```

| Option | Description |
|---|---|
| `-o, --output FILE` | write to a file (directories are created); default is stdout |
| `--from FORMAT` | input format: `json`, `jsonl`, `csv`, `yaml` (default: from the extension) |
| `--to FORMAT` | output format (default: from the `-o` extension, otherwise `json`) |
| `--indent N` | JSON indentation, `0` for compact output |
| `--no-infer` | keep CSV values as strings |

Formats are recognised from `.json`, `.jsonl`/`.ndjson`, `.csv`, `.yaml`/`.yml`. Exit code is `0` on success and
`1` on a user error (missing file, invalid input, data that cannot be written as CSV), with a one-line message on
stderr.

## Use it as a library

```python
from json_flow.formats import read, dumps

people = read("examples/people.csv")
print(dumps([p for p in people if p["active"]], "yaml"))
```

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
