#!/Users/dang/Documents/Development/version-checker/.venv/bin/python
"""One-time importer: Obsidian vault markdown notes -> SQLite applications table.

Read-only against the vault -- never writes or deletes any .md file, so this
can be re-run safely (rows are matched and replaced by (name, instance)).
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

import yaml

from src import db

COLUMNS = [
    "name", "enabled", "context", "namespace", "instance", "type", "category",
    "version_pin", "upgrade", "target", "esphome_key", "github", "dockerhub",
    "current_version", "latest_version", "status", "last_checked", "last_upgraded",
    "check_current", "check_latest", "helm_values_file", "extra_manifests",
    "library_github", "current_library_version", "latest_library_version", "notes",
]


def _parse_note(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}
    return yaml.safe_load(content[4:end]) or {}


def _row_values(frontmatter: dict) -> list:
    values = []
    for col in COLUMNS:
        yaml_key = "esphome key" if col == "esphome_key" else col
        value = frontmatter.get(yaml_key)
        if isinstance(value, (datetime.datetime, datetime.date)):
            # Unquoted timestamps in the YAML (e.g. `last_checked: 2026-04-16 07:41:30`)
            # get auto-parsed into datetime objects by PyYAML; normalize to the same
            # "%Y-%m-%d %H:%M:%S" string format the app itself writes.
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        if col == "enabled":
            value = int(bool(value)) if value is not None else 1
        elif col == "extra_manifests":
            value = json.dumps(value) if value else None
        values.append(value)
    return values


def main():
    parser = argparse.ArgumentParser(description="Migrate Obsidian vault notes into the SQLite database")
    parser.add_argument("--vault", default="/Users/dang/Documents/Goeppedia/Software", help="Path to Obsidian Software vault folder")
    parser.add_argument("--db", default=None, help="Path to SQLite database file (default: from config)")
    args = parser.parse_args()

    vault = Path(args.vault)
    if not vault.is_dir():
        print(f"ERROR: vault folder not found: {vault}")
        sys.exit(1)

    if args.db:
        db_path = Path(args.db)
    else:
        import config
        db_path = Path(config.DATABASE_PATH)

    conn = db.get_connection(db_path)
    db.init_db(conn)

    placeholders = ", ".join("?" for _ in COLUMNS)
    column_list = ", ".join(COLUMNS)

    count = 0
    for md in sorted(vault.glob("*.md")):
        frontmatter = _parse_note(md)
        if not frontmatter.get("name") or not frontmatter.get("instance"):
            print(f"  Skipping {md.name}: missing name/instance")
            continue
        conn.execute(
            f"INSERT OR REPLACE INTO applications (id, {column_list}) "
            f"VALUES ((SELECT id FROM applications WHERE name = ? AND instance = ?), {placeholders})",
            [frontmatter["name"], frontmatter["instance"], *_row_values(frontmatter)],
        )
        count += 1

    conn.commit()
    print(f"Migrated {count} applications into {db_path}")


if __name__ == "__main__":
    main()
