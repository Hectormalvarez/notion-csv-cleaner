# Notion CSV Cleaner

Validate, sanitize, and format raw CSV task files for direct Notion database import.

## Installation

```bash
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Usage

### Infer a schema from a Notion database export

```bash
notion-clean init-schema exported_notion_db.csv -o my_schema.json
```

### Clean and standardize raw task data

```bash
# Using bundled default schema
notion-clean clean raw_tasks.txt

# Using custom database schema
notion-clean clean raw_tasks.txt -s my_schema.json -o ready_for_notion.csv
```

## Schema Structure

A schema JSON file controls validation, normalization, and fallback behavior:

| Key               | Description                                                            |
|-------------------|------------------------------------------------------------------------|
| `expected_columns`| Ordered list of CSV column headers                                     |
| `required_fields` | Columns that must contain a non-empty value                            |
| `valid_containers`| Allowed values for the `Container` column                              |
| `select_mappings` | Per-column normalization rules: `allowed`, `fallbacks`, and `default`  |
| `default_mappings`| Columns that should fall back to another column's value when empty     |

## Notion Import Best Practices

1. Export your Notion database as CSV to use as a template for `init-schema`.
2. Edit the generated schema to add `fallbacks` for common abbreviations or typos.
3. Run `notion-clean clean` on raw exports; the output uses UTF-8-SIG BOM and Unix newlines for maximum compatibility.
4. Import the cleaned CSV into Notion using **Merge with CSV** or **New database**.

## Running Tests

```bash
python -m pytest tests/ -v
```

