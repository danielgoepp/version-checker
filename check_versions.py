#!/usr/bin/env python3

import argparse
import sys

# Suppress urllib3 OpenSSL warning before importing anything that uses requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from version_manager import VersionManager

def main():
    parser = argparse.ArgumentParser(description='Goepp Homelab Version Manager')
    parser.add_argument('--excel', default='Goepp Homelab Master.xlsx', 
                       help='Path to Excel file (default: Goepp Homelab Master.xlsx)')
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
    
    if vm.df is None:
        print("Failed to load Excel file. Run create_excel.py first.")
        sys.exit(1)
    
    if args.check_all:
        vm.check_all_applications()
    elif args.summary:
        vm.show_summary()
    elif args.list:
        vm.show_applications()
    elif args.app:
        # Find application by name
        app_mask = vm.df['Name'].str.lower() == args.app.lower()
        app_col = 'Name'
        
        matching_apps = vm.df[app_mask]
        
        if matching_apps.empty:
            print(f"Application '{args.app}' not found")
            print("Available applications:")
            for app in vm.df[app_col].values:
                print(f"  {app}")
            sys.exit(1)
        
        # Check all matching instances
        for index in matching_apps.index:
            vm.check_single_application(index)
        vm.save_excel()
    else:
        # Interactive mode
        from version_manager import main as interactive_main
        interactive_main()

if __name__ == "__main__":
    main()