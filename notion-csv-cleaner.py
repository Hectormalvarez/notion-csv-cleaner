#!/usr/bin/env python3
"""Notion Life OS CSV Cleaner & Standardizer.

Reads any downloaded or raw CSV text file, validates against the Notion Life OS
Task schema, strips non-standard browser/clipboard formatting artifacts, and
outputs a clean, Notion-ready CSV file with utf-8-sig encoding and Unix newlines.

Usage:
    python3 notion_csv_cleaner.py <input_file> [-o <output_file>]
    python3 notion_csv_cleaner.py raw_tasks.txt
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Dict, List

# Strict Workspace Schema Definitions
EXPECTED_COLUMNS = [
    "Task Name",
    "Container",
    "Energy Demand",
    "Status",
    "MVD Baseline",
    "Scheduled Date",
    "Completed Date",
    "Minutes",
    "Category",
]

VALID_CONTAINERS = {
    # Projects (Finite Goals)
    "AWS Certified Solutions Architect - Associate (SAA-C03)",
    "ServiceNow Administration Fundamentals",
    "Security+ SY0-701",
    "CCNA",
    "CASP",
    "Khan Academy",
    "PracticalSQL",
    "Homelab",
    "MG Drywall USA Website",
    # Pillars (Ongoing Operational Areas)
    "Career",
    "Finance",
    "Health",
    "Fitness",
    "Home",
    "Family",
    "Kids — School",
    "Kids — Activities",
    "Wife",
    "Shopping",
    "Admin",
}

VALID_ENERGY = {"🔋 High", "🟡 Medium", "🧘 Low"}
VALID_STATUS = {"To-do", "In progress", "Complete"}
VALID_MVD = {"Yes", "No"}


def sanitize_row(row: Dict[str, str], line_num: int) -> Dict[str, str]:
    """Cleans up individual field values and validates schema adherence."""
    cleaned: Dict[str, str] = {}
    for col in EXPECTED_COLUMNS:
        cleaned[col] = row.get(col, "").strip()

    # Required field verification
    if not cleaned["Task Name"]:
        raise ValueError(f"Line {line_num}: 'Task Name' cannot be empty.")

    # Container validation
    container = cleaned["Container"]
    if container not in VALID_CONTAINERS:
        print(f"[!] Warning (Line {line_num}): Container '{container}' is not recognized in standard Life OS schema.")

    # Normalization fallbacks
    if cleaned["Energy Demand"] not in VALID_ENERGY:
        raw_val = cleaned["Energy Demand"].lower()
        if "high" in raw_val:
            cleaned["Energy Demand"] = "🔋 High"
        elif "med" in raw_val:
            cleaned["Energy Demand"] = "🟡 Medium"
        elif "low" in raw_val:
            cleaned["Energy Demand"] = "🧘 Low"
        else:
            cleaned["Energy Demand"] = "🟡 Medium"

    if cleaned["Status"] not in VALID_STATUS:
        cleaned["Status"] = "To-do"

    if cleaned["MVD Baseline"] not in VALID_MVD:
        cleaned["MVD Baseline"] = "Yes" if "yes" in cleaned["MVD Baseline"].lower() else "No"

    # Category fallback to container
    if not cleaned["Category"]:
        cleaned["Category"] = cleaned["Container"]

    return cleaned


def process_csv(input_path: Path, output_path: Path | None = None) -> Path:
    """Parses, validates, and re-writes the CSV with strict Notion compatibility."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Read raw content, stripping null bytes and leading/trailing whitespace
    with open(input_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        raw_content = f.read().strip()

    # Split lines and filter out accidental empty lines
    raw_lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
    if not raw_lines:
        raise ValueError(f"File '{input_path}' is completely empty.")

    reader = csv.DictReader(raw_lines)
    
    # Check headers
    if not reader.fieldnames:
        raise ValueError("Could not parse CSV headers from input file.")

    normalized_fieldnames = [fn.strip() for fn in reader.fieldnames]
    missing_cols = [col for col in EXPECTED_COLUMNS if col not in normalized_fieldnames]
    if missing_cols:
        print(f"[!] Warning: Input file is missing expected columns: {missing_cols}")

    processed_rows: List[Dict[str, str]] = []
    for idx, row in enumerate(reader, start=2):
        # Normalize keys in case of trailing spaces in header
        clean_row = {k.strip(): v for k, v in row.items() if k}
        processed_rows.append(sanitize_row(clean_row, idx))

    # Determine output path if not specified
    if not output_path:
        primary_container = processed_rows[0]["Container"] if processed_rows else "tasks"
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", primary_container).strip("_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = input_path.parent / f"notion_tasks_{slug}_{timestamp}.csv"

    # Write clean CSV with UTF-8-SIG, RFC 4180 minimal quotes, and explicit \n
    with open(output_path, mode="w", newline="\n", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=EXPECTED_COLUMNS,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(processed_rows)

    print(f"[✓] Sanitized and wrote {len(processed_rows)} tasks -> {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean raw CSV text into a Notion-compliant Tasks CSV.")
    parser.add_argument("input", type=Path, help="Path to raw downloaded CSV or text file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Custom destination CSV path")
    args = parser.parse_args()

    try:
        process_csv(args.input, args.output)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()