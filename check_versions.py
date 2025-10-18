#!/Users/dang/Documents/Development/version-checker/.venv/bin/python

import argparse
import sys

# Suppress urllib3 OpenSSL warning before importing anything that uses requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from version_manager import VersionManager
from config import EXCEL_FILE_PATH

def main():
    parser = argparse.ArgumentParser(description='Goepp Homelab Version Manager')
    parser.add_argument('--excel', default=EXCEL_FILE_PATH, 
                       help=f'Path to Excel file (default: {EXCEL_FILE_PATH})')
    parser.add_argument('--check-all', action='store_true',
                       help='Check all applications and exit')
    parser.add_argument('--summary', action='store_true',
                       help='Show summary and exit')
    parser.add_argument('--list', action='store_true',
                       help='List all applications and exit')
    parser.add_argument('--app', type=str,
                       help='Check specific application by name')
    
    args = parser.parse_args()
    
    vm = VersionManager(args.excel)
    
    if vm.workbook is None:
        print("Failed to load Excel file. Check file path and permissions.")
        sys.exit(1)
    
    if args.check_all:
        vm.check_all_applications()
    elif args.summary:
        vm.show_summary()
    elif args.list:
        vm.show_applications()
    elif args.app:
        # Find application by name using openpyxl
        if 'Name' not in vm.columns:
            print("Error: 'Name' column not found in Excel file")
            sys.exit(1)
            
        matching_rows = []
        for row_num in range(2, vm.worksheet.max_row + 1):
            name_cell = vm.worksheet[f"{vm.columns['Name']}{row_num}"]
            if name_cell.value and name_cell.value.lower() == args.app.lower():
                matching_rows.append(row_num)
        
        if not matching_rows:
            print(f"Application '{args.app}' not found")
            print("Available applications:")
            for row_num in range(2, vm.worksheet.max_row + 1):
                name_cell = vm.worksheet[f"{vm.columns['Name']}{row_num}"]
                if name_cell.value:
                    print(f"  {name_cell.value}")
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