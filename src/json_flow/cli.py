"""Command-line interface."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .formats import FORMATS, FlowError, detect_format, read, write


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="json-flow", description=__doc__.strip() if __doc__ else None)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert", help="convert between JSON, JSON Lines, CSV and YAML")
    p.add_argument("input", help="input file, or - for stdin (with --from)")
    _add_io(p)
    p.set_defaults(func=cmd_convert)
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
