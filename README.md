# json-flow

Convert, filter, merge, validate and batch-process **JSON, JSON Lines, CSV and YAML** from the command line.

| Command | What it does |
|---|---|
| `convert` | change format, with typed CSV and nested columns |
| `filter` | keep records by conditions; select, sort, limit, count |
| `merge` | concatenate lists, deep-merge objects, upsert by key |
| `validate` | check against a strict JSON Schema subset |
| `batch` | convert and validate many files at once |

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

CSV values are typed on the way in (`36` → number, `true` → boolean, `""` → null, JSON arrays/objects are parsed).
Types are decided **per column**: a column is converted only when all of its values agree, so a ZIP column holding
`007` and `10001` stays text instead of mixing strings and numbers. Dotted column names (`address.zip`) become nested
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
| `--from FORMAT` | input format: `json`, `jsonl`, `csv`, `yaml`, `toml` (default: from the extension) |
| `--to FORMAT` | output format (default: from the `-o` extension, otherwise `json`) |
| `--indent N` | JSON indentation, `0` for compact output |
| `--no-infer` | keep CSV values as strings |

Formats are recognised from `.json`, `.jsonl`/`.ndjson`, `.csv`, `.yaml`/`.yml` and `.toml`. TOML is read-only
(Python 3.11+, via the standard library's `tomllib`); its dates and times become ISO 8601 strings, so a TOML config
can be filtered, validated or converted to any other format. Exit code is `0` on success and
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

## Validate

```console
$ echo '[{"id": 1, "name": "", "age": 200, "nickname": "x"}]' > bad.json
$ json-flow validate bad.json --schema examples/person.schema.yaml --each
$[0].name: must be at least 1 characters
$[0].age: must be <= 150, got 200
$[0].nickname: property is not allowed
✗ 3 error(s)
```

Schemas are JSON or YAML and use a focused subset of JSON Schema: `type` (including `integer` vs `number`, where
booleans are never numbers), `enum`, `const`, `required`, `properties`, `additionalProperties`, `items`,
`minItems`/`maxItems`/`uniqueItems`, `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum`,
`minLength`/`maxLength`/`pattern` and `minProperties`/`maxProperties`. Annotations such as `title` and `$schema` are
allowed. **Any other keyword is rejected** instead of silently ignored, so a schema can never pass data it was meant
to block.

| Option | Description |
|---|---|
| `--schema FILE` | schema to validate against (required) |
| `--each` | validate every item of a list (typical for CSV) |
| `--max-errors N` | print at most N errors (default 50) |
| `-q, --quiet` | print nothing; use the exit code (`0` valid, `1` invalid) |

## Batch processing

```console
$ json-flow batch 'exports/**/*.csv' --to json --out-dir out --schema examples/person.schema.yaml
✓ exports/2026/people.csv → out/2026/people.json
✗ exports/2027/people.csv: invalid: $[3].age: must be <= 150, got 200
1/2 converted, 1 failed
```

- Patterns are expanded by json-flow itself (`**` recurses), so quoting them works the same on every OS.
- The input folder layout is mirrored under `--out-dir`, so files with the same name never overwrite each other.
- With `--schema`, each file (each item, for lists) is validated first; invalid files are reported and not written.
- Every file is attempted; the exit code is `1` if any failed.

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
