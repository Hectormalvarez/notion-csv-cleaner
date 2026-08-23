from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List

from notion_csv_cleaner.schema import NotionSchema


def sanitize_row(row: Dict[str, str], schema: NotionSchema, line_num: int) -> Dict[str, str]:
    cleaned: Dict[str, str] = {col: row.get(col, "").strip() for col in schema.expected_columns}

    for req in schema.required_fields:
        if not cleaned.get(req):
            raise ValueError(f"Line {line_num}: Required field '{req}' cannot be empty.")

    container_val = cleaned.get("Container")
    if schema.valid_containers and container_val and container_val not in schema.valid_containers:
        print(f"[!] Warning (Line {line_num}): Container '{container_val}' not in standard list.")

    for col, rules in schema.select_mappings.items():
        if col not in cleaned:
            continue

        raw_val = cleaned[col]
        allowed = rules.get("allowed", [])
        fallbacks = rules.get("fallbacks", {})
        default_val = rules.get("default", "")

        if allowed and raw_val in allowed:
            continue

        matched = False
        lower_raw = raw_val.lower()
        for keyword, standardized in fallbacks.items():
            if keyword in lower_raw:
                cleaned[col] = standardized
                matched = True
                break

        if not matched and default_val:
            cleaned[col] = default_val

    for target_col, source_col in schema.default_mappings.items():
        if not cleaned.get(target_col) and cleaned.get(source_col):
            cleaned[target_col] = cleaned[source_col]

    return cleaned


def process_csv(
    input_path: Path,
    output_path: Path | None = None,
    schema_path: Path | None = None,
) -> Path:
    schema = NotionSchema.load(schema_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        raw_content = f.read().strip()

    raw_lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
    if not raw_lines:
        raise ValueError(f"File '{input_path}' is empty.")

    reader = csv.DictReader(raw_lines)
    if not reader.fieldnames:
        raise ValueError("Could not parse CSV headers.")

    normalized_fieldnames = [fn.strip() for fn in reader.fieldnames]
    missing_cols = [c for c in schema.expected_columns if c not in normalized_fieldnames]
    if missing_cols:
        print(f"[!] Warning: Missing expected columns: {missing_cols}")

    processed_rows: List[Dict[str, str]] = [
        sanitize_row({k.strip(): v for k, v in row.items() if k}, schema, idx)
        for idx, row in enumerate(reader, start=2)
    ]

    if not output_path:
        primary_container = processed_rows[0].get("Container", "tasks") if processed_rows else "tasks"
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", primary_container).strip("_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = input_path.parent / f"notion_clean_{slug}_{timestamp}.csv"

    with open(output_path, mode="w", newline="\n", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=schema.expected_columns,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(processed_rows)

    print(f"[✓] Sanitized {len(processed_rows)} rows -> {output_path}")
    return output_path
