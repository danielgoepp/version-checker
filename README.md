# Goepp Homelab Version Manager

A comprehensive Python-based system for tracking software versions across your infrastructure using Excel for data management.

## Features

- **Excel Integration**: Uses "Goepp Homelab Master.xlsx" with Name/Instance structure
- **Multi-Instance Support**: Track multiple instances of the same application (e.g., Kopia nodes)
- **Multiple Check Methods**: 
  - GitHub API for latest releases
  - Local API calls (Home Assistant, Kubernetes)
  - MQTT messaging (Zigbee2MQTT)
  - Command execution (Kopia backup servers)
- **Visual Status Indicators**: Emoji icons for quick status recognition (✅⚠️📋❓)
- **Automated Tracking**: Tracks current vs latest versions with timestamps
- **Flexible Interface**: Command-line and interactive modes

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
# Or use the helper script:
# source activate.sh
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Update Excel file structure (if needed):
```bash
python3 update_excel.py
```

4. Update config.py with your credentials (based on existing pattern)

## Usage

### Command Line Interface

```bash
# Check all applications and instances
./check_versions.py --check-all

# Show summary with status icons
./check_versions.py --summary

# List all applications and instances
./check_versions.py --list

# Check specific application (checks all instances)
./check_versions.py --app "Kopia"  # Checks ssd, hdd, b2
./check_versions.py --app "Home Assistant"  # Single instance

# Interactive mode (default)
./check_versions.py
```

### Interactive Mode

Run `./check_versions.py` without arguments for menu-driven interface:
- Check all applications
- Check single application
- Show summary
- Show all applications

## Excel Structure

The Excel file uses a single sheet with the following columns:

- **Name**: Application name (Home Assistant, Kopia, etc.)
- **Instance**: Specific instance (ssd, hdd, b2, prod, etc.)
- **Type**: Application type/category
- **Category**: Infrastructure category (set automatically for servers)
- **Target**: Connection endpoint (URLs, hostnames, etc.)
- **GitHub**: Repository path for latest version checks
- **Current_Version**: Currently running version
- **Latest_Version**: Latest available version
- **Status**: Up to Date, Update Available, etc.
- **Last_Checked**: Timestamp of last check
- **Check_Method**: How versions are retrieved (see methods below)
- **Notes**: Additional information (auto-populated for some checks)

## Supported Applications & Check Methods

### Check Methods Available
- **`api_github`**: API call + GitHub releases (Home Assistant, ESPHome, Traefik)
- **`k8s_api_github`**: Kubernetes API + GitHub (K3s clusters)
- **`kubectl_github`**: Kubernetes exec + GitHub (Telegraf, VictoriaMetrics)
- **`kubectl_tags`**: Kubernetes with Docker tags (Mosquitto)
- **`mqtt_github`**: MQTT subscription + GitHub (Zigbee2MQTT)
- **`command_github`**: Shell command + GitHub (Kopia backup nodes)
- **`project_version`**: GitHub YAML project version (Konnected)
- **`api_custom`**: Custom API logic (OPNsense)
- **`server_status`**: SSH-based server monitoring (Linux servers, Raspberry Pi)
- **`api_proxmox`**: Proxmox VE API integration (Proxmox clusters)
- **`tailscale_multi`**: Multi-device Tailscale API (Tailscale mesh networks)

### Application Types Supported
- **Home Assistant** - Home automation platform with API monitoring
- **Kubernetes (K3s)** - Lightweight Kubernetes clusters
- **Kopia** - Backup software with multi-node support
- **Traefik** - Reverse proxy and load balancer
- **Zigbee2MQTT** - Zigbee to MQTT bridge with multiple coordinators
- **ESPHome** - ESP8266/ESP32 firmware platform
- **Telegraf** - Metrics collection agent
- **VictoriaMetrics** - Time series database components
- **Konnected** - Security system integration panels
- **Mosquitto** - MQTT broker
- **OPNsense** - Firewall/router firmware
- **Proxmox VE** - Virtualization platform
- **Linux Servers** - Ubuntu/Raspberry Pi OS kernel monitoring
- **Tailscale** - VPN mesh network device tracking

### Multi-Instance Applications
Applications that run on multiple servers are tracked separately by instance:
- **Kopia**: Backup instances (ssd, hdd, b2) with separate version tracking
- **Traefik**: Load balancer instances (prod, server1, rpi1) across different environments
- **Home Assistant**: Multiple installations (prod, rpi2, server3)
- **Zigbee2MQTT**: Multiple coordinators (coordinator1, coordinator2)
- **Telegraf**: Multiple monitoring agents (vm, graylog, server4)
- **Konnected**: Multiple alarm panels (car, workshop, garage)

Each instance gets its own row in the Excel file with individual version tracking.

## Security Notes

- Uses existing config.py pattern for credentials
- Never commits actual credentials to git
- Follows your established authentication patterns (Bearer tokens, API keys, etc.)


## Files in Project:
- **`Goepp Homelab Master.xlsx`** - Excel database with Name/Instance structure for tracking
- **`version_manager.py`** - Core Python class handling all version checking logic
- **`check_versions.py`** - Command-line interface with multi-instance support
- **`update_excel.py`** - Script to update Excel structure while preserving data
- **`requirements.txt`** - Python dependencies
- **`config.py`** - Configuration and credentials (not committed to git)
- **`checkers/`** - Directory containing modular version checker modules
  - **`github.py`** - GitHub release API functions
  - **`home_assistant.py`** - Home Assistant API integration
  - **`kubectl.py`** - Kubernetes pod version extraction
  - **`traefik.py`** - Traefik API endpoint version checking
  - **`server_status.py`** - SSH-based server monitoring
  - **`proxmox.py`** - Proxmox VE API integration
  - **`tailscale.py`** - Multi-device Tailscale monitoring
  - **`utils.py`** - Shared HTTP request helpers
  - And more specialized checkers for each application type
- **`venv/`** - Virtual environment (not committed to git)

## Quick Start Example:
```bash
# Activate virtual environment
source venv/bin/activate

# Check all applications (including all Kopia instances)
./check_versions.py --check-all

# Show summary with visual status icons
./check_versions.py --summary
```

### Example Multi-Instance Output:
```
Starting version check for all applications...
==================================================
Checking Kopia-ssd...
  ssd: 0.21.1
  Status: ✅ Up to Date

Checking Kopia-hdd...
  hdd: 0.21.1  
  Status: ✅ Up to Date

Checking Kopia-b2...
  b2: 0.21.1
  Status: ✅ Up to Date
```