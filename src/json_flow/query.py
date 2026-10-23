"""Field paths, conditions and projections for `json-flow filter`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from .formats import FlowError, infer

_MISSING = object()
_CONDITION = re.compile(r"^\s*([^\s=!<>~]+)\s*(==|!=|>=|<=|~=|>|<)\s*(.*?)\s*$")


def get_path(record: Any, path: str) -> Any:
    """Look up "a.b.0.c" in nested dicts and lists; returns _MISSING when absent."""
    node = record
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.lstrip("-").isdigit() and -len(node) <= int(part) < len(node):
            node = node[int(part)]
        else:
            return _MISSING
    return node


def _compare(op: str, left: Any, right: Any) -> bool:
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    # ordering only between two numbers or two strings
    numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (left, right))
    if not numeric and not (isinstance(left, str) and isinstance(right, str)):
        return False
    return {">": left > right, ">=": left >= right, "<": left < right, "<=": left <= right}[op]


@dataclass(frozen=True)
class Condition:
    path: str
    op: str
    raw: str

    @classmethod
    def parse(cls, text: str) -> "Condition":
        m = _CONDITION.match(text)
        if not m:
            raise FlowError(f"cannot parse condition {text!r} (expected e.g. 'age>=18' or 'name~=^A')")
        path, op, raw = m.groups()
        if op == "~=":
            try:
                re.compile(raw)
            except re.error as e:
                raise FlowError(f"invalid regular expression in {text!r}: {e}") from e
        return cls(path, op, raw)

    def __call__(self, record: Any) -> bool:
        value = get_path(record, self.path)
        if value is _MISSING:
            return self.op == "!="
        if self.op == "~=":
            haystack = value if isinstance(value, list) else [value]
            return any(re.search(self.raw, str(v)) for v in haystack if v is not None)
        # quoted values are literal strings: name=="007"
        if len(self.raw) >= 2 and self.raw[0] == self.raw[-1] and self.raw[0] in "\"'":
            target: Any = self.raw[1:-1]
        else:
            target = infer(self.raw)
        return _compare(self.op, value, target)


def build_predicate(conditions: list[str], any_of: bool = False) -> Callable[[Any], bool]:
    parsed = [Condition.parse(c) for c in conditions]
    if not parsed:
        return lambda _r: True
    combine = any if any_of else all
    return lambda record: combine(c(record) for c in parsed)


def project(record: Any, paths: list[str]) -> dict[str, Any]:
    """Keep only the given (possibly dotted) fields, preserving nesting."""
    out: dict[str, Any] = {}
    for path in paths:
        value = get_path(record, path)
        if value is _MISSING:
            continue
        node = out
        *parents, leaf = path.split(".")
        for p in parents:
            node = node.setdefault(p, {})
        node[leaf] = value
    return out


def sort_records(records: list[Any], key: str, descending: bool = False) -> list[Any]:
    """Sort by a field. Records missing the field (or holding null) always go last."""
    present = [r for r in records if get_path(r, key) not in (_MISSING, None)]
    absent = [r for r in records if get_path(r, key) in (_MISSING, None)]
    try:
        present.sort(key=lambda r: get_path(r, key), reverse=descending)
    except TypeError as e:
        raise FlowError(f"cannot sort by {key!r}: values have mixed types") from e
    return present + absent
