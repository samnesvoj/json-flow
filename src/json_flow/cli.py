"""Command-line interface."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .formats import FORMATS, FlowError, detect_format, read, write
from .merge import merge_documents
from .query import build_predicate, project, sort_records


def _add_io(p: argparse.ArgumentParser) -> None:
    p.add_argument("-o", "--output", help="output file (default: stdout)")
    p.add_argument("--from", dest="src_format", choices=FORMATS, help="input format (default: from extension)")
    p.add_argument("--to", dest="dst_format", choices=FORMATS, help="output format (default: from -o extension, else json)")
    p.add_argument("--indent", type=int, default=2, help="JSON indentation, 0 for compact (default: 2)")
    p.add_argument("--no-infer", action="store_true", help="keep CSV values as strings")


def _output_format(args: argparse.Namespace) -> str:
    if args.dst_format:
        return args.dst_format
    if args.output and args.output != "-":
        return detect_format(args.output)
    return "json"


def cmd_convert(args: argparse.Namespace) -> int:
    data = read(args.input, args.src_format, infer_types=not args.no_infer)
    write(data, args.output, _output_format(args), indent=args.indent)
    return 0


def _records(data: object, what: str) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        lists = [k for k, v in data.items() if isinstance(v, list)]
        if len(lists) == 1:  # {"items": [...]} — operate on the only list
            return data[lists[0]]
    raise FlowError(f"{what} needs a list of records (or an object holding exactly one list)")


def cmd_filter(args: argparse.Namespace) -> int:
    records = _records(read(args.input, args.src_format, infer_types=not args.no_infer), "filter")
    keep = build_predicate(args.where or [], any_of=args.any)
    result = [r for r in records if keep(r)]
    if args.sort:
        result = sort_records(result, args.sort, descending=args.desc)
    if args.limit is not None:
        result = result[: args.limit]
    if args.select:
        fields = [f.strip() for f in args.select.split(",") if f.strip()]
        result = [project(r, fields) for r in result]
    if args.count:
        print(len(result))
    else:
        write(result, args.output, _output_format(args), indent=args.indent)
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    docs = [read(path, args.src_format, infer_types=not args.no_infer) for path in args.inputs]
    merged = merge_documents(docs, key=args.key, list_mode="replace" if args.replace_lists else "concat")
    write(merged, args.output, _output_format(args), indent=args.indent)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="json-flow", description=__doc__.strip() if __doc__ else None)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert", help="convert between JSON, JSON Lines, CSV and YAML")
    p.add_argument("input", help="input file, or - for stdin (with --from)")
    _add_io(p)
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("filter", help="keep records matching conditions; select, sort and limit")
    p.add_argument("input", help="input file, or - for stdin (with --from)")
    p.add_argument("-w", "--where", action="append", metavar="COND",
                   help="condition like 'age>=18', 'city==Paris', 'name~=^A' (repeatable; all must match)")
    p.add_argument("--any", action="store_true", help="keep records matching any condition instead of all")
    p.add_argument("-s", "--select", metavar="FIELDS", help="comma-separated fields to keep, e.g. name,address.zip")
    p.add_argument("--sort", metavar="FIELD", help="sort by a field (records without it go last)")
    p.add_argument("--desc", action="store_true", help="sort in descending order")
    p.add_argument("--limit", type=int, metavar="N", help="keep at most N records")
    p.add_argument("--count", action="store_true", help="print only the number of matching records")
    _add_io(p)
    p.set_defaults(func=cmd_filter)

    p = sub.add_parser("merge", help="merge files: concatenate lists, deep-merge objects, upsert by key")
    p.add_argument("inputs", nargs="+", help="files to merge, in order (formats may differ)")
    p.add_argument("-k", "--key", metavar="FIELD", help="merge list records that share this field (upsert)")
    p.add_argument("--replace-lists", action="store_true",
                   help="when deep-merging objects, replace lists instead of concatenating them")
    _add_io(p)
    p.set_defaults(func=cmd_merge)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FlowError as e:
        print(f"json-flow: {e}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
