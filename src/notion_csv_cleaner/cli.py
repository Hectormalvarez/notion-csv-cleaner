from __future__ import annotations

import argparse
from pathlib import Path
import sys

from notion_csv_cleaner.cleaner import process_csv
from notion_csv_cleaner.generator import generate_schema_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="notion-clean",
        description="Notion CSV Cleaner & Schema Standardizer CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    clean_parser = subparsers.add_parser(
        "clean", help="Sanitize and validate a CSV against a schema"
    )
    clean_parser.add_argument("input", type=Path, help="Input CSV or text file")
    clean_parser.add_argument("-o", "--output", type=Path, default=None, help="Custom output CSV path")
    clean_parser.add_argument("-s", "--schema", type=Path, default=None, help="Custom schema JSON path")

    init_parser = subparsers.add_parser(
        "init-schema", help="Infer a starter schema JSON from a Notion CSV export"
    )
    init_parser.add_argument("input", type=Path, help="Exported Notion CSV file")
    init_parser.add_argument(
        "-o", "--output", type=Path, default=Path("schema.json"), help="Output JSON schema path"
    )

    args = parser.parse_args()

    try:
        if args.command == "clean":
            process_csv(args.input, args.output, args.schema)
        elif args.command == "init-schema":
            generate_schema_from_csv(args.input, args.output)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
