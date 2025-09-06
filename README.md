# Goepp Homelab Version Manager

A comprehensive Python-based system for tracking software versions across your infrastructure using Excel for data management.

## Features

- **Excel Integration**: Uses "Goepp Homelab Master.xlsx" with Name/Instance structure
- **Multi-Instance Support**: Track multiple instances of the same application (e.g., Kopia nodes)
- **Dual Check Method Architecture**: 
  - **Current Version**: API calls, SSH connections, Kubernetes queries, MQTT subscriptions
  - **Latest Version**: GitHub releases/tags, Docker Hub, custom APIs, Proxmox updates
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
- **Repository**: Repository path for latest version checks (GitHub, Docker Hub, etc.)
- **Current_Version**: Currently running version
- **Latest_Version**: Latest available version
- **Status**: Up to Date, Update Available, etc.
- **Last_Checked**: Timestamp of last check
- **Check_Current**: How current versions are retrieved (api, ssh, kubectl, etc.)
- **Check_Latest**: How latest versions are retrieved (github_release, docker_hub, etc.)
- **Notes**: Additional information (auto-populated for some checks)

## Supported Applications & Check Methods

### Current Version Methods (`Check_Current`)
- **`api`**: REST API calls (Home Assistant, ESPHome, Traefik, OPNsense, Proxmox, Tailscale, Graylog)
- **`ssh`**: SSH connections to servers (Linux servers show OS + kernel, e.g. "Ubuntu 24.04.3 LTS - 6.8.0-79-generic")
- **`kubectl`**: Kubernetes operations - pod queries and node info (Telegraf, VictoriaMetrics, Mosquitto, K3s, Calico, MetalLB, Alertmanager)
- **`command`**: Shell commands (Kopia backup nodes)
- **`mqtt`**: MQTT subscription (Zigbee2MQTT)

### Latest Version Methods (`Check_Latest`)
- **`github_release`**: GitHub releases API (Home Assistant, ESPHome, Traefik, K3s, Calico, MetalLB, Alertmanager, etc.)
- **`github_tag`**: GitHub tags API (Konnected project versions, Mosquitto)
- **`docker_hub`**: Docker Hub/container tags (Graylog)
- **`ssh_apt`**: SSH-based apt package checking for kernel updates (Ubuntu, Raspberry Pi)
- **`proxmox`**: Proxmox-specific API (Proxmox VE)
- **`opnsense`**: OPNsense firmware update logic (OPNsense)
- **`tailscale`**: Tailscale device update tracking (Tailscale)
- **`none`**: No latest version checking (legacy method)

### Application Types Supported
- **Home Assistant** - Home automation platform with API monitoring
- **Kubernetes (K3s)** - Lightweight Kubernetes clusters with pod monitoring
- **Kopia** - Backup software with multi-node support (ssd, hdd, b2)
- **Traefik** - Reverse proxy and load balancer across environments
- **Zigbee2MQTT** - Zigbee to MQTT bridge with multiple coordinators
- **ESPHome** - ESP8266/ESP32 firmware platform
- **Telegraf** - Metrics collection agent across infrastructure
- **VictoriaMetrics** - Time series database components (vmsingle, vmagent, operator)
- **Konnected** - Security system integration panels
- **Mosquitto** - MQTT broker
- **OPNsense** - Firewall/router firmware
- **Proxmox VE** - Virtualization platform across cluster nodes
- **Graylog** - Log management platform with Docker Hub version tracking
- **MongoDB** - Document database
- **OpenSearch** - Search and analytics engine
- **Fluent Bit** - Log processor and forwarder
- **Calico** - Kubernetes networking and security
- **MetalLB** - Kubernetes load balancer
- **Alertmanager** - Prometheus alert handling
- **Linux Servers** - Ubuntu/Raspberry Pi kernel monitoring with apt-based update detection
- **Tailscale** - VPN mesh network device tracking

### Multi-Instance Applications
Applications that run on multiple servers are tracked separately by instance:
- **Kopia**: Backup instances (ssd, hdd, b2) with separate version tracking
- **Traefik**: Load balancer instances (prod, morgspi, mudderpi) across different environments
- **Home Assistant**: Multiple installations (prod, morgspi, mudderpi)
- **Zigbee2MQTT**: Multiple coordinators (zigbee11, zigbee15)
- **Telegraf**: Multiple monitoring agents (vm, graylog)
- **Konnected**: Multiple alarm panels (car, workshop)
- **K3s**: Kubernetes clusters (k3s-prod, k3s-morgspi, k3s-mudderpi)
- **Proxmox VE**: Cluster nodes (pve11, pve12, pve13, pve15)
- **VictoriaMetrics**: Multiple components (vmsingle, vmagent, operator)
- **Ubuntu/Raspberry Pi**: Multiple servers and devices with individual kernel tracking

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
  - **`graylog.py`** - Graylog API integration with Docker Hub version tracking
  - **`linux_kernel.py`** - Unified Linux kernel update checking via SSH and apt
  - **`server_status.py`** - SSH-based server monitoring
  - **`proxmox.py`** - Proxmox VE API integration
  - **`tailscale.py`** - Multi-device Tailscale monitoring
  - **`mongodb.py`** - MongoDB version checking
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