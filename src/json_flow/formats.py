"""Reading and writing JSON, JSON Lines, CSV and YAML."""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

FORMATS = ("json", "jsonl", "csv", "yaml")
_EXTENSIONS = {".json": "json", ".jsonl": "jsonl", ".ndjson": "jsonl", ".csv": "csv", ".yaml": "yaml", ".yml": "yaml"}


class FlowError(Exception):
    """A user-facing error: bad input, unsupported data shape, unknown format."""


def detect_format(path: str | Path, explicit: str | None = None) -> str:
    if explicit:
        if explicit not in FORMATS:
            raise FlowError(f"unknown format {explicit!r} (expected one of: {', '.join(FORMATS)})")
        return explicit
    fmt = _EXTENSIONS.get(Path(str(path)).suffix.lower())
    if fmt is None:
        raise FlowError(f"cannot tell the format of {path!s}; pass it explicitly")
    return fmt


# ── CSV helpers ────────────────────────────────────────────────────────────
def flatten(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """{"a": {"b": 1}} -> {"a.b": 1}. Lists are kept as JSON text so they survive a round trip."""
    out: dict[str, Any] = {}
    for key, value in record.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            out.update(flatten(value, f"{name}."))
        elif isinstance(value, (list, dict)):
            out[name] = json.dumps(value, ensure_ascii=False)
        else:
            out[name] = value
    return out


def unflatten(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in record.items():
        node = out
        *parents, leaf = key.split(".")
        for part in parents:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise FlowError(f"column {key!r} conflicts with a scalar column of the same prefix")
        node[leaf] = value
    return out


_INT = re.compile(r"-?(?:0|[1-9]\d*)")
_FLOAT = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+(?:[eE][-+]?\d+)?|[eE][-+]?\d+)")


def infer(value: str) -> Any:
    """Turn CSV text into the JSON value it most likely represents.

    Numbers with leading zeros ("007", ZIP codes) stay strings.
    """
    if value == "":
        return None
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if low == "null":
        return None
    if _INT.fullmatch(value):
        return int(value)
    if _FLOAT.fullmatch(value):
        return float(value)
    if value[:1] in "[{":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return value


def _kind(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (list, dict)):
        return "json"
    return "string"


def infer_columns(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Infer one type per column, so a column never mixes strings and numbers.

    Empty cells become null. A column is converted only when every non-empty cell infers to the
    same kind of value (all numbers, all booleans or all JSON); otherwise it stays text — e.g. a ZIP
    column with "007" and "10001" keeps both as strings.
    """
    columns = {k for row in rows for k in row}
    convert: set[str] = set()
    for col in columns:
        kinds = {_kind(infer(row[col])) for row in rows if row.get(col) not in (None, "")}
        if len(kinds) == 1 and kinds != {"string"}:
            convert.add(col)
    return [{k: None if v in (None, "") else infer(v) if k in convert else v for k, v in row.items()} for row in rows]


# ── public API ─────────────────────────────────────────────────────────────
def loads(text: str, fmt: str, *, infer_types: bool = True) -> Any:
    try:
        if fmt == "json":
            return json.loads(text)
        if fmt == "jsonl":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        if fmt == "yaml":
            return yaml.safe_load(text)
        if fmt == "csv":
            rows = list(csv.DictReader(io.StringIO(text)))
            if infer_types:
                rows = infer_columns(rows)
            return [unflatten(row) for row in rows]
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise FlowError(f"invalid {fmt.upper()}: {e}") from e
    raise FlowError(f"unknown format {fmt!r}")


def dumps(data: Any, fmt: str, *, indent: int = 2) -> str:
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=indent or None) + "\n"
    if fmt == "jsonl":
        rows = data if isinstance(data, list) else [data]
        return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    if fmt == "yaml":
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    if fmt == "csv":
        rows = [data] if isinstance(data, dict) else data
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise FlowError("CSV output needs an object or a list of objects")
        flat = [flatten(r) for r in rows]
        columns: list[str] = []
        for r in flat:
            columns += [c for c in r if c not in columns]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for r in flat:
            writer.writerow({k: _csv_cell(v) for k, v in r.items()})
        return buf.getvalue()
    raise FlowError(f"unknown format {fmt!r}")


def _csv_cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def read(path: str, fmt: str | None = None, *, infer_types: bool = True) -> Any:
    """Read a file (or stdin for "-", which needs an explicit format)."""
    if path == "-":
        if not fmt:
            raise FlowError("reading from stdin needs --from")
        return loads(sys.stdin.read(), fmt, infer_types=infer_types)
    p = Path(path)
    if not p.is_file():
        raise FlowError(f"file not found: {path}")
    return loads(p.read_text(encoding="utf-8-sig"), detect_format(p, fmt), infer_types=infer_types)


def write(data: Any, path: str | None, fmt: str, *, indent: int = 2) -> None:
    text = dumps(data, fmt, indent=indent)
    if path in (None, "-"):
        sys.stdout.write(text)
    else:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")
