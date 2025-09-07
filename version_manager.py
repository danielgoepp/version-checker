#!/usr/bin/env python

from datetime import datetime
import urllib3
from openpyxl import load_workbook
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
from checkers.kubectl import get_telegraf_version, get_mosquitto_version, get_victoriametrics_version, get_calico_version, get_metallb_version, get_alertmanager_version, get_fluentbit_version, get_mongodb_version, get_opensearch_version, get_pgadmin_version, get_unpoller_version, get_certmanager_version, get_postfix_version, get_hertzbeat_kubectl_version
from checkers.postgres import get_cnpg_operator_version, get_postgres_version
from checkers.server_status import check_server_status
from checkers.proxmox import get_proxmox_version, get_proxmox_latest_version
from checkers.tailscale import check_tailscale_versions
from checkers.traefik import get_traefik_version
from checkers.graylog import get_graylog_current_version, get_graylog_latest_version_from_repo, get_postgresql_latest_version_from_ghcr
from checkers.grafana import get_grafana_version
from checkers.mongodb import get_mongodb_latest_version
from checkers.unifi_protect import get_unifi_protect_version
from checkers.unifi_network import get_unifi_network_version
from checkers.samba import get_samba_version, get_latest_samba_version
from checkers.syncthing import check_syncthing_current_version
from checkers.awx import check_awx_current_version
from checkers.postfix import get_postfix_latest_version_from_dockerhub
from checkers.dockerhub import get_dockerhub_latest_version
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
    
    # Expected column names (order-independent)
    EXPECTED_COLUMNS = [
        'Name', 'Instance', 'Type', 'Category', 'Target', 
        'GitHub', 'DockerHub', 'Current_Version', 'Latest_Version', 
        'Status', 'Last_Checked', 'Check_Current', 'Check_Latest'
    ]
    
    def __init__(self, excel_path=None):
        self.excel_path = excel_path or self.DEFAULT_EXCEL_PATH
        self.workbook = None
        self.worksheet = None
        self.columns = {}  # Dynamic column mapping
        self.load_workbook()
    
    def load_workbook(self):
        """Load Excel workbook using openpyxl and map columns dynamically"""
        try:
            self.workbook = load_workbook(self.excel_path)
            self.worksheet = self.workbook[self.SHEET_NAME]
            
            # Read header row and create dynamic column mapping
            self._map_columns()
            
            # Count applications (excluding header row)
            app_count = self.worksheet.max_row - 1 if self.worksheet.max_row > 1 else 0
            print(f"Loaded {app_count} applications from Excel")
        except FileNotFoundError:
            print(f"Excel file not found: {self.excel_path}")
            self.workbook = None
            self.worksheet = None
            self.columns = {}
        except Exception as e:
            print(f"Error loading Excel file: {e}")
            self.workbook = None
            self.worksheet = None
            self.columns = {}
    
    def _map_columns(self):
        """Create dynamic column mapping by reading header row"""
        self.columns = {}
        if not self.worksheet:
            return
            
        # Read header row (row 1) and map column names to letters
        for col_num in range(1, self.worksheet.max_column + 1):
            col_letter = chr(ord('A') + col_num - 1)
            header_cell = self.worksheet[f'{col_letter}1']
            
            if header_cell.value:
                column_name = str(header_cell.value).strip()
                self.columns[column_name] = col_letter
        
        # Verify all expected columns are present
        missing_columns = []
        for expected_col in self.EXPECTED_COLUMNS:
            if expected_col not in self.columns:
                missing_columns.append(expected_col)
        
        if missing_columns:
            print(f"Warning: Missing columns in Excel file: {missing_columns}")
            print(f"Found columns: {list(self.columns.keys())}")
    
    def save_workbook(self):
        """Save workbook preserving all formatting"""
        if self.workbook is None:
            print("No workbook to save")
            return
        try:
            self.workbook.save(self.excel_path)
            print("Excel file updated successfully (formatting preserved)")
        except Exception as e:
            print(f"Error saving Excel file: {e}")

    def get_row_data(self, row_num):
        """Get all data for a specific row"""
        if self.worksheet is None or row_num < 2:
            return None
        
        data = {}
        for col_name, col_letter in self.columns.items():
            cell = self.worksheet[f'{col_letter}{row_num}']
            data[col_name] = cell.value if cell.value is not None else ''
        
        return data
    
    def update_row_data(self, row_num, updates):
        """Update specific columns in a row"""
        if self.worksheet is None:
            return
        
        for col_name, value in updates.items():
            if col_name in self.columns:
                col_letter = self.columns[col_name]
                self.worksheet[f'{col_letter}{row_num}'] = value
    
    def find_application_row(self, app_name, instance='prod'):
        """Find the row number for a specific application and instance"""
        if self.worksheet is None or 'Name' not in self.columns or 'Instance' not in self.columns:
            return None
        
        for row_num in range(2, self.worksheet.max_row + 1):
            name_cell = self.worksheet[f"{self.columns['Name']}{row_num}"]
            instance_cell = self.worksheet[f"{self.columns['Instance']}{row_num}"]
            
            if (name_cell.value and name_cell.value.lower() == app_name.lower() and
                instance_cell.value and instance_cell.value.lower() == instance.lower()):
                return row_num
        return None
    
    def get_latest_version(self, app_name, check_latest, github_repo, dockerhub_repo):
        """Get latest version based on check_latest method, preferring Docker Hub when available"""
        latest_version = None
        
        # PREFERENCE: Docker Hub over GitHub when both are available
        if check_latest == 'github_release' or check_latest == 'github_tag':
            # Check if Docker Hub is also available - if so, prefer it
            if dockerhub_repo and dockerhub_repo.strip():
                print(f"  Found both GitHub ({github_repo}) and Docker Hub ({dockerhub_repo}) - preferring Docker Hub")
                if app_name == 'MongoDB':
                    latest_version = get_mongodb_latest_version()
                elif app_name == 'Graylog':
                    if 'graylog' in dockerhub_repo.lower():
                        latest_version = get_graylog_latest_version_from_repo(dockerhub_repo)
                    elif 'postgres' in dockerhub_repo.lower():
                        latest_version = get_postgresql_latest_version_from_ghcr(dockerhub_repo)
                    elif 'postfix' in dockerhub_repo.lower():
                        latest_version = get_postfix_latest_version_from_dockerhub(dockerhub_repo)
                    else:
                        latest_version = get_dockerhub_latest_version(dockerhub_repo)
                else:
                    latest_version = get_dockerhub_latest_version(dockerhub_repo)
            # Fall back to GitHub if Docker Hub not available or failed
            elif not latest_version and github_repo and github_repo.strip():
                if check_latest == 'github_release':
                    latest_version = get_github_latest_version(github_repo)
                elif check_latest == 'github_tag':
                    latest_version = get_github_latest_tag(github_repo)
        elif check_latest == 'docker_hub':
            if app_name == 'MongoDB':
                latest_version = get_mongodb_latest_version()
            elif dockerhub_repo and dockerhub_repo.strip():
                if app_name == 'Graylog':
                    if 'graylog' in dockerhub_repo.lower():
                        latest_version = get_graylog_latest_version_from_repo(dockerhub_repo)
                    elif 'postgres' in dockerhub_repo.lower():
                        latest_version = get_postgresql_latest_version_from_ghcr(dockerhub_repo)
                    elif 'postfix' in dockerhub_repo.lower():
                        latest_version = get_postfix_latest_version_from_dockerhub(dockerhub_repo)
                else:
                    latest_version = get_dockerhub_latest_version(dockerhub_repo)
        elif check_latest == 'proxmox':
            latest_version = get_proxmox_latest_version(include_ceph=True)
        # ssh_apt method - latest version will be populated during ssh current check
        
        return latest_version

    def get_current_version(self, app_data):
        """Get current version based on check_current method"""
        app_name = app_data.get('Name', '')
        instance = app_data.get('Instance', 'prod')
        check_current = app_data.get('Check_Current', '')
        check_latest = app_data.get('Check_Latest', '')
        url = app_data.get('Target', '')
        github_repo = app_data.get('GitHub', '')
        
        current_version = None
        latest_version = None
        firmware_update_available = False
        
        # Get current version based on check_current method
        if check_current == 'api':
            if app_name == 'Home Assistant':
                if url:
                    current_version = get_home_assistant_version(instance, url)
            elif app_name == 'ESPHome':
                if url:
                    current_version = get_esphome_version(url)
            elif app_name == 'Konnected':
                if check_latest == 'github_tag':
                    # Project version mode - get from GitHub repository
                    project_version = get_konnected_version(instance, None, github_repo)
                    latest_version = project_version
                    current_version = project_version
                else:
                    current_version = get_konnected_version(instance, url, github_repo)
            elif app_name == 'Traefik':
                current_version = get_traefik_version(instance, url)
            elif app_name == 'OPNsense':
                result = get_opnsense_version(instance, url)
                if isinstance(result, dict):
                    current_version = result.get('current_version')
                    firmware_update_available = result.get('firmware_update_available', False)
                    
                    # Use the full_version as the latest version for OPNsense
                    if result.get('full_version'):
                        latest_version = result['full_version']
            elif app_name == 'Proxmox VE':
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
                    
                    # Current version shows count of devices needing updates
                    current_version = f"{devices_needing_updates} need updates"
                    
                    # Latest version shows count of devices up to date  
                    latest_version = f"{devices_up_to_date} up-to-date"
            elif app_name == 'Graylog':
                if url:
                    current_version = get_graylog_current_version(instance, url)
            elif app_name == 'UniFi Protect':
                if url:
                    current_version = get_unifi_protect_version(instance, url)
            elif app_name == 'UniFi Network':
                if url:
                    current_version = get_unifi_network_version(instance, url)
            # Add more API-based applications here as needed
        
        elif check_current == 'ssh':
            if check_latest == 'ssh_apt':
                # SSH with kernel checking - this will set both current and latest versions
                kernel_result = check_server_status(instance, url)
                if isinstance(kernel_result, dict):
                    current_version = kernel_result.get('current_version')
                    latest_version = kernel_result.get('latest_version')
        
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
            elif app_name == 'UnPoller':
                current_version = get_unpoller_version(instance)
            elif app_name == 'cert-manager':
                current_version = get_certmanager_version(instance)
            elif app_name == 'K3s':
                current_version = get_k3s_current_version(instance)
            elif app_name == 'Postfix':
                current_version = get_postfix_version(instance)
            elif app_name == 'HertzBeat':
                current_version = get_hertzbeat_kubectl_version(instance)
        
        elif check_current == 'mqtt':
            if app_name == 'Zigbee2MQTT':
                current_version = get_zigbee2mqtt_version(instance)
        
        elif check_current == 'command':
            if app_name == 'Kopia':
                current_version = get_kopia_version(instance, url)
            elif app_name == 'Syncthing':
                current_version = check_syncthing_current_version(instance)
            elif app_name == 'Samba':
                current_version = get_samba_version(instance, url)
                if check_latest == 'ssh_apt':
                    latest_version = get_latest_samba_version(instance)
            elif app_name == 'AWX':
                current_version = check_awx_current_version(instance)
        
        return current_version, latest_version, firmware_update_available

    def check_single_application(self, row_num):
        """Check version for a single application by row number"""
        if self.worksheet is None:
            print("No worksheet loaded")
            return
        
        app_data = self.get_row_data(row_num)
        if not app_data:
            return
            
        app_name = app_data.get('Name', '')
        instance = app_data.get('Instance', 'prod')
        check_current = app_data.get('Check_Current', '')
        check_latest = app_data.get('Check_Latest', '')
        github_repo = app_data.get('GitHub', '')
        dockerhub_repo = app_data.get('DockerHub', '')
        
        print(f"Checking {app_name} ({instance})...")
        
        # Get latest version
        latest_version = self.get_latest_version(app_name, check_latest, github_repo, dockerhub_repo)
        
        # Get current version (and possibly additional latest version from SSH methods)
        current_version, ssh_latest_version, firmware_update_available = self.get_current_version(app_data)
        
        # For SSH-based methods, use the latest version from the SSH check if available
        if ssh_latest_version:
            latest_version = ssh_latest_version
        
        # Update timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare updates
        updates = {'Last_Checked': timestamp}
        
        if current_version:
            updates['Current_Version'] = current_version
        if latest_version:
            updates['Latest_Version'] = latest_version
        
        # Update notes if firmware update is available (OPNsense specific)
        if firmware_update_available:
            updates['Notes'] = 'Firmware update available'
        
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
        
        updates['Status'] = status
        
        # Update the Excel row
        self.update_row_data(row_num, updates)
        
        # Display results
        current_display = current_version if current_version else "N/A"
        latest_display = latest_version if latest_version else "N/A"
        icon = self.STATUS_ICONS.get(status, '')
        
        print(f"  Current: {current_display}")
        print(f"  Latest: {latest_display}")
        print(f"  Status: {icon} {status}")
        print()
    
    def check_all_applications(self):
        """Check versions for all applications"""
        if self.worksheet is None:
            print("No worksheet loaded")
            return
            
        print("Starting version check for all applications...")
        print("=" * 50)
        
        for row_num in range(2, self.worksheet.max_row + 1):
            self.check_single_application(row_num)
        
        self.save_workbook()
        print("Version check completed!")
    
    def show_summary(self):
        """Display a summary of version status"""
        if self.worksheet is None:
            print("No worksheet loaded")
            return
        
        print("\nVersion Summary:")
        print("=" * 40)
        
        # Count statuses
        status_counts = {}
        total_apps = 0
        
        for row_num in range(2, self.worksheet.max_row + 1):
            if 'Status' in self.columns:
                status_cell = self.worksheet[f"{self.columns['Status']}{row_num}"]
                status = status_cell.value if status_cell.value else "Unknown"
                status_counts[status] = status_counts.get(status, 0) + 1
            total_apps += 1
        
        for status, count in status_counts.items():
            icon = self.STATUS_ICONS.get(status, '')
            print(f"{icon} {status}: {count}")
        
        print(f"\nTotal Applications: {total_apps}")
        
        # Show outdated applications
        print(f"\n⚠️  Applications needing updates:")
        if all(col in self.columns for col in ['Status', 'Name', 'Instance', 'Current_Version', 'Latest_Version']):
            for row_num in range(2, self.worksheet.max_row + 1):
                status_cell = self.worksheet[f"{self.columns['Status']}{row_num}"]
                if status_cell.value == 'Update Available':
                    name_cell = self.worksheet[f"{self.columns['Name']}{row_num}"]
                    instance_cell = self.worksheet[f"{self.columns['Instance']}{row_num}"]
                    current_cell = self.worksheet[f"{self.columns['Current_Version']}{row_num}"]
                    latest_cell = self.worksheet[f"{self.columns['Latest_Version']}{row_num}"]
                    
                    name = name_cell.value if name_cell.value else ""
                    instance = instance_cell.value if instance_cell.value else ""
                    current = current_cell.value if current_cell.value else "N/A"
                    latest = latest_cell.value if latest_cell.value else "N/A"
                    
                    app_display = f"{name}-{instance}" if instance != 'prod' else name
                    print(f"  {app_display}: {current} -> {latest}")
        else:
            print("  Unable to show updates - missing required columns")
    
    def show_applications(self):
        """Show all applications in a formatted table"""
        if self.worksheet is None:
            print("No worksheet loaded")
            return
        
        print("\nApplications:")
        print("=" * 120)
        
        # Print header
        print(f"{'#':<4} {'Name':<20} {'Instance':<12} {'Type':<18} {'Current':<15} {'Latest':<15} {'Status':<8} {'Target':<30}")
        print("-" * 120)
        
        # Print each row
        index = 0
        for row_num in range(2, self.worksheet.max_row + 1):
            row_data = self.get_row_data(row_num)
            
            name = row_data.get('Name', '')[:19] if row_data.get('Name') else ''
            instance = row_data.get('Instance', '')[:11] if row_data.get('Instance') else ''
            app_type = row_data.get('Type', '')[:17] if row_data.get('Type') else ''
            current = row_data.get('Current_Version', '')[:14] if row_data.get('Current_Version') else ''
            latest = row_data.get('Latest_Version', '')[:14] if row_data.get('Latest_Version') else ''
            status = row_data.get('Status', '')
            target = row_data.get('Target', '')[:29] if row_data.get('Target') else ''
            
            # Get status icon
            status_icon = self.STATUS_ICONS.get(status, '') if status else ''
            
            print(f"{index:<4} {name:<20} {instance:<12} {app_type:<18} {current:<15} {latest:<15} {status_icon:<8} {target:<30}")
            index += 1

def main():
    """Main interactive interface"""
    vm = VersionManager()
    
    while True:
        print("\n" + "="*50)
        print("Version Checker Management System")
        print("="*50)
        print("1. Check all applications")
        print("2. Check single application")
        print("3. Show summary")
        print("4. List all applications")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            vm.check_all_applications()
        elif choice == '2':
            vm.show_applications()
            try:
                index = int(input("Enter application number (0-based): "))
                row_num = index + 2  # Convert to Excel row number
                if 2 <= row_num <= vm.worksheet.max_row:
                    vm.check_single_application(row_num)
                    vm.save_workbook()
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
            print("Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()