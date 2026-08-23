from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Set


def generate_schema_from_csv(input_path: Path, output_path: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Could not parse CSV headers from {input_path}")

        headers = [h.strip() for h in reader.fieldnames if h]
        sample_values: Dict[str, Set[str]] = {h: set() for h in headers}

        for row in reader:
            for h in headers:
                val = row.get(h, "").strip()
                if val:
                    sample_values[h].add(val)

    required_field = [headers[0]] if headers else []
    select_mappings: Dict[str, Any] = {}
    valid_containers: list[str] = []

    if "Container" in sample_values:
        valid_containers = sorted(sample_values["Container"])

    for col, values in sample_values.items():
        if col != "Container" and 0 < len(values) <= 6:
            select_mappings[col] = {
                "default": next(iter(values)),
                "allowed": sorted(values),
                "fallbacks": {},
            }

    schema_config = {
        "expected_columns": headers,
        "required_fields": required_field,
        "valid_containers": valid_containers,
        "select_mappings": select_mappings,
        "default_mappings": {},
    }

    with open(output_path, mode="w", encoding="utf-8") as f:
        json.dump(schema_config, f, indent=2, ensure_ascii=False)

    print(f"[✓] Generated starter schema -> {output_path}")
    return output_path
