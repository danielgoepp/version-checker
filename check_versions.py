#!/Users/dang/Documents/Development/version-checker/.venv/bin/python
# PYTHON_ARGCOMPLETE_OK

import argparse
import os
import sys
from pathlib import Path

# Suppress urllib3 OpenSSL warning before importing anything that uses requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)


def _db_path() -> Path:
    default = str(Path(__file__).parent / "data" / "version_checker.db")
    return Path(os.environ.get("DATABASE_PATH", default))


def _fetch_name_instance_pairs() -> list[tuple[str, str]]:
    import sqlite3
    db_path = _db_path()
    if not db_path.is_file():
        return []
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT DISTINCT name, instance FROM applications").fetchall()
    finally:
        conn.close()


def _app_completer(prefix, parsed_args, **kwargs):
    names = {name for name, _ in _fetch_name_instance_pairs()}
    return [n for n in sorted(names) if n.startswith(prefix)]


def _instance_completer(prefix, parsed_args, **kwargs):
    app = getattr(parsed_args, "app", None)
    instances = [
        instance for name, instance in _fetch_name_instance_pairs()
        if app is None or name == app
    ]
    return [i for i in sorted(set(instances)) if i.startswith(prefix)]


def main():
    parser = argparse.ArgumentParser(description="Goepp Homelab Version Manager")
    parser.add_argument(
        "--db",
        default=None,
        help="Path to SQLite database file (default: from config)",
    )
    parser.add_argument(
        "--check-all", action="store_true", help="Check all applications and exit"
    )
    parser.add_argument("--summary", action="store_true", help="Show summary and exit")
    parser.add_argument(
        "--list", action="store_true", help="List all applications and exit"
    )
    parser.add_argument(
        "--updates",
        action="store_true",
        help="List only applications with updates available and exit",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help=(
            "Show upgrade history from the transactions table and exit "
            "(most recent 40; use --app/--instance to filter)"
        ),
    )
    app_arg = parser.add_argument("--app", type=str, help="Check specific application by name")
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help=(
            "Upgrade the application specified by --app. "
            "For version_pin='latest': triggers an AWX job directly. "
            "For version_pin='pinned': updates the k3s manifest file first, then triggers AWX."
        ),
    )
    instance_arg = parser.add_argument(
        "--instance",
        type=str,
        default="",
        help="Filter to a specific instance (use with --app)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Force AWX trigger even if already up to date or manifest unchanged. "
            "For version_pin='pinned': skips manifest update and goes straight to AWX."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making any changes (use with --app --upgrade)",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch the interactive terminal UI",
    )

    try:
        import argcomplete
        app_arg.completer = _app_completer
        instance_arg.completer = _instance_completer
        argcomplete.autocomplete(parser, exclude=["--"])
    except ImportError:
        pass

    args = parser.parse_args()

    from version_manager import VersionManager

    vm = VersionManager(args.db)

    if not vm.notes:
        print("Failed to load application data. Check the database path and permissions.")
        sys.exit(1)

    if args.tui:
        from src.tui.app import run_tui

        run_tui(vm)
    elif args.check_all:
        vm.check_all_applications()
    elif args.summary:
        vm.show_summary()
    elif args.list:
        vm.show_applications()
    elif args.updates:
        vm.show_updates()
    elif args.history:
        vm.show_history(name=args.app or "", instance=args.instance)
    elif args.app:
        if args.upgrade:
            label = f"'{args.app}'" + (f" (instance: {args.instance})" if args.instance else "")
            if args.dry_run:
                print(f"[DRY RUN] Upgrade requested for {label}")
            else:
                print(f"Upgrade requested for {label}")
            print()
            vm.upgrade_application(args.app, dry_run=args.dry_run, instance=args.instance, force=args.force)
        else:
            matching = vm.find_application_rows_by_name(args.app, instance=args.instance)

            if not matching:
                print(f"Application '{args.app}' not found")
                print("Available applications:")
                for name in vm.get_all_application_names():
                    print(f"  {name}")
                sys.exit(1)

            unavailable = []
            for idx in matching:
                label = vm.check_single_application(idx)
                if label:
                    unavailable.append(label)
            if len(matching) > 1 and unavailable:
                print(f"❓ Current version unavailable for {len(unavailable)} application(s):")
                for label in unavailable:
                    print(f"  {label}")
    elif args.upgrade:
        print("--upgrade requires --app")
        parser.print_help()
        sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
