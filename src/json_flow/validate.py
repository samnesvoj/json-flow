"""A focused JSON Schema subset for `json-flow validate`.

Unsupported keywords raise an error rather than being ignored, so a schema
can never pass data it was meant to reject.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

from .formats import FlowError

_ANNOTATIONS = {"$schema", "$id", "$comment", "title", "description", "default", "examples", "deprecated",
                "readOnly", "writeOnly"}
_SUPPORTED = {"type", "enum", "const", "required", "properties", "additionalProperties", "items",
              "minItems", "maxItems", "uniqueItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
              "minLength", "maxLength", "pattern", "minProperties", "maxProperties"}
_TYPES = {
    "null": lambda v: v is None,
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool) or isinstance(v, float) and v.is_integer(),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def _path(parts: tuple[Any, ...]) -> str:
    out = "$"
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else f".{p}"
    return out


def check_schema(schema: Any, where: str = "$") -> None:
    """Reject schemas using keywords this validator does not implement."""
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise FlowError(f"schema at {where} must be an object or boolean")
    unknown = set(schema) - _SUPPORTED - _ANNOTATIONS
    if unknown:
        raise FlowError(f"unsupported schema keyword(s) at {where}: {', '.join(sorted(unknown))}")
    types = schema.get("type", [])
    for t in [types] if isinstance(types, str) else types:
        if t not in _TYPES:
            raise FlowError(f"unknown type {t!r} at {where}")
    for name, sub in schema.get("properties", {}).items():
        check_schema(sub, f"{where}.properties.{name}")
    for key in ("items", "additionalProperties"):
        if key in schema and not isinstance(schema[key], bool):
            check_schema(schema[key], f"{where}.{key}")


def _type_name(v: Any) -> str:
    return next(t for t in ("null", "boolean", "integer", "number", "string", "array", "object") if _TYPES[t](v))


def iter_errors(value: Any, schema: Any, path: tuple[Any, ...] = ()) -> Iterator[str]:
    where = _path(path)
    if schema is True:
        return
    if schema is False:
        yield f"{where}: no value is allowed here"
        return
    if "type" in schema:
        allowed = [schema["type"]] if isinstance(schema["type"], str) else schema["type"]
        if not any(_TYPES[t](value) for t in allowed):
            yield f"{where}: expected {' or '.join(allowed)}, got {_type_name(value)}"
            return
    if "const" in schema and value != schema["const"]:
        yield f"{where}: must equal {schema['const']!r}"
    if "enum" in schema and value not in schema["enum"]:
        yield f"{where}: must be one of {schema['enum']!r}, got {value!r}"

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for key, bad, word in (("minimum", lambda v, b: v < b, ">="), ("maximum", lambda v, b: v > b, "<="),
                               ("exclusiveMinimum", lambda v, b: v <= b, ">"),
                               ("exclusiveMaximum", lambda v, b: v >= b, "<")):
            if key in schema and bad(value, schema[key]):
                yield f"{where}: must be {word} {schema[key]}, got {value}"

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            yield f"{where}: must be at least {schema['minLength']} characters"
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            yield f"{where}: must be at most {schema['maxLength']} characters"
        if "pattern" in schema and not re.search(schema["pattern"], value):
            yield f"{where}: does not match pattern {schema['pattern']!r}"

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            yield f"{where}: must have at least {schema['minItems']} items"
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            yield f"{where}: must have at most {schema['maxItems']} items"
        if schema.get("uniqueItems"):
            seen: list[Any] = []
            for i, item in enumerate(value):
                if item in seen:
                    yield f"{_path(path + (i,))}: duplicate item {item!r}"
                seen.append(item)
        if "items" in schema:
            for i, item in enumerate(value):
                yield from iter_errors(item, schema["items"], path + (i,))

    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                yield f"{where}: missing required property {name!r}"
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            yield f"{where}: must have at least {schema['minProperties']} properties"
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            yield f"{where}: must have at most {schema['maxProperties']} properties"
        props = schema.get("properties", {})
        for name, sub in props.items():
            if name in value:
                yield from iter_errors(value[name], sub, path + (name,))
        extra = schema.get("additionalProperties", True)
        for name in value:
            if name in props:
                continue
            if extra is False:
                yield f"{_path(path + (name,))}: property is not allowed"
            elif isinstance(extra, dict):
                yield from iter_errors(value[name], extra, path + (name,))


def validate(value: Any, schema: Any, *, each: bool = False) -> list[str]:
    """Return a list of error messages; empty means valid. With each=True every list item is checked."""
    check_schema(schema)
    if each:
        if not isinstance(value, list):
            raise FlowError("--each needs the input to be a list")
        return [err for i, item in enumerate(value) for err in iter_errors(item, schema, (i,))]
    return list(iter_errors(value, schema))
