#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

# Import all version checkers
from checkers.github import get_github_latest_version, get_github_latest_tag
from checkers.home_assistant import get_home_assistant_version
from checkers.esphome import get_esphome_version
from checkers.konnected import get_konnected_version
from checkers.opnsense import get_opnsense_version
from checkers.k3s import get_k3s_current_version
from checkers.zigbee2mqtt import get_zigbee2mqtt_version
from checkers.kopia import get_kopia_version
from checkers.kubectl import get_telegraf_version, get_mosquitto_version, get_victoriametrics_version
from checkers.server_status import check_server_status

class VersionManager:
    # Constants
    DEFAULT_EXCEL_PATH = "Goepp Homelab Master.xlsx"
    SHEET_NAME = "Sheet1"
    
    STATUS_ICONS = {
        'Up to Date': '✅',
        'Update Available': '⚠️ ',
        'Latest Available': '📋',
        'Current Version': '📌',
        'Unknown': '❓'
    }
    
    def __init__(self, excel_path=None):
        self.excel_path = excel_path or self.DEFAULT_EXCEL_PATH
        self.df = None
        self.load_excel()
    
    def load_excel(self):
        try:
            self.df = pd.read_excel(self.excel_path, sheet_name=self.SHEET_NAME)
            print(f"Loaded {len(self.df)} applications from Excel")
        except FileNotFoundError:
            print(f"Excel file not found: {self.excel_path}")
            self.df = None
        except Exception as e:
            print(f"Error loading Excel file: {e}")
            self.df = None
    
    def save_excel(self):
        if self.df is None:
            print("No data to save")
            return
        try:
            with pd.ExcelWriter(self.excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                self.df.to_excel(writer, sheet_name=self.SHEET_NAME, index=False)
            print("Excel file updated successfully")
        except Exception as e:
            print(f"Error saving Excel file: {e}")
    
    def check_single_application(self, index):
        """Check version for a single application by index"""
        app = self.df.iloc[index]
        
        # Use current Name/Instance structure
        app_name = app['Name']
        instance = app['Instance']
        display_name = f"{app_name}" if instance == 'prod' else f"{app_name}-{instance}"
            
        check_method = app['Check_Method']
        github_repo = app['GitHub']
        
        print(f"Checking {display_name}...")
        
        current_version = None
        latest_version = None
        
        # Get latest version (mostly from GitHub)
        if github_repo and pd.notna(github_repo):
            if check_method == 'kubectl_tags':
                latest_version = get_github_latest_tag(github_repo)
            else:
                latest_version = get_github_latest_version(github_repo)
        
        # Get current version based on check method
        if check_method == 'api_github':
            if app_name == 'Home Assistant':
                url = app.get('Target')
                if url:
                    current_version = get_home_assistant_version(instance, url)
            elif app_name == 'ESPHome':
                url = app.get('Target')
                if url:
                    current_version = get_esphome_version(url)
            elif app_name == 'Konnected':
                url = app.get('Target')
                github_repo = app.get('GitHub')
                current_version = get_konnected_version(instance, url, github_repo)
        elif check_method == 'k8s_api_github':
            if app_name == 'K3s':
                current_version = get_k3s_current_version(instance)
        elif check_method == 'mqtt_github':
            if app_name == 'Zigbee2MQTT':
                current_version = get_zigbee2mqtt_version(instance)
        elif check_method == 'command_github':
            if app_name == 'Kopia':
                url = app.get('Target')
                current_version = get_kopia_version(instance, url)
        elif check_method == 'api_custom':
            if app_name == 'OPNsense':
                url = app.get('Target')
                result = get_opnsense_version(instance, url)
                if isinstance(result, dict):
                    current_version = result.get('current_version')
                    firmware_update_available = result.get('firmware_update_available', False)
                    
                    # Use the full_version as the latest version for OPNsense
                    if result.get('full_version'):
                        latest_version = result['full_version']
                    
                    # Store detailed information in Update_Details only
                    if result.get('update_details'):
                        self.df.at[index, 'Update_Details'] = result['update_details']
                    
                    # Update notes if firmware update is available
                    if firmware_update_available:
                        self.df.at[index, 'Notes'] = 'Firmware update available'
        elif check_method == 'project_version':
            if app_name == 'Konnected':
                github_repo = app.get('GitHub')
                project_version = get_konnected_version(instance, None, github_repo)
                latest_version = project_version
                current_version = project_version
        elif check_method == 'kubectl_github':
            if app_name == 'Telegraf':
                current_version = get_telegraf_version(instance)
            elif app_name == 'VictoriaMetrics':
                current_version = get_victoriametrics_version(instance)
            elif app_name == 'Mosquitto':
                current_version = get_mosquitto_version(instance)
        elif check_method == 'kubectl_only':
            if app_name == 'Mosquitto':
                current_version = get_mosquitto_version(instance)
                latest_version = None
        elif check_method == 'kubectl_tags':
            if app_name == 'Mosquitto':
                current_version = get_mosquitto_version(instance)
        elif check_method == 'server_status':
            # Handle server/hardware Linux version checks via SSH
            target = app.get('Target')
            if target:
                server_info = check_server_status(instance, target)
                if server_info:
                    # Use kernel version as the "version" to track
                    current_version = server_info['kernel']
                    latest_version = server_info.get('latest_kernel', server_info['kernel'])
                    
                    # Update Category with the OS name
                    self.df.at[index, 'Category'] = server_info['os_name']
                    
                    # Store full display info in Update_Details
                    display_info = server_info['display_info']
                    if latest_version and latest_version != current_version:
                        display_info += f" | Latest: {latest_version}"
                    self.df.at[index, 'Update_Details'] = display_info
                else:
                    current_version = "SSH Failed"
                    latest_version = "Unknown"
        
        # Update DataFrame
        if current_version:
            self.df.at[index, 'Current_Version'] = current_version
        if latest_version:
            self.df.at[index, 'Latest_Version'] = latest_version
        
        # Determine status
        status = "Unknown"
        if current_version and latest_version:
            # For Kopia, extract just the version number for comparison
            current_clean = current_version
            if "build:" in current_version:
                current_clean = current_version.split("build:")[0].strip()
            
            # Remove 'v' prefix if present in latest_version
            latest_clean = latest_version
            if latest_clean.startswith("v"):
                latest_clean = latest_clean[1:]
            
            if current_clean == latest_clean:
                status = "Up to Date"
            else:
                status = "Update Available"
        elif latest_version and not current_version:
            status = "Latest Available"
        elif current_version and not latest_version:
            status = "Current Version"
        
        self.df.at[index, 'Status'] = status
        self.df.at[index, 'Last_Checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        icon = self.STATUS_ICONS.get(status, '')
        print(f"  Current: {current_version or 'N/A'}")
        print(f"  Latest: {latest_version or 'N/A'}")
        print(f"  Status: {icon} {status}")
        print()
    
    def check_all_applications(self):
        """Check versions for all applications"""
        print("Starting version check for all applications...")
        print("=" * 50)
        
        for index in range(len(self.df)):
            self.check_single_application(index)
        
        self.save_excel()
        print("Version check completed!")
    
    def show_summary(self):
        """Display a summary of version status"""
        if self.df is None:
            print("No data loaded")
            return
        
        print("\nVersion Summary:")
        print("=" * 40)
        
        status_counts = self.df['Status'].value_counts()
        for status, count in status_counts.items():
            icon = self.STATUS_ICONS.get(status, '')
            print(f"{icon} {status}: {count}")
        
        print(f"\nTotal Applications: {len(self.df)}")
        
        # Show outdated applications
        outdated = self.df[self.df['Status'] == 'Update Available']
        if not outdated.empty:
            print(f"\n⚠️  Applications needing updates:")
            for _, app in outdated.iterrows():
                app_display = f"{app['Name']}-{app['Instance']}" if app['Instance'] != 'prod' else app['Name']
                print(f"  {app_display}: {app['Current_Version']} -> {app['Latest_Version']}")
    
    def show_applications(self):
        """Show all applications in a formatted table"""
        if self.df is None:
            print("No data loaded")
            return
        
        # Create a copy with status icons
        display_df = self.df.copy()
        
        # Just use icons for status - no text
        display_df['Status'] = display_df['Status'].map(lambda x: self.STATUS_ICONS.get(x, x) if pd.notna(x) else x)
        
        # Rename columns for display
        display_df = display_df.rename(columns={
            'Current_Version': 'Current',
            'Latest_Version': 'Latest'
        })
        
        # Select key columns for display
        display_cols = ['Name', 'Instance', 'Current', 'Latest', 'Last_Checked', 'Status']
        
        # Only show columns that exist
        existing_cols = [col for col in display_cols if col in display_df.columns]
        
        # Manual formatting with fixed column widths for perfect alignment
        col_widths = {
            'Name': 18,
            'Instance': 22,  # Sized for longest instance name (vms-prod-lt-vmsingle = 20 chars + padding)
            'Current': 12,
            'Latest': 12,
            'Last_Checked': 20,  # Increased for full timestamp display
            'Status': 3  # Just icons, small width
        }
        
        # Print header
        header_parts = []
        for col in existing_cols:
            width = col_widths.get(col, 15)
            header_parts.append(col.ljust(width))
        print(''.join(header_parts))
        
        # Print rows
        for _, row in display_df[existing_cols].iterrows():
            row_parts = []
            for col in existing_cols:
                width = col_widths.get(col, 15)
                value = str(row[col]) if pd.notna(row[col]) else ''
                # Handle NaN values
                if value == 'nan':
                    value = ''
                # Simple truncate and pad
                if len(value) > width:
                    value = value[:width-3] + '...'
                row_parts.append(value.ljust(width))
            print(''.join(row_parts))

def main():
    vm = VersionManager()
    
    if vm.df is None:
        return
    
    print("Goepp Homelab Version Manager")
    print("========================")
    
    while True:
        print("\nOptions:")
        print("1. Check all applications")
        print("2. Check single application") 
        print("3. Show summary")
        print("4. Show all applications")
        print("5. Quit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            vm.check_all_applications()
        elif choice == '2':
            vm.show_applications()
            try:
                index = int(input("Enter application number (0-based): "))
                if 0 <= index < len(vm.df):
                    vm.check_single_application(index)
                    vm.save_excel()
                else:
                    print("Invalid index")
            except ValueError:
                print("Please enter a valid number")
        elif choice == '3':
            vm.show_summary()
        elif choice == '4':
            vm.show_applications()
        elif choice == '5':
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()