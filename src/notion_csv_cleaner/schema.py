from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set


class NotionSchema:
    def __init__(self, config: Dict[str, Any]):
        self.expected_columns: List[str] = config.get("expected_columns", [])
        self.required_fields: List[str] = config.get("required_fields", [])
        self.valid_containers: Set[str] = set(config.get("valid_containers", []))
        self.select_mappings: Dict[str, Any] = config.get("select_mappings", {})
        self.default_mappings: Dict[str, str] = config.get("default_mappings", {})

    @classmethod
    def load(cls, path: Path | None = None) -> NotionSchema:
        if path and path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return cls(json.load(f))

        default_path = Path(__file__).parent / "default_schema.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return cls(json.load(f))

        return cls({})
