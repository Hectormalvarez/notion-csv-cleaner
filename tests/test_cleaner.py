"""Tests for schema loading and CSV cleaning pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from notion_csv_cleaner.cleaner import process_csv, sanitize_row
from notion_csv_cleaner.schema import NotionSchema

COLUMNS = [
    "Task Name", "Container", "Energy Demand", "Status",
    "MVD Baseline", "Scheduled Date", "Completed Date", "Minutes", "Category",
]


def _write_csv(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "input.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=COLUMNS).writerows([dict(zip(COLUMNS, COLUMNS))] + rows)
    return path


def _row(**overrides) -> dict[str, str]:
    base = {col: "" for col in COLUMNS}
    base["Task Name"] = "Sample task"
    base["Container"] = "Career"
    base.update(overrides)
    return base


def _schema_cfg(**overrides) -> dict:
    cfg: dict = {
        "expected_columns": COLUMNS,
        "required_fields": ["Task Name"],
        "valid_containers": ["Career", "Finance"],
        "select_mappings": {
            "Energy Demand": {
                "default": "\U0001f7e1 Medium",
                "fallbacks": {"high": "\U0001f50b High", "low": "\U0001f9d8 Low"},
            },
            "Status": {"default": "To-do", "allowed": ["To-do", "In progress", "Complete"]},
            "MVD Baseline": {"default": "No", "fallbacks": {"yes": "Yes", "no": "No"}},
        },
        "default_mappings": {"Category": "Container"},
    }
    cfg.update(overrides)
    return cfg


# -- Schema ------------------------------------------------------------------

class TestNotionSchema:
    def test_load_default(self):
        s = NotionSchema.load()
        assert len(s.expected_columns) == 9
        assert "Task Name" in s.required_fields

    def test_load_from_path(self, tmp_path):
        p = tmp_path / "s.json"
        p.write_text(json.dumps(_schema_cfg()), encoding="utf-8")
        s = NotionSchema.load(p)
        assert s.expected_columns == COLUMNS
        assert s.valid_containers == {"Career", "Finance"}

    def test_missing_file_falls_back_to_default(self, tmp_path):
        s = NotionSchema.load(tmp_path / "nope.json")
        assert len(s.expected_columns) == 9  # bundled default

    def test_empty_config(self):
        s = NotionSchema({})
        assert s.expected_columns == []
        assert s.valid_containers == set()

# -- sanitize_row ------------------------------------------------------------

class TestSanitizeRow:
    def setup_method(self):
        self.schema = NotionSchema(_schema_cfg())

    def test_passthrough(self):
        r = sanitize_row(_row(), self.schema, 2)
        assert r["Task Name"] == "Sample task"

    def test_energy_high(self):
        assert sanitize_row(_row(**{"Energy Demand": "HIGH"}), self.schema, 2)["Energy Demand"] == "\U0001f50b High"

    def test_energy_low(self):
        assert sanitize_row(_row(**{"Energy Demand": "low energy"}), self.schema, 2)["Energy Demand"] == "\U0001f9d8 Low"

    def test_energy_unknown_defaults(self):
        assert sanitize_row(_row(**{"Energy Demand": "???"}), self.schema, 2)["Energy Demand"] == "\U0001f7e1 Medium"

    def test_status_invalid(self):
        assert sanitize_row(_row(**{"Status": "wip"}), self.schema, 2)["Status"] == "To-do"

    def test_mvd_yes_fallback(self):
        assert sanitize_row(_row(**{"MVD Baseline": "yes"}), self.schema, 2)["MVD Baseline"] == "Yes"

    def test_category_fallback(self):
        r = sanitize_row(_row(**{"Container": "Finance"}), self.schema, 2)
        assert r["Category"] == "Finance"

    def test_empty_required_raises(self):
        with pytest.raises(ValueError, match="Required field"):
            sanitize_row(_row(**{"Task Name": ""}), self.schema, 2)

    def test_whitespace_stripped(self):
        assert sanitize_row(_row(**{"Task Name": "  hi  "}), self.schema, 2)["Task Name"] == "hi"


# -- process_csv -------------------------------------------------------------

class TestProcessCSV:
    def test_end_to_end(self, tmp_path):
        csv_path = _write_csv(tmp_path, [_row(**{"Energy Demand": "high", "Status": "wip", "Category": ""})])
        out = tmp_path / "out.csv"
        process_csv(csv_path, out)
        with open(out, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["Energy Demand"] == "\U0001f50b High"
        assert rows[0]["Status"] == "To-do"
        assert rows[0]["Category"] == "Career"

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_csv(tmp_path / "nope.csv", tmp_path / "out.csv")

    def test_empty_file(self, tmp_path):
        (tmp_path / "empty.csv").write_text("")
        with pytest.raises(ValueError, match="empty"):
            process_csv(tmp_path / "empty.csv", tmp_path / "out.csv")

    def test_custom_schema(self, tmp_path):
        cfg = _schema_cfg(expected_columns=["Name", "Group"])
        cfg.update({"required_fields": ["Name"], "valid_containers": [], "select_mappings": {}, "default_mappings": {}})
        (tmp_path / "s.json").write_text(json.dumps(cfg), encoding="utf-8")
        with open(tmp_path / "mini.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["Name", "Group"])
            w.writeheader()
            w.writerow({"Name": "Widget", "Group": "A"})
        out = tmp_path / "out.csv"
        process_csv(tmp_path / "mini.csv", out, tmp_path / "s.json")
        with open(out, encoding="utf-8-sig") as f:
            assert list(csv.DictReader(f))[0]["Name"] == "Widget"

