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

## Filter, select and sort

```console
$ json-flow filter examples/people.csv -w 'age>=30' --sort age --desc --select name,city --to csv
name,city
Grace,New York
Ada,London
```

| Option | Description |
|---|---|
| `-w, --where COND` | keep records matching a condition; repeat for more (all must match) |
| `--any` | keep records matching *any* condition instead |
| `-s, --select FIELDS` | comma-separated fields to keep; dotted paths keep their nesting (`address.zip`) |
| `--sort FIELD` / `--desc` | sort by a field; records without it go last |
| `--limit N` | keep at most N records |
| `--count` | print only the number of matches |

Conditions are `FIELD OP VALUE` with `==`, `!=`, `>`, `>=`, `<`, `<=` or `~=` (regular expression search; on a list
it matches any element). Fields are dotted paths and may index lists (`tags.0`). Values are typed like CSV cells, so
`age>=18` compares numbers; quote a value to force a string (`zip=="007"`). Ordering comparisons between
incompatible types are simply false. If the input is an object holding exactly one list (`{"items": [...]}`), that
list is filtered.

## Merge

```console
$ json-flow merge examples/people.csv examples/users-update.yaml --key id --to csv
```

- **Lists** are concatenated in order.
- **Objects** are deep-merged; later files win on conflicts (lists inside them are concatenated, or replaced with
  `--replace-lists`). Handy for layered config: `json-flow merge base.yaml prod.json`.
- **`--key FIELD`** upserts list records that share a field (dotted paths allowed): later records are merged into
  earlier ones, order follows first appearance, and records without the key are kept as they are.

Inputs may be in different formats.

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
