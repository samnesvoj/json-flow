"""Processing many files at once for `json-flow batch`."""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .formats import FlowError, read, write
from .validate import check_schema, validate

_EXT = {"json": ".json", "jsonl": ".jsonl", "csv": ".csv", "yaml": ".yaml"}


@dataclass
class BatchResult:
    converted: list[tuple[Path, Path]] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)


def expand(patterns: list[str]) -> list[Path]:
    """Expand glob patterns ourselves (Windows shells don't), keeping order and dropping duplicates."""
    seen: dict[Path, None] = {}
    for pattern in patterns:
        matches = sorted(glob.glob(pattern, recursive=True)) if glob.has_magic(pattern) else [pattern]
        for m in matches:
            p = Path(m)
            if p.is_file():
                seen.setdefault(p.resolve(), None)
    return list(seen)


def plan_outputs(inputs: list[Path], out_dir: Path, fmt: str) -> list[Path]:
    """Mirror the inputs' directory layout under out_dir, so a/x.csv and b/x.csv do not collide."""
    if not inputs:
        return []
    base = Path(os.path.commonpath([p.parent for p in inputs]))
    return [out_dir / p.relative_to(base).with_suffix(_EXT[fmt]) for p in inputs]


def run_batch(patterns: list[str], out_dir: str, fmt: str, *, schema: Any = None, infer_types: bool = True,
              indent: int = 2) -> BatchResult:
    inputs = expand(patterns)
    if not inputs:
        raise FlowError("no input files matched")
    if schema is not None:
        check_schema(schema)
    result = BatchResult()
    for src, dst in zip(inputs, plan_outputs(inputs, Path(out_dir), fmt)):
        try:
            data = read(str(src), infer_types=infer_types)
            if schema is not None:
                errors = validate(data, schema, each=isinstance(data, list))
                if errors:
                    more = f" (+{len(errors) - 1} more)" if len(errors) > 1 else ""
                    raise FlowError(f"invalid: {errors[0]}{more}")
            write(data, str(dst), fmt, indent=indent)
            result.converted.append((src, dst))
        except FlowError as e:
            result.failed.append((src, str(e)))
    return result
