#!/Users/dang/Documents/Development/version-checker/.venv/bin/python

import argparse
import sys

# Suppress urllib3 OpenSSL warning before importing anything that uses requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from version_manager import VersionManager


def main():
    parser = argparse.ArgumentParser(description="Goepp Homelab Version Manager")
    parser.add_argument(
        "--vault",
        default=None,
        help="Path to Obsidian Software vault folder (default: from config)",
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
    parser.add_argument("--app", type=str, help="Check specific application by name")
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Maximum concurrent workers for --check-all (default: 10)",
    )
    parser.add_argument(
        "--upgrade",
        type=str,
        metavar="APP_NAME",
        help=(
            "Upgrade a specific application. "
            "For version_pin='latest': triggers an AWX job directly. "
            "For version_pin='pinned': updates the k3s manifest file first, then triggers AWX."
        ),
    )
    parser.add_argument(
        "--instance",
        type=str,
        default="",
        help="Filter to a specific instance (use with --upgrade or --app)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making any changes (use with --upgrade)",
    )

    args = parser.parse_args()

    vm = VersionManager(args.vault)

    if not vm.notes:
        print("Failed to load vault notes. Check vault path and permissions.")
        sys.exit(1)

    if args.check_all:
        vm.check_all_applications(max_workers=args.workers)
    elif args.summary:
        vm.show_summary()
    elif args.list:
        vm.show_applications()
    elif args.updates:
        vm.show_updates()
    elif args.app:
        matching = vm.find_application_rows_by_name(args.app, instance=args.instance)

        if not matching:
            print(f"Application '{args.app}' not found")
            print("Available applications:")
            for name in vm.get_all_application_names():
                print(f"  {name}")
            sys.exit(1)

        for idx in matching:
            vm.check_single_application(idx)
    elif args.upgrade:
        if args.dry_run:
            print(f"[DRY RUN] Upgrade requested for '{args.upgrade}'" + (f" (instance: {args.instance})" if args.instance else ""))
        else:
            print(f"Upgrade requested for '{args.upgrade}'" + (f" (instance: {args.instance})" if args.instance else ""))
        print()
        vm.upgrade_application(args.upgrade, dry_run=args.dry_run, instance=args.instance)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
