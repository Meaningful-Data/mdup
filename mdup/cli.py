"""Command-line interface for mdup."""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .core import VALID_FORMATS, MarkdownConverter


def _parse_formats(value: str) -> list:
    fmts = [f.strip().lower() for f in value.split(",") if f.strip()]
    bad = [f for f in fmts if f not in VALID_FORMATS]
    if bad:
        raise argparse.ArgumentTypeError(
            f"invalid format(s): {', '.join(bad)} (choose from {', '.join(VALID_FORMATS)})"
        )
    if not fmts:
        raise argparse.ArgumentTypeError("no formats given")
    return fmts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdup",
        description="Export Markdown file(s) to DOCX and/or PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  mdup notes.md                         # -> notes.pdf\n"
            "  mdup notes.md -f docx,pdf -o out/     # both formats into out/\n"
            "  mdup a.md b.md --merge -o book.pdf    # one merged PDF\n"
            "  mdup a.md b.md -f docx                # a.docx and b.docx\n"
        ),
    )
    parser.add_argument("inputs", nargs="+", metavar="INPUT", help="Markdown file(s)")
    parser.add_argument(
        "-f", "--format", dest="formats", type=_parse_formats, default=["pdf"],
        metavar="FMT[,FMT]",
        help="output format(s): pdf, docx, or both (comma-separated). Default: pdf",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="output directory, or a file path. Default: alongside each input.",
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="with multiple inputs, produce a single merged file per format",
    )
    parser.add_argument(
        "--toc", action="store_true",
        help="insert a table of contents (or honour a [TOC] marker)",
    )
    parser.add_argument(
        "--pdf-backend", choices=("xhtml2pdf", "weasyprint"), default="xhtml2pdf",
        help="PDF engine. xhtml2pdf (default, pure-Python) or weasyprint (extra).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    parser.add_argument("--version", action="version", version=f"mdup {__version__}")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    try:
        converter = MarkdownConverter(
            args.formats,
            pdf_backend=args.pdf_backend,
            merge=args.merge,
            toc=args.toc,
        )
        written = converter.convert(args.inputs, output=args.output)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ImportError as exc:
        print(f"error: missing optional dependency — {exc}", file=sys.stderr)
        return 3

    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
