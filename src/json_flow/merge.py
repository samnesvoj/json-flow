"""Combining several documents for `json-flow merge`."""

from __future__ import annotations

import copy
from typing import Any

from .formats import FlowError
from .query import _MISSING, get_path


def deep_merge(base: Any, update: Any, *, list_mode: str = "concat") -> Any:
    """Recursively merge `update` into a copy of `base`; on conflicts `update` wins.

    list_mode: "concat" appends lists, "replace" takes the newer list.
    """
    if isinstance(base, dict) and isinstance(update, dict):
        out = copy.deepcopy(base)
        for key, value in update.items():
            out[key] = deep_merge(out[key], value, list_mode=list_mode) if key in out else copy.deepcopy(value)
        return out
    if isinstance(base, list) and isinstance(update, list) and list_mode == "concat":
        return copy.deepcopy(base) + copy.deepcopy(update)
    return copy.deepcopy(update)


def merge_by_key(lists: list[list[Any]], key: str) -> list[Any]:
    """Upsert records by `key` (a dotted path): later records are deep-merged into earlier ones.

    Order follows first appearance; records without the key are appended as they are.
    """
    merged: dict[Any, Any] = {}
    order: list[Any] = []
    for records in lists:
        for record in records:
            if not isinstance(record, dict):
                raise FlowError("--key needs every list item to be an object")
            k = get_path(record, key)
            if k is _MISSING:
                order.append(("unkeyed", len(order)))
                merged[order[-1]] = copy.deepcopy(record)
                continue
            if isinstance(k, (dict, list)):
                raise FlowError(f"--key {key!r} must point at a scalar value")
            ident = ("key", k)
            if ident in merged:
                merged[ident] = deep_merge(merged[ident], record, list_mode="replace")
            else:
                order.append(ident)
                merged[ident] = copy.deepcopy(record)
    return [merged[i] for i in order]


def merge_documents(docs: list[Any], *, key: str | None = None, list_mode: str = "concat") -> Any:
    if not docs:
        raise FlowError("nothing to merge")
    if all(isinstance(d, list) for d in docs):
        if key:
            return merge_by_key(docs, key)
        return [item for d in docs for item in d]
    if all(isinstance(d, dict) for d in docs):
        if key:
            raise FlowError("--key only applies when merging lists of records")
        out: Any = {}
        for d in docs:
            out = deep_merge(out, d, list_mode=list_mode)
        return out
    kinds = sorted({type(d).__name__ for d in docs})
    raise FlowError(f"cannot merge different kinds of documents: {', '.join(kinds)}")
