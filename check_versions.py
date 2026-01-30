#!/Users/dang/Documents/Development/version-checker/.venv/bin/python

import argparse
import sys

# Suppress urllib3 OpenSSL warning before importing anything that uses requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from version_manager import VersionManager
from config import EXCEL_FILE_PATH


def main():
    parser = argparse.ArgumentParser(description="Goepp Homelab Version Manager")
    parser.add_argument(
        "--excel",
        default=EXCEL_FILE_PATH,
        help=f"Path to Excel file (default: {EXCEL_FILE_PATH})",
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

    args = parser.parse_args()

    vm = VersionManager(args.excel)

    if vm.workbook is None:
        print("Failed to load Excel file. Check file path and permissions.")
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
        # Find application by name using VersionManager methods
        matching_rows = vm.find_application_rows_by_name(args.app)

        if not matching_rows:
            print(f"Application '{args.app}' not found")
            print("Available applications:")
            for name in vm.get_all_application_names():
                print(f"  {name}")
            sys.exit(1)

        # Check all matching instances
        for row_num in matching_rows:
            vm.check_single_application(row_num)
        vm.save_workbook()
    else:
        # Interactive mode
        from version_manager import main as interactive_main

        interactive_main()


if __name__ == "__main__":
    main()
