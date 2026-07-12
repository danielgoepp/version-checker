import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    instance TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    context TEXT,
    namespace TEXT,
    type TEXT,
    category TEXT,
    version_pin TEXT,
    upgrade TEXT,
    target TEXT,
    esphome_key TEXT,
    github TEXT,
    dockerhub TEXT,
    current_version TEXT,
    latest_version TEXT,
    status TEXT,
    last_checked TEXT,
    last_upgraded TEXT,
    check_current TEXT,
    check_latest TEXT,
    helm_values_file TEXT,
    extra_manifests TEXT,
    library_github TEXT,
    current_library_version TEXT,
    latest_library_version TEXT,
    notes TEXT,
    UNIQUE(name, instance)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER REFERENCES applications(id),
    name TEXT NOT NULL,
    instance TEXT NOT NULL,
    upgrade_method TEXT,
    from_version TEXT,
    to_version TEXT,
    timestamp TEXT NOT NULL,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # The TUI runs checks/upgrades on a worker thread (Textual's run_worker(thread=True))
    # while this connection is created on the main thread. Usage always alternates
    # rather than overlaps (App.call_from_thread blocks the worker until the main
    # thread finishes), so a single shared connection is safe here.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
