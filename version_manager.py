#!/usr/bin/env python

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
from checkers.kubectl import get_telegraf_version, get_mosquitto_version, get_victoriametrics_version, get_calico_version, get_metallb_version, get_alertmanager_version, get_fluentbit_version, get_mongodb_version, get_opensearch_version, get_pgadmin_version
from checkers.postgres import get_cnpg_operator_version, get_postgres_version
from checkers.server_status import check_server_status
from checkers.proxmox import get_proxmox_version, get_proxmox_latest_version
from checkers.tailscale import check_tailscale_versions
from checkers.traefik import get_traefik_version
from checkers.graylog import get_graylog_current_version, get_graylog_latest_version_from_repo, get_postgresql_latest_version_from_ghcr
from checkers.grafana import get_grafana_version
from checkers.mongodb import get_mongodb_latest_version
from checkers.unifi_protect import get_unifi_protect_version
import config

class VersionManager:
    # Constants
    DEFAULT_EXCEL_PATH = config.EXCEL_FILE_PATH
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
            
        check_current = app['Check_Current']
        check_latest = app['Check_Latest']
        repository = app['Repository']
        
        print(f"Checking {display_name}...")
        
        current_version = None
        latest_version = None
        firmware_update_available = False
        
        # Get latest version based on check_latest method
        if check_latest == 'github_release' and repository and pd.notna(repository):
            latest_version = get_github_latest_version(repository)
        elif check_latest == 'github_tag' and repository and pd.notna(repository):
            if app_name == 'MongoDB':
                latest_version = get_mongodb_latest_version()
            elif app_name == 'pgAdmin':
                raw_tag = get_github_latest_tag(repository)
                if raw_tag and raw_tag.startswith('REL-'):
                    # Convert REL-9_8 to 9.8
                    latest_version = raw_tag.replace('REL-', '').replace('_', '.')
                else:
                    latest_version = raw_tag
            else:
                latest_version = get_github_latest_tag(repository)
        elif check_latest == 'docker_hub' and repository and pd.notna(repository):
            # Use Repository field for docker_hub method - no hardcoding
            if app_name == 'Graylog':
                latest_version = get_graylog_latest_version_from_repo(repository)
            elif app_name == 'PostgreSQL':
                latest_version = get_postgresql_latest_version_from_ghcr(repository)
            # No fallback - if docker_hub method fails, we don't get data
        elif check_latest == 'proxmox' and app_name == 'Proxmox VE':
            latest_version = get_proxmox_latest_version()
        elif check_latest == 'opnsense' and app_name == 'OPNsense':
            # OPNsense latest version is handled in the current version check
            pass
        elif check_latest == 'tailscale' and app_name == 'Tailscale':
            # Tailscale latest version is handled in the current version check
            pass
        elif check_latest == 'ssh_apt':
            # SSH-based apt checking for latest available kernel versions
            # This will be populated during the ssh current version check
            pass
        
        # Get current version based on check_current method
        if check_current == 'api':
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
                if check_latest == 'github_tag':
                    # Project version mode - get from Repository
                    project_version = get_konnected_version(instance, None, repository)
                    latest_version = project_version
                    current_version = project_version
                else:
                    current_version = get_konnected_version(instance, url, repository)
            elif app_name == 'Traefik':
                url = app.get('Target')
                current_version = get_traefik_version(instance, url)
            elif app_name == 'OPNsense':
                url = app.get('Target')
                result = get_opnsense_version(instance, url)
                if isinstance(result, dict):
                    current_version = result.get('current_version')
                    firmware_update_available = result.get('firmware_update_available', False)
                    
                    # Use the full_version as the latest version for OPNsense
                    if result.get('full_version'):
                        latest_version = result['full_version']
            elif app_name == 'Proxmox VE':
                url = app.get('Target')
                if url:
                    current_version = get_proxmox_version(instance, url)
            elif app_name == 'Tailscale':
                print("  Checking all Tailscale devices...")
                device_results = check_tailscale_versions(
                    api_key=config.TAILSCALE_API_KEY,
                    tailnet=config.TAILSCALE_TAILNET
                )
                
                if device_results and device_results['total_devices'] > 0:
                    # Use counts from API update availability
                    devices_needing_updates = device_results['devices_needing_updates']
                    devices_up_to_date = device_results['devices_up_to_date']
                    total_devices = device_results['total_devices']
                    
                    # Current version shows count of devices needing updates
                    current_version = f"{devices_needing_updates} need updates"
                    
                    # Latest version shows count of devices up to date  
                    latest_version = f"{devices_up_to_date} up-to-date"
            elif app_name == 'Graylog':
                url = app.get('Target')
                if url:
                    current_version = get_graylog_current_version(instance, url)
            elif app_name == 'UniFi Protect':
                url = app.get('Target')
                if url:
                    current_version = get_unifi_protect_version(instance, url)
        elif check_current == 'kubectl':
            if app_name == 'Telegraf':
                current_version = get_telegraf_version(instance)
            elif app_name == 'VictoriaMetrics':
                current_version = get_victoriametrics_version(instance)
            elif app_name == 'Mosquitto':
                current_version = get_mosquitto_version(instance)
            elif app_name == 'Calico':
                current_version = get_calico_version(instance)
            elif app_name == 'MetalLB':
                current_version = get_metallb_version(instance)
            elif app_name == 'Alertmanager':
                current_version = get_alertmanager_version(instance)
            elif app_name == 'Fluent Bit':
                current_version = get_fluentbit_version(instance)
            elif app_name == 'MongoDB':
                current_version = get_mongodb_version(instance)
            elif app_name == 'OpenSearch':
                current_version = get_opensearch_version(instance)
            elif app_name == 'CloudNativePG':
                current_version = get_cnpg_operator_version(instance)
            elif app_name == 'PostgreSQL':
                current_version = get_postgres_version(instance)
            elif app_name == 'pgAdmin':
                current_version = get_pgadmin_version(instance)
            elif app_name == 'Grafana':
                current_version = get_grafana_version(instance)
            elif app_name == 'K3s':
                current_version = get_k3s_current_version(instance)
        elif check_current == 'mqtt':
            if app_name == 'Zigbee2MQTT':
                current_version = get_zigbee2mqtt_version(instance)
        elif check_current == 'command':
            if app_name == 'Kopia':
                url = app.get('Target')
                current_version = get_kopia_version(instance, url)
        elif check_current == 'ssh':
            # Handle server/hardware Linux version checks via SSH using instance
            server_info = check_server_status(instance, None)
            if server_info:
                # Combine OS name and kernel version for Current_Version
                os_name = server_info['os_name']
                kernel = server_info['kernel']
                current_version = f"{os_name} - {kernel}"
                if check_latest == 'none' or check_latest == 'ssh_apt':
                    raw_latest = server_info.get('latest_kernel', kernel)
                    # For ssh_apt, show user-friendly status instead of kernel version
                    if check_latest == 'ssh_apt':
                        latest_version = raw_latest if raw_latest == "update available" else "No updates"
                    else:
                        latest_version = raw_latest
                
            else:
                current_version = "SSH Failed"
                if check_latest == 'none' or check_latest == 'ssh_apt':
                    latest_version = "Unknown"
        
        # Update notes if firmware update is available (OPNsense specific)
        if firmware_update_available:
            self.df.at[index, 'Notes'] = 'Firmware update available'
        
        # Update DataFrame
        if current_version:
            self.df.at[index, 'Current_Version'] = current_version
        if latest_version:
            self.df.at[index, 'Latest_Version'] = latest_version
        
        # Determine status
        status = "Unknown"
        if current_version and latest_version:
            # Special handling for Tailscale multi-device checking
            if check_current == 'api' and app_name == 'Tailscale':
                # For Tailscale, current_version contains devices needing updates count
                if "0 need updates" in current_version:
                    status = "Up to Date"
                else:
                    status = "Update Available"
            # Special handling for SSH systems with ssh_apt method
            elif check_current == 'ssh' and check_latest == 'ssh_apt':
                # For SSH systems, status is based on whether apt found updates
                if latest_version == "update available":
                    status = "Update Available"
                elif latest_version == "No updates":
                    status = "Up to Date"
                else:
                    status = "Up to Date"
            else:
                # Standard version comparison for other applications
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
            'Current': 55,   # Sized for full OS name + kernel (e.g. "Debian GNU/Linux 12 (bookworm) - 6.12.34+rpt-rpi-2712" = 53 chars + 2)
            'Latest': 22,    # Increased for RPi kernel strings like 6.12.34+rpt-rpi-v8
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